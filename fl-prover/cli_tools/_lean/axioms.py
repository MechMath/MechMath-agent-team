#!/usr/bin/env python3
"""Axiom-set audit: what a file depends on, and what it simply assumes.

Compiling cleanly and scanning for `sorry` is not enough: a proof can still lean
on a project-local `axiom`, or reach `sorryAx` through a dependency. This tool
asks the kernel which axioms each declaration actually depends on and flags every
axiom outside the accepted base set.

That kernel question has a blind spot, and it is the one that matters at
formalization time. `#print axioms` reports what a declaration *depends on* — so a
bare `axiom` nothing has consumed yet is invisible, and a file whose only content is
assumptions used to return `okay: true` outright. `opaque` is invisible even after
consumption, because it adds no kernel axiom at all. Both are how a missing object
gets sealed into a statement that then asserts nothing.

So the audit has two halves. **Depends-on**: the `#print axioms` result, unchanged.
**Declares**: every `axiom` / `opaque` declaration in the file, found lexically,
reported whether or not anything uses it. A declared assumption is a finding unless
it is named in `--allow`, exactly like a kernel axiom.

    axioms <file.lean> [--decl NAME ...] [--allow AXIOM ...] [--allow-only AXIOM ...]
           [--timeout-seconds N] [--compact]

The audit elaborates a *copy* of the file with `#print axioms` appended, so it
works on files that have never been `lake build`-ed — the same cost as `check`.

Output JSON: { okay, allowed, declarations: [...], violations: [...] }.
`okay` is false when any inspected declaration depends on an axiom outside
`allowed`, or when the audit itself could not be run.
"""

from __future__ import annotations

import argparse
import json
import logging
import re
import subprocess
import sys
from pathlib import Path

from _common.paths import configure_cli_logging
from _lean import check as lean_check
from _lean import sourcetools as lst

configure_cli_logging()
logger = logging.getLogger(__name__)

# Mathlib's classical base. Anything else — including `sorryAx` and any
# project-local `axiom` — is a finding, not a default.
BASE_AXIOMS = ("propext", "Classical.choice", "Quot.sound")

# Kinds that can actually carry an axiom, and so must be audited. Definitions belong
# here, not only proofs: `noncomputable def foo : X := sorry` carries `sorryAx`
# exactly as a theorem would (verified against the kernel), and a `def` is precisely
# how a missing *object* gets sealed in. The original `{theorem, lemma}` filter
# silently skipped every one of them.
PROVABLE_KINDS = {"theorem", "lemma", "def", "abbrev", "instance"}

# Kinds `#print axioms` accepts but which are not audited. They name types rather
# than values: measured against the kernel, a `structure`/`inductive` name, its `.mk`
# and its projections report clean even when a default value is built from a
# `sorry`-carrying def, so querying them buys nothing — and a file whose only
# auditable content is assumptions must stay auditable without a Lean toolchain.
#
# They are still *counted* and returned as `not_audited`, because the count is what
# makes this gate self-checking: `audited + not_audited` equals a plain `grep` of the
# file, so a coverage gap is visible without a hand-written `#print axioms` probe.
# Three separate agents had to run such probes by hand before this was fixed.
UNAUDITED_KINDS = {"structure", "class", "inductive"}

# `sourcetools.DECL_RE` requires the declaration keyword to follow only a modifier
# (`private`, `noncomputable`, …), so a declaration carrying an attribute on the same
# line — `@[simp] theorem foo …` — is invisible to it. That is a blind spot in exactly
# the audit that must not have one: such a theorem can reach `sorryAx` through a
# dependency and never be asked. Measured on the Kakeya tree: 255 of 10 284
# theorem/lemma declarations are attribute-prefixed.
#
# We do NOT widen `DECL_RE` itself: its match start is the offset the guard tool
# snapshots statement text from, so admitting the attribute there would shift every
# existing snapshot of an attributed declaration and fail guards that are in fact
# intact. This regex is local to the axiom audit and only ever adds names.
ATTR_DECL_RE = re.compile(
    r"(?m)^[ \t]*(?:@\[[^\]]*\][ \t]*)+"
    r"(?:(?:private|protected|noncomputable|unsafe|partial)[ \t]+)*"
    r"(?P<kind>theorem|lemma)[ \t]+(?P<name>[A-Za-z_][\w'.]*)"
)

