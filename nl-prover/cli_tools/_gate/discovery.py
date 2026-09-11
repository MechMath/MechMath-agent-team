#!/usr/bin/env python3
"""Discovery-region schema lint (ADR 0023 P).

Structural only. Nothing here reads mathematics; every check asks whether a
required field is present, whether a status word is one the state machine knows,
and whether an artifact that claims a hard verdict cites what would justify it.

The one thing this gate exists to catch is a route being written off harder than
the evidence allows — a failed attempt recorded as a refuted theorem. Nine of the
ten kill mechanisms in the forensics reduce to that.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

from _gate import waiver

# The whole state vocabulary. A word outside it does not move a branch.
ALLOWED_STATUSES = ("active", "queued", "open", "blocked", "rejected", "done")
# Only certification mode reaches these two, and only with the evidence below.
CERTIFICATION_ONLY = ("rejected", "done")

# What a `rejected` row must cite. Either an exact counterexample or a
# certification-mode Verifier FAIL; nothing else closes a route.
REJECTED_EVIDENCE = re.compile(
    r"\b(?:counterexample|verifier\s+fail|fail\b.{0,20}\bverifier|review[_\- ]?packet)\b",
    re.IGNORECASE,
)
# A blocked row must name what it waits on, not merely assert it is blocked.
# Runs write the condition two ways -- with a connective ("blocked until the
# human supplies log 2") and with a colon ("**blocked**: cannot run on this
# machine"). Demanding the connective rejected the colon form, which is the one
# real branch tables use.
BLOCKED_CONDITION = re.compile(
    r"\b(?:until|waiting|awaits?|requires?|needs?|once|pending)\b", re.IGNORECASE
)
BLOCKED_EXPLANATION = re.compile(r"blocked\**\s*[:—–-]\s*\S", re.IGNORECASE)

SCOPE_TAG = "NO_RESULT_IN_DECLARED_SCOPE"
SCOPE_FIELDS = ("searched:", "next:")
# How far below an emitted tag its two fields may sit. A real `searched:` runs
# to a dozen lines when it enumerates what it covered, which is the case worth
# encouraging, so this is generous.
SCOPE_WINDOW = 40

# `discovery/` is the name the ADR used; no run has ever created it. This gate
# used to scan a fixed list of directories instead — routes, logs, sketch,
# search, knowledge, recovery, ce, audit, code, writer — with `lemmas/` left out
# on the grounds that it is the certification region.
#
# That list contradicted the ADR it implements. ADR 0023 puts the region on the
# artifact, not on the directory ("there is no separate `discovery/` tree"), and
# the corpus agrees: one workspace declared `Mode: DISCOVERY` in 23 files under
# `lemmas/`, 14 under `computations/`, 14 under `queries/` and 4 under
# `references/` — 55 artifacts the gate never opened, so their empty-search
# scopes, gap `consumed_at` fields and `Closed Off` evidence were never checked.
# An inclusion list has to be extended every time a run invents a directory, and
# nothing tells you it is short.
#
# So: read the whole workspace, minus what is not an artifact.
ARTIFACT_SKIP_DIRS = frozenset(
    {
        ".git",
        "__pycache__",
        ".venv",
        ".extracted",   # extracted PDF text, not written by an agent
        "static",       # presentation/static/, copied assets
        "memory",       # mechanical index output: it quotes other artifacts
                        # verbatim, so reading it double-reports their defects
                        # against a path whose owner cannot fix them
    }
)

# How a discovery-mode artifact announces itself, in its opening lines. This is
# what makes region separation checkable now that the region is a property of
# the artifact rather than of its directory.
DISCOVERY_HEADER = re.compile(r"\bmode\b\W{0,6}\**\s*discovery\b|\bDISCOVERY\b\s*[-—–]", re.I)
HEADER_LINES = 15

# Workspace-relative paths cited from proof.tex.
CITED_PATH = re.compile(r"\b([A-Za-z_][\w-]*(?:/[\w.-]+)+\.(?:md|txt|json|py))\b")

# What introduces a gap-specification section. `first_missing` was the field
# name the ADR proposed; runs write prose headings and `consumed_at` instead.
GAP_SECTION = re.compile(r"gap specification|first_missing", re.IGNORECASE)

# Status words agents invented, which downstream readers collapse to "not PASS".
# Flagged, never blocking: the prose stays, it just stops moving state.
INVENTED_TOKENS = re.compile(
    r"\b(?:DISPOSITION\s*=|[A-Z][A-Z0-9_]*_CLAIM\s*=|[A-Z][A-Z0-9_]*_EXECUTABLE\s*=|"
    r"\bINCONCLUSIVE\b|FINITE_UNIVERSE_NOT_DERIVED)"
)

REQUIREMENT = waiver.requirement_text(
    checks=(
        "Branch rows in STATUS.md: status word, and the evidence a hard status needs.\n"
        "Discovery artifacts: empty-search reports, gap specifications, closed-off records.\n"
        "Region separation: proof.tex must not cite any artifact that declares\n"
        "discovery mode in its opening lines."
    ),
    legal=(
        "status: " + " | ".join(ALLOWED_STATUSES) + "\n"
        "  rejected  needs an exact counterexample or a certification-mode Verifier FAIL\n"
        "  blocked   needs the external condition it waits on, written out\n"
        "  anything else that failed is: open\n"
        "empty search: " + SCOPE_TAG + " with fields " + ", ".join(SCOPE_FIELDS) + "\n"
        "gap specification: consumed_at (which hole it fills) is required;\n"
        "  acceptance is written by the consumer and may be empty"
    ),
    fix=(
        "A failed attempt with no counterexample: change the status to open.\n"
        "A blocked row: add the condition being waited on.\n"
        "An empty search: add the scope searched and the next scope to try.\n"
        "A gap specification: add consumed_at pointing at a hole in the current\n"
        "decomposition."
    ),
)


@dataclass
class DiscoveryResult:
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    waived: list[str] = field(default_factory=list)
    checked: list[str] = field(default_factory=list)
    # Every rejection this run recorded, with whatever it said about its own
    # reach. Data, not prose: the qualifier is what a later round needs in order
    # to know whether a neighbouring route is still open.
    rejections: list[dict] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.errors


_KNOWN_WORDS = ALLOWED_STATUSES + ("inconclusive", "superseded")


def _leading_status(cell: str) -> str:
    """The status word a table cell opens with, or ''.

    Real outcome cells are not bare words: they read ``**done** - superseded and
    exceeded by lem_uncovered_rate`` or ``blocked until the human supplies log
    2``. Requiring the whole cell to equal a status word made this gate blind to
    every branch table an actual run has written.
    """
    text = cell.strip().strip("`").replace("**", "").replace("__", "").strip()
    match = re.match(r"[A-Za-z-]+", text)
    if not match:
        return ""
    word = match.group(0).lower()
    return word if word in _KNOWN_WORDS else ""


def _status_rows(text: str) -> list[tuple[int, str, str]]:
    """Yield (line_no, status, whole_line) for markdown table rows with a status.

    Only the last cell is read as the status cell, and only its leading word.
    Scanning every cell for a prose-leading match would fire on ordinary text
    like "open question about ..." in a description column.
    """
    rows: list[tuple[int, str, str]] = []
    for line_no, line in enumerate(text.splitlines(), start=1):
        stripped = line.strip()
        if not stripped.startswith("|") or stripped.startswith("|---"):
            continue
        cells = [c.strip() for c in stripped.strip("|").split("|")]
        if len(cells) < 2:
            continue
        status = _leading_status(cells[-1])
        if not status:
            # Some tables put the status mid-row; accept only an exact cell.
            for cell in cells[:-1]:
                if cell.strip("` ").lower() in _KNOWN_WORDS:
                    status = cell.strip("` ").lower()
                    break
        if status:
            rows.append((line_no, status, stripped))
    return rows


def _bullets(lines: list[str]) -> list[tuple[int, str]]:
    """Group a markdown list into (start_line_no, whole_bullet_text).

    A bullet runs until the next bullet at the same-or-shallower indent. The
    fields this gate looks for are routinely written on continuation lines:

        - `scope:` the covering direction ...
          `evidence:` sketch/target_contract.md

    Checking line by line reported that correctly-written bullet as a violation.
    """
    out: list[tuple[int, str]] = []
    start: int | None = None
    indent = 0
    buf: list[str] = []
    for line_no, line in enumerate(lines, start=1):
        stripped = line.lstrip()
        is_item = stripped.startswith(("- ", "* ", "+ "))
        here = len(line) - len(stripped)
        if is_item and (start is None or here <= indent):
            if start is not None:
                out.append((start, "\n".join(buf)))
            start, indent, buf = line_no, here, [line]
        elif start is not None:
            if stripped and here <= indent and not is_item:
                out.append((start, "\n".join(buf)))
                start, buf = None, []
            else:
                buf.append(line)
    if start is not None:
        out.append((start, "\n".join(buf)))
    return out


def _tag_emissions(lines: list[str]) -> list[int]:
    """Line numbers where the empty-search tag is *emitted*, not mentioned.

    An emission stands alone on its line, or heads a block and ends in a colon.
    A mention sits inside a sentence -- "No `NO_RESULT_IN_DECLARED_SCOPE`
    condition arose", "one tag for the covering-system search". Nine of the
    sixteen files carrying the tag in one run only mentioned it; a file-level
    substring test flagged every one, and testing merely that the line *starts*
    with the tag still catches prose that happens to wrap there.
    """
    out: list[int] = []
    for line_no, line in enumerate(lines, start=1):
        head = line.strip().lstrip("-*+>| ").strip().strip("`").replace("**", "")
        if not head.startswith(SCOPE_TAG):
            continue
        rest = head[len(SCOPE_TAG):].strip().strip("`").strip()
        if rest and not rest.endswith(":"):
            continue
        out.append(line_no)
    return out


# What a rejection says about its own reach. Runs already write this by hand --
# `rejected: exact NW9 rule only`, `rejected: exact printed design only` -- and
# pair it with a `Non-goals: ... remain open` clause in route_history.md. The
# status parser reads the first word of the cell and discards the rest, so the
# most load-bearing half of the sentence reaches no tool.
#
# The lesson is already in this harness's own long-term memory, card
# `neg-a-counterexample-certifies-that-a-statement-is-false-it`: "a
# counterexample certifies that a statement is false; it does not delimit how it
# is false." An unqualified `rejected` closes a route at whatever width the
# reader assumes, which is exactly the failure that card was written about.
SCOPE_QUALIFIER = re.compile(
    r"\bexact\b|\bonly\b|\bthis\s+(?:frame|section|scope|instance|form)\b"
    r"|\bnon-?goals?\b|\bremains?\s+open\b|\bwithin\b|\brestricted\s+to\b"
    r"|\bin\s+this\s+\w+\s+scope\b",
    re.IGNORECASE,
)


def status_cell(row: str) -> str:
    """The status cell of a markdown table row: the last one."""
    cells = [c.strip() for c in row.strip().strip("|").split("|")]
    return cells[-1] if cells else ""


def status_qualifier(row: str) -> str:
    """Whatever the status cell says after its status word, or ''.

    Read from the status cell alone. Reading the whole row would pick up an
    "exact counterexample" in the evidence column and report a rejection as
    scoped when its status cell is the bare word.

    This is the field the vocabulary does not have. It is reported rather than
    parsed into a schema: inventing a scope grammar before anyone has written
    against one would be guessing at what the runs mean.
    """
    text = status_cell(row).strip("`").replace("**", "").replace("__", "").strip()
    match = re.match(r"[A-Za-z-]+[:\s\u2014\u2013-]*(.*)$", text)
    return match.group(1).strip() if match else ""


def check_status_rows(result: DiscoveryResult, status_path: Path) -> None:
    if not status_path.exists():
        return
    result.checked.append(str(status_path))
    text = status_path.read_text(encoding="utf-8", errors="replace")
    for line_no, status, line in _status_rows(text):
        if status in ("inconclusive", "superseded"):
            result.errors.append(
                f"{status_path}:{line_no} uses retired status {status!r}; "
                f"legal statuses are {', '.join(ALLOWED_STATUSES)}. "
                "A failed attempt with no counterexample is 'open'."
            )
            continue
        if status == "rejected":
            if not REJECTED_EVIDENCE.search(line):
                result.errors.append(
                    f"{status_path}:{line_no} is 'rejected' but cites no exact "
                    "counterexample and no certification-mode Verifier FAIL. "
                    "Use 'open' unless one exists."
                )
            elif not SCOPE_QUALIFIER.search(status_cell(line)):
                # Warning, not error: the evidence requirement above is the hard
                # one, and rows written before this existed must still pass.
                result.warnings.append(
                    f"{status_path}:{line_no} is 'rejected' without saying how far. "
                    "A counterexample certifies that a statement is false; it does "
                    "not delimit how it is false, and an unqualified rejection "
                    "closes the route at whatever width the next reader assumes. "
                    "Say what exactly is rejected and what remains open — runs "
                    "already write this ('rejected: exact <thing> only', plus a "
                    "'Non-goals: ... remain open' line in recovery/route_history.md)."
                )
            result.rejections.append(
                {
                    "path": str(status_path),
                    "line": line_no,
                    "scope": status_qualifier(line),
                }
            )
        if status == "blocked" and not (
            BLOCKED_CONDITION.search(line) or BLOCKED_EXPLANATION.search(line)
        ):
            result.errors.append(
                f"{status_path}:{line_no} is 'blocked' without naming the external "
                "condition it waits on. Name it, or use 'open'."
            )


def _artifact_paths(workspace: Path) -> list[Path]:
    """Every markdown artifact in the workspace, minus the non-artifacts.

    Whether a file carries proof weight is decided by its own mode header, not
    by which directory it sits in, so where the gate looks cannot be a list of
    directories either.
    """
    paths: list[Path] = []
    for path in workspace.rglob("*.md"):
        rel = path.relative_to(workspace)
        if ARTIFACT_SKIP_DIRS.intersection(rel.parts[:-1]):
            continue
        paths.append(path)
    return sorted(set(paths))


def check_empty_searches(result: DiscoveryResult, path: Path, lines: list[str]) -> None:
    for line_no in _tag_emissions(lines):
        window = "\n".join(lines[line_no - 1: line_no - 1 + SCOPE_WINDOW])
        missing = [f for f in SCOPE_FIELDS if f not in window]
        if missing:
            result.errors.append(
                f"{path}:{line_no} emits {SCOPE_TAG} without {', '.join(missing)} "
                f"in the following {SCOPE_WINDOW} lines. An empty search is a "
                "statement about the scope searched, so both the scope covered "
                "and the next scope to try are required."
            )


def check_gap_specifications(result: DiscoveryResult, path: Path, lines: list[str]) -> None:
    """Every item in a gap-specification section must name its consumer.

    Scoped to the section, not the file: a file may discuss gaps in prose and
    carry one specification, and requiring `consumed_at` to appear *somewhere*
    in such a file passes it on the strength of an unrelated line.
    """
    for line_no, line in enumerate(lines, start=1):
        if "first_missing" not in line:
            continue
        window = "\n".join(lines[line_no - 1: line_no - 1 + SCOPE_WINDOW])
        if "consumed_at" not in window:
            result.errors.append(
                f"{path}:{line_no} names a first_missing with no consumed_at. "
                "Name the hole in the current decomposition it fills."
            )

    for index, line in enumerate(lines):
        if not (line.lstrip().startswith("#") and GAP_SECTION.search(line)):
            continue
        level = len(line) - len(line.lstrip("#").lstrip()) if line.startswith("#") else 99
        body: list[tuple[int, str]] = []
        for offset, follow in enumerate(lines[index + 1:], start=index + 2):
            if follow.startswith("#") and len(follow) - len(follow.lstrip("#")) <= level:
                break
            body.append((offset, follow))
        item_start: int | None = None
        buf: list[str] = []
        items: list[tuple[int, str]] = []
        for line_no, follow in body:
            if follow.strip().startswith("**") or follow.strip().startswith("- **"):
                if item_start is not None:
                    items.append((item_start, "\n".join(buf)))
                item_start, buf = line_no, [follow]
            elif item_start is not None:
                buf.append(follow)
        if item_start is not None:
            items.append((item_start, "\n".join(buf)))
        for line_no, item in items:
            if "consumed_at" not in item:
                result.errors.append(
                    f"{path}:{line_no} specifies a gap with no consumed_at. "
                    "Name the hole in the current decomposition it fills, so a "
                    "specification that has drifted off-target is caught before "
                    "dispatch rather than at assembly."
                )


def check_closed_off(result: DiscoveryResult, path: Path, lines: list[str]) -> None:
    if not any("Closed Off" in line or "Do Not Retry" in line for line in lines):
        return
    for line_no, bullet in _bullets(lines):
        if "scope:" in bullet and "evidence:" not in bullet:
            result.errors.append(
                f"{path}:{line_no} closes something off without evidence:. "
                "Cite the artifact that closed it."
            )


def check_discovery_artifacts(result: DiscoveryResult, workspace: Path) -> None:
    for path in _artifact_paths(workspace):
        result.checked.append(str(path))
        text = path.read_text(encoding="utf-8", errors="replace")
        lines = text.splitlines()

        check_empty_searches(result, path, lines)
        check_gap_specifications(result, path, lines)
        check_closed_off(result, path, lines)

        for match in INVENTED_TOKENS.finditer(text):
            result.warnings.append(
                f"{path}: {match.group(0)!r} is not a status word and moves nothing. "
                "Say it in prose; use one of "
                f"{', '.join(ALLOWED_STATUSES)} for state."
            )
            break


def check_region_separation(result: DiscoveryResult, workspace: Path) -> None:
    proof = workspace / "proof.tex"
    if not proof.exists():
        return
    result.checked.append(str(proof))
    text = proof.read_text(encoding="utf-8", errors="replace")
    for line_no, line in enumerate(text.splitlines(), start=1):
        if "discovery/" in line:
            result.errors.append(
                f"{proof}:{line_no} cites discovery/. Discovery output is "
                "conjectural evidence and carries no proof weight; route it "
                "through a specialist and a fresh Verifier first."
            )
            continue
        for cited in CITED_PATH.findall(line):
            target = workspace / cited
            if not target.is_file():
                continue
            head = "\n".join(
                target.read_text(encoding="utf-8", errors="replace").splitlines()[:HEADER_LINES]
            )
            if DISCOVERY_HEADER.search(head):
                result.errors.append(
                    f"{proof}:{line_no} cites {cited}, which declares discovery "
                    "mode. Discovery output is conjectural evidence and carries "
                    "no proof weight; route it through a specialist and a fresh "
                    "Verifier first."
                )


def run(workspace: Path) -> DiscoveryResult:
    result = DiscoveryResult()
    check_status_rows(result, workspace / "STATUS.md")
    check_discovery_artifacts(result, workspace)
    check_region_separation(result, workspace)
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="gate discovery",
        description="Discovery-region schema lint (ADR 0023).",
        epilog=REQUIREMENT,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("workspace")
    parser.add_argument("--json", action="store_true")
    waiver.add_waiver_arg(parser)
    args = parser.parse_args(argv)

    workspace = Path(args.workspace)
    result = run(workspace)
    result.errors, result.waived = waiver.apply_waiver(
        result.errors, args.waive, gate="discovery", workspace=workspace
    )

    if args.json:
        print(json.dumps({
            "ok": result.ok,
            "errors": result.errors,
            "warnings": result.warnings,
            "waived": result.waived,
            "checked": result.checked,
            "rejections": result.rejections,
        }, indent=2))
        return 0 if result.ok else 1

    print("PASS" if result.ok else "FAIL")
    for error in result.errors:
        print(f"  ERROR {error}")
    for warning in result.warnings:
        print(f"  warn  {warning}")
    waiver.print_waived(result.waived, args.waive or "")
    if result.errors and not args.json:
        # Prose after a JSON document makes the document unparseable exactly
        # when it carries something to report. Six of the ten gates did this;
        # only the ones that happened to pass on the workspace they were tried
        # against looked healthy.
        print()
        print(REQUIREMENT)
    return 0 if result.ok else 1


if __name__ == "__main__":
    sys.exit(main())
