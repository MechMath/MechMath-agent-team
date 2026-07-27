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

from _gate.completion import (
    GateResult,
    validate_candidate_aggregation,
    validate_candidate_production,
    validate_index_freshness,
    validate_longterm_read,
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
        )
        if not path.exists()
    ]
    if missing:
        result.errors.append(
            f"non-proof stop without {' and '.join(missing)}; dispatch Writer in "
            "PROGRESS_NOTES mode before stopping (ADR 0021)"
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
    return result


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Check that a run may stop: memory written back, export present."
    )
    parser.add_argument("workspace", type=Path, help="Problem workspace to check.")
    parser.add_argument(
        "--verified-proof",
        action="store_true",
        help="This stop is a verified proof (expect proof.pdf, not progress notes).",
    )
    parser.add_argument("--json", action="store_true", help="Print machine-readable output.")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    result = lint_workspace(args.workspace, verified_proof=args.verified_proof)

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
    return 0 if result.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