# Declaration kinds that *are* an assumption rather than depending on one. `axiom`
# asserts; `opaque` names an object and seals its definition, so nothing downstream
# can unfold it and no proof can say anything about it.
ASSUMING_KINDS = {"axiom", "opaque"}

# Lean prefixes `#print` output with `file:line:col: information:`, and wraps
# long axiom lists across lines, so match anywhere and span newlines.
# Non-greedy name so declarations ending in a prime (e.g. `gp4_eq'`) still match:
# Lean prints those as `'Ramanujan28.gp4_eq'' depends on axioms: [...]`, and a
# `[^']` name class stops at the trailing prime and defeats the pattern.
DEPENDS_RE = re.compile(r"'(?P<name>[^\n]+?)' depends on axioms: \[(?P<axioms>[^\]]*)\]", re.S)
NO_AXIOMS_RE = re.compile(r"'(?P<name>[^'\n]+)' does not depend on any axioms")

NAMESPACE_RE = re.compile(r"(?m)^[ \t]*(?P<kind>namespace|end|section)(?:[ \t]+(?P<name>[A-Za-z_][\w'.]*))?[ \t]*$")


def namespace_prefixes(text: str) -> list[tuple[int, str]]:
    """Return (offset, namespace_prefix) checkpoints in source order.

    Lexical, like the rest of `sourcetools`: it tracks `namespace X` / `end X`
    (and anonymous `section` / `end`) so a declaration's fully qualified name can
    be reconstructed for `#print axioms`.
    """
    mask = lst.code_mask(text)
    clean = lst.masked_text(text, mask)
    stack: list[str | None] = []
    points: list[tuple[int, str]] = [(0, "")]
    for m in NAMESPACE_RE.finditer(clean):
        kind, name = m.group("kind"), m.group("name")
        if kind == "namespace" and name:
            stack.append(name)
        elif kind == "section":
            stack.append(None)
        elif kind == "end":
            if stack:
                stack.pop()
        prefix = ".".join(p for p in stack if p)
        points.append((m.end(), prefix + "." if prefix else ""))
    return points


def qualify(prefix: str, name: str) -> str:
    """Fully qualify `name` under `prefix`, honouring Lean's `_root_.` escape.

    A declaration written `theorem _root_.Foo.bar` inside `namespace Kakeya` is
    `Foo.bar`, not `Kakeya._root_.Foo.bar` — `_root_.` explicitly discards the
    enclosing namespace. Prefixing it anyway produced a name that does not exist,
    so `#print axioms` errored and the whole file's audit came back as
    `elaboration_failed`, hiding every other declaration in it. Observed on
    `MainLemma2/PlankPresentation.lean` and `Section6Compat.lean`.
    """
    if name.startswith("_root_."):
        return name[len("_root_."):]
    return prefix + name


def prefix_at(points: list[tuple[int, str]], offset: int) -> str:
    prefix = ""
    for start, value in points:
        if start <= offset:
            prefix = value
        else:
            break
    return prefix


def unaudited_declarations(file_path: Path) -> list[str]:
    """Fully qualified names present in the file but deliberately not queried.

    Reported so that `len(audited) + len(unaudited)` accounts for every declaration
    a `grep` of the file would find; see `UNAUDITED_KINDS`.
    """
    text = lst.read_text(file_path)
    points = namespace_prefixes(text)
    return [
        qualify(prefix_at(points, d.start), d.name)
        for d in lst.find_declarations(text)
        if d.name and d.kind in UNAUDITED_KINDS
    ]


