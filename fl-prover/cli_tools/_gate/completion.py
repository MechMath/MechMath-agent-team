#!/usr/bin/env python3
"""Structural completion gate for NL-Prover workspaces.

This tool is intentionally non-mathematical. It checks that a workspace marked
complete has no obvious pending proof markers, no unresolved STATUS obligations,
and lintable passing review packets for accepted lemma rows.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path


# Sibling lint modules in the same _gate package.
from _gate import review_packet as review_packet_lint
from _gate import proof_review as proof_review_lint
from _gate import result_contract as result_contract_lint


PROOF_PENDING_PATTERNS = [
    ("LaTeX pending proof marker", re.compile(r"\\sorry(?:\b|\{)")),
    ("explicit SORRY marker", re.compile(r"\[SORRY\b", re.IGNORECASE)),
    ("human-review marker", re.compile(r"\[/?human-review\]", re.IGNORECASE)),
    ("TODO/FIXME/TBD marker", re.compile(r"\b(?:TODO|FIXME|TBD)\b")),
    (
        "blueprint placeholder",
        re.compile(
            r"<(?:original problem|main theorem|lemma statement|"
            r"verified proof|proof|statement)[^>\n]*>",
            re.IGNORECASE,
        ),
    ),
]

UNRESOLVED_STATUS_TOKENS = {
    "assigned",
    "blocked",
    "blocker",
    "fail",
    "failed",
    "in_progress",
    "missing",
    "needs_revision",
    "open",
    "pending",
    "restartable",
    "stuck",
    "todo",
    "unresolved",
    "unverified",
}

ACCEPTED_STATUS_TOKENS = {
    "accepted",
    "complete",
    "merged",
    "proved",
    "resolved",
    "verified",
}

ACCEPTED_VERDICTS = {"PASS"}

PROOF_REVIEW_RESTART_STATUSES = {
    "PROOF_REVISION",
    "SOURCE_OR_DEFINITION_RECOVERY",
    "RESKETCH",
    "HUMAN_CLARIFICATION",
}


@dataclass
class GateResult:
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    packets_checked: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.errors


def canonical(name: str) -> str:
    return re.sub(r"\s+", " ", name.strip()).casefold()


def read_sections(text: str) -> dict[str, str]:
    sections: dict[str, list[str]] = {}
    current: str | None = None
    for line in text.splitlines():
        match = re.match(r"^##\s+(.+?)\s*$", line)
        if match:
            current = canonical(match.group(1))
            sections.setdefault(current, [])
            continue
        if current is not None:
            sections[current].append(line)
    return {name: "\n".join(lines).strip() for name, lines in sections.items()}


def first_content_line(section: str) -> str:
    for line in section.splitlines():
        stripped = line.strip()
        if stripped and not stripped.startswith("<!--"):
            return stripped
    return ""


def content_lines(section: str) -> list[str]:
    return [
        line.strip()
        for line in section.splitlines()
        if line.strip() and not line.strip().startswith("<!--")
    ]


def is_none_or_empty(section: str) -> bool:
    lines = content_lines(section)
    return not lines or (len(lines) == 1 and lines[0].upper() == "NONE")


def split_table_row(line: str) -> list[str]:
    return [cell.strip() for cell in line.strip().strip("|").split("|")]


def parse_markdown_table(section: str) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    headers: list[str] | None = None
    for line in section.splitlines():
        stripped = line.strip()
        if not stripped.startswith("|") or not stripped.endswith("|"):
            continue
        cells = split_table_row(stripped)
        if all(re.fullmatch(r":?-{3,}:?", cell.replace(" ", "")) for cell in cells):
            continue
        if headers is None:
            headers = [canonical(cell) for cell in cells]
            continue
        rows.append(dict(zip(headers, cells, strict=False)))
    return rows


def status_tokens(value: str) -> set[str]:
    return set(re.findall(r"[A-Za-z_]+", value.casefold()))


def extract_path(value: str) -> str | None:
    stripped = value.strip()
    if not stripped or stripped in {"-", "NONE", "N/A"}:
        return None
    markdown_link = re.search(r"\]\(([^)]+)\)", stripped)
    if markdown_link:
        stripped = markdown_link.group(1)
    stripped = stripped.strip("` ")
    match = re.search(r"[\w./:-]*review_packet[\w./:-]*\.md", stripped)
    if match:
        return match.group(0)
    return stripped.split()[0].strip(",;") if stripped else None


def validate_proof_markers(result: GateResult, proof_path: Path) -> None:
    if not proof_path.exists():
        result.errors.append(f"Missing proof file: {proof_path}")
        return
    text = proof_path.read_text(encoding="utf-8")
    for label, pattern in PROOF_PENDING_PATTERNS:
        match = pattern.search(text)
        if match:
            line_no = text[: match.start()].count("\n") + 1
            result.errors.append(f"proof.tex has {label} at line {line_no}")


def validate_open_obligations(result: GateResult, section: str) -> None:
    if is_none_or_empty(section):
        return
    rows = parse_markdown_table(section)
    if not rows:
        result.errors.append(
            "STATUS.md Open Proof Obligations is not NONE and has no parseable table"
        )
        return
    for index, row in enumerate(rows, start=1):
        status = row.get("status", "")
        tokens = status_tokens(status)
        unresolved = sorted(tokens & UNRESOLVED_STATUS_TOKENS)
        if unresolved:
            result.errors.append(
                f"STATUS.md open obligation row {index} has unresolved status {status!r}"
            )
        elif not tokens & ACCEPTED_STATUS_TOKENS:
            result.warnings.append(
                f"STATUS.md open obligation row {index} has unrecognized status {status!r}"
            )


def validate_phase(result: GateResult, sections: dict[str, str]) -> None:
    phase = first_content_line(sections.get(canonical("Phase"), ""))
    if not phase:
        result.errors.append("STATUS.md is missing a Phase value")
        return
    if "complete" not in status_tokens(phase):
        result.errors.append(f"STATUS.md Phase is not complete: {phase!r}")


def validate_lemma_rows(
    result: GateResult,
    *,
    workspace: Path,
    lemma_section: str,
) -> None:
    rows = parse_markdown_table(lemma_section)
    if not rows:
        result.warnings.append("STATUS.md has no parseable Lemma Status rows")
        return
    for index, row in enumerate(rows, start=1):
        lemma = row.get("lemma", f"row {index}")
        status = row.get("status", "")
        status_parts = status_tokens(status)
        if status_parts & UNRESOLVED_STATUS_TOKENS:
            result.errors.append(f"lemma {lemma} has unresolved status {status!r}")
        elif not status_parts & ACCEPTED_STATUS_TOKENS:
            result.errors.append(f"lemma {lemma} is not marked accepted/verified")

        verdict = row.get("verifier verdict", "").strip().upper()
        if verdict and verdict not in ACCEPTED_VERDICTS:
            result.errors.append(f"lemma {lemma} verifier verdict is not PASS: {verdict}")
        elif not verdict:
            result.errors.append(f"lemma {lemma} is missing a verifier verdict")

        packet_value = row.get("review packet", "")
        packet_name = extract_path(packet_value)
        if packet_name is None:
            result.errors.append(f"lemma {lemma} is missing a review packet path")
            continue
        packet_path = Path(packet_name)
        if not packet_path.is_absolute():
            packet_path = workspace / packet_path
        lint_packet(result, packet_path)


def lint_packet(result: GateResult, packet_path: Path) -> None:
    lint = review_packet_lint.lint_file(packet_path, mode="auto")
    result.packets_checked.append(str(packet_path))
    for error in lint.errors:
        result.errors.append(f"{packet_path}: {error}")
    for warning in lint.warnings:
        result.warnings.append(f"{packet_path}: {warning}")


def validate_proof_review(
    result: GateResult,
    *,
    workspace: Path,
    obstruction_packets: list[str],
) -> None:
    review_path = workspace / "review" / "proof_review.md"
    if not review_path.exists():
        return

    lint = proof_review_lint.lint_file(review_path)
    for error in lint.errors:
        result.errors.append(f"{review_path}: {error}")
    for warning in lint.warnings:
        result.warnings.append(f"{review_path}: {warning}")

    status = lint.selected_status
    if status in PROOF_REVIEW_RESTART_STATUSES:
        result.errors.append(
            f"{review_path}: selected restart status {status}; route this "
            "blocker to the named owner before marking the workspace complete"
        )
    elif status == "OBSTRUCTION_VERIFICATION" and not obstruction_packets:
        result.errors.append(
            f"{review_path}: selected OBSTRUCTION_VERIFICATION, but no accepted "
            "obstruction review packet was supplied with --packet"
        )


def _read_jsonl(path: Path) -> list[dict]:
    records: list[dict] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            records.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return records


def validate_candidate_aggregation(result: GateResult, workspace: Path) -> None:
    """ADR 0016 §3.6 (Phase 3.5): if a run emitted candidate negative-constraint
    cards, they must have been aggregated by the Orchestrator (dedup product) and
    promoted into the long-term tier. Enforcement anchors at the gate as a
    mechanical fact, not the Orchestrator's good intention."""
    cand_dir = workspace / "memory" / "candidates"
    if not cand_dir.exists():
        return
    records: list[dict] = []
    for path in sorted(cand_dir.glob("*.jsonl")):
        records.extend(_read_jsonl(path))
    # `no_constraint` markers satisfy the production-side check but carry nothing
    # to promote, so a run whose only records are markers owes no aggregation.
    real = [r for r in records if not r.get("no_constraint")]
    if not real:
        return
    aggregated = workspace / "memory" / "candidates_aggregated.jsonl"
    if not aggregated.exists():
        result.errors.append(
            "candidate cards present in memory/candidates/ but not aggregated; "
            "run `memory.py aggregate-candidates <workspace>`"
        )
        return
    if not (workspace / "memory" / "candidates_promoted.json").exists():
        result.errors.append(
            "aggregated candidate cards were not promoted into the long-term tier; "
            "run `memory.py aggregate-candidates <workspace>`"
        )


