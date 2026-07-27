#!/usr/bin/env python3
"""Axiom-set audit: run Lean's `#print axioms` over a file's declarations.

Compiling cleanly and scanning for `sorry` is not enough: a proof can still lean
on a project-local `axiom`, or reach `sorryAx` through a dependency. This tool
asks the kernel which axioms each declaration actually depends on and flags every
axiom outside the accepted base set.

    axioms <file.lean> [--decl NAME ...] [--allow AXIOM ...]
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

PROVABLE_KINDS = {"theorem", "lemma"}

# Lean prefixes `#print` output with `file:line:col: information:`, and wraps
# long axiom lists across lines, so match anywhere and span newlines.
DEPENDS_RE = re.compile(r"'(?P<name>[^'\n]+)' depends on axioms: \[(?P<axioms>[^\]]*)\]", re.S)
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


def prefix_at(points: list[tuple[int, str]], offset: int) -> str:
    prefix = ""
    for start, value in points:
        if start <= offset:
            prefix = value
        else:
            break
    return prefix


def target_declarations(file_path: Path, wanted: list[str] | None) -> list[str]:
    """Fully qualified theorem/lemma names declared in the file."""
    text = lst.read_text(file_path)
    points = namespace_prefixes(text)
    names = [
        prefix_at(points, d.start) + d.name
        for d in lst.find_declarations(text)
        if d.name and d.kind in PROVABLE_KINDS
    ]
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


def audit(
    file_path: Path,
    wanted: list[str] | None = None,
    allowed: list[str] | None = None,
    timeout: int = 300,
) -> dict:
    allow = list(allowed) if allowed is not None else list(BASE_AXIOMS)
    declarations = target_declarations(file_path, wanted)
    if not declarations:
        return {"okay": True, "allowed": allow, "declarations": [], "violations": []}

    ran, output = run_audit(file_path, declarations, timeout=timeout)
    if not ran:
        return {"okay": False, "allowed": allow, "error": output}

    reported = parse_audit(output)
    entries = []
    violations = []
    missing = []
    for name in declarations:
        if name in reported:
            axioms = reported[name]
        elif name.rsplit(".", 1)[-1] in reported:
            axioms = reported[name.rsplit(".", 1)[-1]]
        else:
            missing.append(name)
            continue
        extra = [a for a in axioms if a not in allow]
        entries.append({"declaration": name, "axioms": axioms, "unexpected": extra})
        if extra:
            violations.append({"declaration": name, "unexpected": extra})

    payload = {
        "okay": not violations and not missing,
        "allowed": allow,
        "declarations": entries,
        "violations": violations,
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
        help=f"Accepted axiom (default: {', '.join(BASE_AXIOMS)}); may be repeated",
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
    )
    if args.compact:
        payload.pop("declarations", None)
    print(json.dumps(payload, indent=2, ensure_ascii=False))
    sys.exit(0 if payload.get("okay") else 1)


if __name__ == "__main__":
    main()