def target_declarations(file_path: Path, wanted: list[str] | None) -> list[str]:
    """Fully qualified theorem/lemma names declared in the file."""
    text = lst.read_text(file_path)
    points = namespace_prefixes(text)
    found: list[tuple[int, str]] = [
        (d.start, qualify(prefix_at(points, d.start), d.name))
        for d in lst.find_declarations(text)
        if d.name and d.kind in PROVABLE_KINDS
    ]
    # Attribute-prefixed declarations, which `DECL_RE` cannot see (see ATTR_DECL_RE).
    # Match against comment/string-masked text so a declaration quoted in a docstring
    # is not audited as if it were code.
    clean = lst.masked_text(text, lst.code_mask(text))
    for match in ATTR_DECL_RE.finditer(clean):
        offset = match.start("kind")
        found.append((offset, qualify(prefix_at(points, offset), match.group("name"))))
    seen: set[str] = set()
    names = []
    for _, name in sorted(found, key=lambda pair: pair[0]):
        if name not in seen:
            seen.add(name)
            names.append(name)
    if wanted:
        want = set(wanted)
        picked = [n for n in names if n in want or n.rsplit(".", 1)[-1] in want]
        return picked or list(wanted)
    return names


def run_audit(file_path: Path, declarations: list[str], timeout: int = 300) -> tuple[bool, str]:
    """Elaborate the file plus appended `#print axioms` commands."""
    project_root = lean_check.find_project_root(file_path)
    text = lst.read_text(file_path)
    body = text.rstrip("\n") + "\n\n" + "\n".join(f"#print axioms {d}" for d in declarations) + "\n"

    # The probe sits beside the original so relative imports and the module's own
    # position in the package still resolve.
    probe = file_path.with_name(f".{file_path.stem}.axioms_probe.lean")
    try:
        probe.write_text(body, encoding="utf-8")
        result = subprocess.run(
            ["lake", "env", "lean", str(probe)],
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=str(project_root),
        )
    except subprocess.TimeoutExpired:
        return False, f"axiom audit timed out after {timeout}s"
    except Exception as exc:  # noqa: BLE001 — surfaced as JSON, not a traceback
        return False, str(exc)
    finally:
        probe.unlink(missing_ok=True)
    return True, result.stdout + "\n" + result.stderr


def parse_audit(output: str) -> dict[str, list[str]]:
    found: dict[str, list[str]] = {}
    for m in DEPENDS_RE.finditer(output):
        axioms = [a.strip() for a in m.group("axioms").replace("\n", " ").split(",") if a.strip()]
        found[m.group("name").strip()] = axioms
    for m in NO_AXIOMS_RE.finditer(output):
        found.setdefault(m.group("name").strip(), [])
    return found


def declared_assumptions(file_path: Path) -> list[dict]:
    """Every `axiom` / `opaque` declaration in the file, used or not.

    Lexical, like the rest of `sourcetools`, and deliberately so: this must report a
    declaration the kernel will never be asked about.
    """
    text = lst.read_text(file_path)
    points = namespace_prefixes(text)
    return [
        {
            "declaration": prefix_at(points, d.start) + (d.name or "_"),
            "kind": d.kind,
            "line": d.line,
        }
        for d in lst.find_declarations(text)
        if d.kind in ASSUMING_KINDS
    ]