def validate_candidate_production(result: GateResult, workspace: Path, *, escalate: bool = False) -> None:
    """ADR 0016 §3.6 production-side backstop: if the run recorded failure
    artifacts (a proof-review routing artifact, or a non-empty failed_paths
    channel), the Orchestrator should have captured a lesson — at least one
    candidate card OR an explicit no_constraint marker.

    ADR 0022: `escalate` makes this an error rather than a warning. A run that
    recorded failures and captured no lesson leaves nothing behind for the next
    problem, which is the exact defect ADR 0022 fixes; the escape hatch is one
    `{"no_constraint": "..."}` line, so the bar is cheap to clear honestly."""
    failed_paths = workspace / "memory" / "failed_paths.jsonl"
    review = workspace / "review" / "proof_review.md"
    routes = list((workspace / "routes").glob("proof_review*.md")) if (workspace / "routes").exists() else []
    had_failure_signal = bool(routes) or review.exists() or (
        failed_paths.exists() and _read_jsonl(failed_paths)
    )
    if not had_failure_signal:
        return
    cand_dir = workspace / "memory" / "candidates"
    records: list[dict] = []
    if cand_dir.exists():
        for path in sorted(cand_dir.glob("*.jsonl")):
            records.extend(_read_jsonl(path))
    if not records:
        message = (
            "run recorded failure/obstruction artifacts but emitted no candidate "
            "cards or no_constraint markers (see the memory-routing skill)"
        )
        (result.errors if escalate else result.warnings).append(message)


