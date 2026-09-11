#!/usr/bin/env python3
"""Stop gate — the mechanical check that must pass before *any* run stop (ADR 0022).

The completion gate (`gate complete`) only runs on the verified-proof path, so a
run that stopped for an exhausted branch budget, a human pause, or a verified
obstruction wrote nothing back: candidate cards stayed in `memory/candidates/`,
the KB inbox stayed empty, and the resident `memory.md` never learned anything.
This gate anchors the run-end write-back as a mechanical fact at every stop.

    gate stop <workspace> [--verified-proof] [--json]

Checks, all errors (the completion gate keeps its softer warning classification;
here the whole point is that a stop cannot silently skip the write-back):

- local memory index exists and is fresh vs STATUS.md;
- the long-term tier was actually read this run (`memory/.longterm_read.json`);
- a run that recorded failures captured a lesson (candidate card or an explicit
  `no_constraint` marker);
- candidate cards were aggregated and landed in the KB inbox;
- the stop left its reader-facing export (ADR 0021): `proof.pdf` for a verified
  proof, `progress_notes.pdf` for every other stop.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from _gate import waiver

from _gate.completion import (
    GateResult,
    validate_candidate_aggregation,
    validate_candidate_production,
    validate_index_freshness,
    validate_longterm_read,
)


REQUIREMENT = waiver.requirement_text(
    checks="the write-back a stop owes the next run: local index freshness, long-term tier\nread, a lesson captured when the run recorded failures, candidates promoted,\nand the stop's export present.",
    legal='every stop, proof or not. --verified-proof only selects the completion path.',
    fix='Run memory.py refresh, then memory.py aggregate-candidates, then retry.\nIf there is genuinely nothing to learn, write the no_constraint marker and\nsay why.',
)

def validate_local_index(result: GateResult, workspace: Path) -> None:
    """`validate_index_freshness` deliberately skips a workspace that never built
    an index. At a stop that is itself the defect: nothing was sedimented."""
    if not (workspace / "memory" / "index.json").exists():
        result.errors.append(
            "no local memory index (memory/index.json); the run's routes and dead "
            "ends were never sedimented — run `memory.py refresh <workspace>`"
        )
        return
    validate_index_freshness(result, workspace)


def validate_stop_export(result: GateResult, workspace: Path, *, verified_proof: bool) -> None:
    """ADR 0021: every stop leaves a reader-facing document."""
    if verified_proof:
        if not (workspace / "proof.pdf").exists():
            result.errors.append(
                "verified-proof stop without proof.pdf; dispatch Writer and export "
                "the final article (ADR 0021)"
            )
        return
    missing = [
        name
        for name, path in (
            ("writer/progress_notes.tex", workspace / "writer" / "progress_notes.tex"),
            ("progress_notes.pdf", workspace / "progress_notes.pdf"),
            ("writer/progress_summary.tex", workspace / "writer" / "progress_summary.tex"),
            ("progress_summary.pdf", workspace / "progress_summary.pdf"),
        )
        if not path.exists()
    ]
    if missing:
        result.errors.append(
            f"non-proof stop without {' and '.join(missing)}; dispatch Writer in "
            "PROGRESS_NOTES mode before stopping (ADR 0021). The restart document "
            "and the summary are two documents with two readers, not one document "
            "twice. Both are LaTeX exported to PDF: the summary is the one a person "
            "opens, so it is the one that has to be typeset"
        )


def validate_notes_are_written_not_pasted(result: GateResult, workspace: Path) -> None:
    """A restart document may be long. It may not be a directory with a preamble.

    The most recent note in the corpus is 21,215 lines of which 20,655 -- 97.4%
    -- sit inside \begin{verbatim}: 42 internal packets pasted into LaTeX,
    markdown headings and all. It is the only file in 24 with any verbatim
    dumping, so this is not the corpus norm and a warning is proportionate.

    Warning, not error: ADR 0021 bought that length deliberately and this must
    not become a back door to capping it. What is being counted is pasting, not
    length.
    """
    notes = workspace / "writer" / "progress_notes.tex"
    if not notes.is_file():
        return
    try:
        text = notes.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return
    lines = text.splitlines()
    inside = False
    pasted = 0
    blocks = 0
    for line in lines:
        if "\\begin{verbatim}" in line:
            inside = True
            blocks += 1
            continue
        if "\\end{verbatim}" in line:
            inside = False
            continue
        if inside:
            pasted += 1
    if not blocks:
        return
    share = pasted / max(len(lines), 1)
    result.warnings.append(
        f"writer/progress_notes.tex: {blocks} verbatim block(s), {pasted} of "
        f"{len(lines)} lines ({share:.0%}) pasted rather than written. A verified "
        "proof is restated as mathematics; where it genuinely cannot be, cite the "
        "artifact's path and say why (prompts/writer.md, Progress Notes §2)"
    )


def lint_workspace(workspace: Path, *, verified_proof: bool = False) -> GateResult:
    result = GateResult()
    workspace = workspace.resolve()
    if not (workspace / "STATUS.md").exists():
        result.errors.append(f"Missing STATUS.md: {workspace / 'STATUS.md'}")
        return result

    validate_local_index(result, workspace)
    validate_longterm_read(result, workspace, escalate=True)
    validate_candidate_production(result, workspace, escalate=True)
    validate_candidate_aggregation(result, workspace)
    validate_stop_export(result, workspace, verified_proof=verified_proof)
    validate_notes_are_written_not_pasted(result, workspace)
    validate_run_times(result, workspace)
    return result


def validate_run_times(result: GateResult, workspace: Path) -> None:
    """A stop should leave behind when the run started and when it ended.

    That used to be asked of a hand-written `RUN_TIMES.md`. It was asked for and
    never delivered: 0 of 5 workspaces had one when the check landed, and none
    since. It had no template anywhere in the repo — its only specification was
    the warning string that asked for it — and the hook now records every
    dispatch's start, end and byte count, which is strictly more than the file
    ever held. So the ask is gone rather than repeated louder; the ten
    `RUN_TIMES.md` in the IMO corpus stay what they are, historical evidence.

    Warning, not error: a run that did everything else right must still be able
    to stop.
    """
    if not (workspace / "logs" / "dispatch.jsonl").is_file():
        result.warnings.append(
            f"No logs/dispatch.jsonl in {workspace}. One line per specialist dispatch "
            f"(role, start, end, bytes, batch) is the only per-dispatch timing the "
            f"natural-language side has; without it, concurrency and cost can only be "
            f"inferred from file mtimes. On Claude Code this file is written by the "
            f"PreToolUse/PostToolUse hook and its absence means the hook is not firing "
            f"— check NLPROVER_WORKSPACE. On Codex there is no hook mechanism and you "
            f"append the lines yourself. See the Dispatch Log section of "
            f"orchestrator-cookbook.md, which is split by platform."
        )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Check that a run may stop: memory written back, export present.",
        epilog=REQUIREMENT,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("workspace", type=Path, help="Problem workspace to check.")
    parser.add_argument(
        "--verified-proof",
        action="store_true",
        help="This stop is a verified proof (expect proof.pdf, not progress notes).",
    )
    parser.add_argument("--json", action="store_true", help="Print machine-readable output.")
    waiver.add_waiver_arg(parser)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    result = lint_workspace(args.workspace, verified_proof=args.verified_proof)

    # Waive before reporting. Reporting first published a verdict computed
    # before the waiver was applied, so `--json` listed errors the waiver
    # had already excused and carried an `ok` that disagreed with the
    # human output on the same run. The two views are one computation.
    for entry in waiver.read_waivers(args.workspace):
        result.warnings.append(
            f"waived {entry.get('gate','?')} ({len(entry.get('waived', []))} finding(s)): "
            f"{entry.get('reason','')}"
        )
    result.errors, _waived = waiver.apply_waiver(
        result.errors, args.waive, gate="stop",
        workspace=args.workspace,
    )
    if args.json:
        print(
            json.dumps(
                {"ok": result.ok, "errors": result.errors, "warnings": result.warnings},
                indent=2,
                sort_keys=True,
            )
        )
    else:
        print(f"stop_gate: {'PASS' if result.ok else 'FAIL'} ({args.workspace})")
        for error in result.errors:
            print(f"ERROR: {error}")
        for warning in result.warnings:
            print(f"WARNING: {warning}")
    if not args.json:
        waiver.print_waived(_waived, args.waive or "")
    if result.errors and not args.json:
        # Not under --json: the epilogue is prose, and printing prose after a
        # JSON document makes the document unparseable exactly when it carries
        # something to report. Measured: three of five workspaces failed to
        # parse, all three of them the failing ones.
        print()
        print(REQUIREMENT)
    return 0 if result.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