def audit(
    file_path: Path,
    wanted: list[str] | None = None,
    allowed: list[str] | None = None,
    timeout: int = 300,
    allow_only: list[str] | None = None,
) -> dict:
    # `--allow` extends the classical base; `--allow-only` replaces it. It used to
    # replace silently, so `--allow Foo` de-allowed `propext` and the audit passed
    # a file it should have failed.
    if allow_only is not None:
        allow = list(allow_only)
    else:
        allow = list(BASE_AXIOMS) + list(allowed or [])

    assumed = [a for a in declared_assumptions(file_path)
               if a["declaration"] not in allow
               and a["declaration"].rsplit(".", 1)[-1] not in allow]

    declarations = target_declarations(file_path, wanted)
    unaudited = [] if wanted else unaudited_declarations(file_path)
    if not declarations:
        # No theorem to ask the kernel about. That is not the same as nothing to
        # report: a file can consist entirely of assumptions.
        return {
            "okay": not assumed,
            "allowed": allow,
            "declarations": [],
            "violations": [],
            "declared_assumptions": assumed,
            "not_audited": unaudited,
        }

    ran, output = run_audit(file_path, declarations, timeout=timeout)
    if not ran:
        return {"okay": False, "allowed": allow, "error": output}

    # If the audit's own elaboration errored, Lean's recovery seals the failed
    # declarations with `sorryAx` — which then reads as an axiom violation of a
    # perfectly clean theorem. Surface it instead of reporting the symptom: the usual
    # cause is auditing a file inside a checkout whose `.lake` is not current, and the
    # fix is to build first, not to distrust the declaration.
    elaboration_errors = [
        line for line in output.splitlines()
        if "error:" in line or "error(" in line
    ]
    if elaboration_errors:
        return {
            "okay": False,
            "allowed": allow,
            "elaboration_failed": True,
            "elaboration_errors": elaboration_errors[:20],
            "hint": "the audit's own elaboration errored, so any `sorryAx` below is "
                    "error recovery, not a real dependency; run `check` on this file "
                    "and rebuild the checkout, then re-audit",
        }

    reported = parse_audit(output)
    entries = []
    violations = []
    missing = []
    # `#print axioms` prints a `private` declaration under its mangled internal name,
    # `_private.<Module>.<hash>.<Name>`, so a literal or short-name lookup misses it and
    # the declaration reads as unreported. Index the reported keys by final segment so
    # those map back. (Measured on the Kakeya tree: 15 private lemmas in one file print
    # mangled; a further few print no line at all, which correctly stays `unreported`.)
    # Only genuinely mangled keys are eligible. Matching *any* reported key by its final
    # segment is unsafe: it can bind a wanted declaration to a different one that merely
    # shares a short name, which produced a false `sorryAx` violation against a clean
    # theorem when this was first written.
    by_last_segment: dict[str, list[str]] = {}
    for key in reported:
        if key.startswith("_private."):
            by_last_segment.setdefault(key.rsplit(".", 1)[-1], []).append(key)

    for name in declarations:
        short = name.rsplit(".", 1)[-1]
        if name in reported:
            axioms = reported[name]
        elif short in reported:
            axioms = reported[short]
        elif len(by_last_segment.get(short, ())) == 1:
            # Unambiguous mangled match; ambiguity stays unreported rather than guessed.
            axioms = reported[by_last_segment[short][0]]
        else:
            missing.append(name)
            continue
        extra = [a for a in axioms if a not in allow]
        entries.append({"declaration": name, "axioms": axioms, "unexpected": extra})
        if extra:
            violations.append({"declaration": name, "unexpected": extra})

    payload = {
        "okay": not violations and not missing and not assumed,
        "allowed": allow,
        "declarations": entries,
        "violations": violations,
        "declared_assumptions": assumed,
        "not_audited": unaudited,
    }
    if missing:
        payload["unreported"] = missing
        payload["error"] = (
            "some declarations produced no `#print axioms` line "
            "(the file failed to elaborate?)"
        )
        payload["lean_output"] = output.strip()[:4000]
    return payload


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Audit the axiom set of a Lean file's theorems")
    parser.add_argument("file", type=Path, help="Lean file to audit")
    parser.add_argument("--decl", action="append", help="Restrict to this declaration; may be repeated")
    parser.add_argument(
        "--allow",
        action="append",
        help=(
            f"Additionally accept this axiom or declared assumption, on top of the "
            f"classical base ({', '.join(BASE_AXIOMS)}); may be repeated"
        ),
    )
    parser.add_argument(
        "--allow-only",
        action="append",
        help="Replace the accepted set entirely (the old --allow behaviour); may be repeated",
    )
    parser.add_argument("--timeout-seconds", type=int, default=300)
    parser.add_argument("--compact", action="store_true", help="Drop the per-declaration axiom lists")
    args = parser.parse_args(argv)

    file_path = args.file.resolve()
    if not file_path.exists():
        print(json.dumps({"okay": False, "error": f"File not found: {file_path}"}))
        sys.exit(1)

    logger.info("lean.axioms called: file=%s decls=%s", file_path, args.decl)
    payload = audit(
        file_path,
        wanted=args.decl,
        allowed=args.allow,
        timeout=args.timeout_seconds,
        allow_only=args.allow_only,
    )
    if args.compact:
        payload.pop("declarations", None)
    print(json.dumps(payload, indent=2, ensure_ascii=False))
    sys.exit(0 if payload.get("okay") else 1)


if __name__ == "__main__":
    main()