def validate_index_freshness(result: "GateResult", workspace: Path) -> None:
    """ADR 0020 B.3: the local memory index must not be stale at completion. Only
    fires when an index exists (a run that never built one is not blocked here)."""
    index_json = workspace / "memory" / "index.json"
    if not index_json.exists():
        return
    try:
        from _memory import local as _mem  # type: ignore
    except Exception:
        sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
        try:
            from _memory import local as _mem  # type: ignore
        except Exception:
            return
    st = _mem.staleness(workspace)
    if st.get("stale"):
        newer = ", ".join(st.get("newer_than_index") or []) or "STATUS.md"
        result.errors.append(
            f"local memory index is stale ({newer} newer than memory/index.json); "
            "run `memory.py refresh <workspace>` (ADR 0020)"
        )


def validate_longterm_read(result: "GateResult", workspace: Path, *, escalate: bool = False) -> None:
    """ADR 0016/0020 B.0: leave a mechanical signal that the resident long-term
    memory was read. Warning at completion (so existing runs are not
    retro-blocked); ADR 0022 escalates it at the stop gate."""
    marker = workspace / "memory" / ".longterm_read.json"
    if not marker.exists():
        message = (
            "no long-term-memory read trace (memory/.longterm_read.json); the "
            "resident memory.md may not have been consulted this run — read it with "
            "`memory.py read --tier long-term <workspace>` (ADR 0016/0020)"
        )
        (result.errors if escalate else result.warnings).append(message)


def lint_workspace(workspace: Path, extra_packets: list[Path] | None = None) -> GateResult:
    result = GateResult()
    workspace = workspace.resolve()
    status_path = workspace / "STATUS.md"
    proof_path = workspace / "proof.tex"

    validate_proof_markers(result, proof_path)

    if not status_path.exists():
        result.errors.append(f"Missing STATUS.md: {status_path}")
        return result

    status_text = status_path.read_text(encoding="utf-8")
    sections = read_sections(status_text)
    validate_phase(result, sections)
    validate_open_obligations(
        result,
        sections.get(canonical("Open Proof Obligations"), ""),
    )
    validate_lemma_rows(
        result,
        workspace=workspace,
        lemma_section=sections.get(canonical("Lemma Status"), ""),
    )

    for packet in extra_packets or []:
        packet_path = packet if packet.is_absolute() else workspace / packet
        lint_packet(result, packet_path)

    contract = result_contract_lint.lint_workspace(
        workspace,
        extra_packets=extra_packets,
    )
    for error in contract.errors:
        result.errors.append(f"result contract: {error}")
    for warning in contract.warnings:
        result.warnings.append(f"result contract: {warning}")

    validate_proof_review(
        result,
        workspace=workspace,
        obstruction_packets=contract.obstruction_packets,
    )

    validate_candidate_aggregation(result, workspace)
    validate_candidate_production(result, workspace)

    validate_index_freshness(result, workspace)
    validate_longterm_read(result, workspace)

    if not result.packets_checked:
        result.errors.append("No review packets were checked for completion")

    return result


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Check completion readiness before an NL-Prover final answer."
    )
    parser.add_argument(
        "workspace",
        type=Path,
        help="Problem workspace containing proof.tex and STATUS.md.",
    )
    parser.add_argument(
        "--packet",
        action="append",
        default=[],
        type=Path,
        help="Additional refined-proof or obstruction review packet to lint.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print machine-readable gate output.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    result = lint_workspace(args.workspace, extra_packets=args.packet)

    if args.json:
        print(
            json.dumps(
                {
                    "ok": result.ok,
                    "errors": result.errors,
                    "warnings": result.warnings,
                    "packets_checked": result.packets_checked,
                },
                indent=2,
                sort_keys=True,
            )
        )
    else:
        status = "PASS" if result.ok else "FAIL"
        print(f"completion_gate: {status} ({args.workspace})")
        for error in result.errors:
            print(f"ERROR: {error}")
        for warning in result.warnings:
            print(f"WARNING: {warning}")
        if result.packets_checked:
            print("Packets checked:")
            for packet in result.packets_checked:
                print(f"- {packet}")
    return 0 if result.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
