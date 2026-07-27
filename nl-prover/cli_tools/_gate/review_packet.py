#!/usr/bin/env python3
"""Shape lint for NL-Prover verifier review packets.

This tool checks restartable packet shape and merge-gate invariants. It does
not check mathematics; fresh Verifier agents remain responsible for proof
correctness.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path


REQUIRED_SECTIONS = [
    "Inputs Checked",
    "Verdict Snapshot",
    "Blocking Issues",
    "Problem Reading and Normalization",
    "Dependency and Theorem Ledger",
    "Definition and Source-Theorem Audit",
    "Load-Bearing Obligation Ledger",
    "Adversarial Route Audit",
    "Open Proof Obligations",
    "Uncertainty",
    "Next Action",
]

SNAPSHOT_KEYS = [
    "Verdict",
    "Score",
    "Statement preservation",
    "Problem-reading audit",
    "Hypotheses/preconditions audit",
    "Proof-obligation classification",
    "Definition/notation audit",
    "Source theorem audit",
    "Adversarial route audit",
    "External cross-verification",
]

PASS_AUDIT_KEYS = [
    "Statement preservation",
    "Problem-reading audit",
    "Hypotheses/preconditions audit",
    "Proof-obligation classification",
    "Definition/notation audit",
    "Source theorem audit",
    "Adversarial route audit",
]

ADVERSARIAL_AUDIT_KEYS = [
    "Target polarity",
    "Opposite-polarity examples or obstructions considered",
    "Global compatibility checks",
    "Known theorem or invariant collisions checked",
    "Unresolved adversarial blockers",
]

TARGET_OBSTRUCTION_AUDIT_KEYS = [
    "Obstruction kind",
    "Object and hypotheses audit",
    "Conclusion failure",
    "Accepted reading challenge",
    "Boundary and degenerate variants checked",
    "Process-failure dependence",
]

NEXT_ACTIONS = {
    "MERGE",
    "PROCEED_WITH_PLAN",
    "REVISE_PROOF",
    "REVISE_PLAN",
    "SEARCH_SOURCE",
    "LOOKUP_DEFINITION",
    "BRAINSTORM_ALTERNATIVES",
    "ADOPT_REFINED_PROOF",
    "ACCEPT_OBSTRUCTION",
    "KEEP_ORIGINAL",
    "HUMAN_REVIEW",
}

PASS_ACTION_BY_MODE = {
    "lemma": {"MERGE"},
    "plan": {"PROCEED_WITH_PLAN"},
    "global": {"ADOPT_REFINED_PROOF"},
    "obstruction": {"ACCEPT_OBSTRUCTION"},
}

BAD_LEDGER_STATUS = {
    "blocker",
    "blocked",
    "fail",
    "failed",
    "missing",
    "open",
    "pending",
    "todo",
    "unresolved",
    "unjustified",
}


@dataclass
class LintResult:
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    mode: str = "auto"
    verdict: str | None = None
    next_action: str | None = None

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


def parse_bullets(section: str) -> dict[str, str]:
    values: dict[str, str] = {}
    for line in section.splitlines():
        match = re.match(r"^\s*[-*]\s*([^:]+):\s*(.*?)\s*$", line)
        if match:
            values[canonical(match.group(1))] = match.group(2).strip()
    return values


def first_content_line(section: str) -> str:
    for line in section.splitlines():
        stripped = line.strip()
        if stripped:
            return stripped
    return ""


def is_none_section(section: str) -> bool:
    lines = [
        line.strip()
        for line in section.splitlines()
        if line.strip() and not line.strip().startswith("<!--")
    ]
    return len(lines) == 1 and lines[0] == "NONE"


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


def status_from_row(row: dict[str, str]) -> str:
    for key, value in row.items():
        if key == "status":
            return value.strip()
    if row:
        return next(reversed(row.values())).strip()
    return ""


def status_tokens(status: str) -> set[str]:
    return set(re.findall(r"[A-Za-z_]+", status.casefold()))


def check_ledger(
    *,
    result: LintResult,
    rows: list[dict[str, str]],
    label: str,
    mode: str,
    pass_verdict: bool,
) -> None:
    if not pass_verdict:
        return
    for index, row in enumerate(rows, start=1):
        status = status_from_row(row)
        tokens = status_tokens(status)
        bad = sorted(tokens & BAD_LEDGER_STATUS)
        if bad:
            result.errors.append(
                f"{label} row {index} has unresolved status {status!r}"
            )
        if mode in {"lemma", "global", "obstruction"} and "assigned" in tokens:
            result.errors.append(
                f"{label} row {index} is assigned, but {mode} PASS requires resolved work"
            )


def infer_mode(mode: str, next_action: str | None) -> str:
    if mode != "auto":
        return mode
    if next_action == "PROCEED_WITH_PLAN":
        return "plan"
    if next_action == "ADOPT_REFINED_PROOF":
        return "global"
    if next_action == "ACCEPT_OBSTRUCTION":
        return "obstruction"
    return "lemma"


def validate_external_status(result: LintResult, value: str) -> None:
    if not value or value.upper() in {"TODO", "PENDING", "TBD"}:
        result.errors.append("External cross-verification status is not recorded")
        return
    status = value.split(";", 1)[0].strip().casefold()
    if status not in {"ran", "unavailable", "failed"}:
        result.errors.append(
            "External cross-verification must start with ran, unavailable, or failed"
        )
    if status in {"ran", "failed"} and "raw files:" not in value.casefold():
        result.errors.append(
            "External cross-verification ran/failed status must name raw files or NONE"
        )


def validate_adversarial_audit(
    result: LintResult,
    sections: dict[str, str],
    *,
    pass_verdict: bool,
) -> None:
    if not pass_verdict:
        return

    audit = parse_bullets(sections.get(canonical("Adversarial Route Audit"), ""))
    for key in ADVERSARIAL_AUDIT_KEYS:
        if canonical(key) not in audit:
            result.errors.append(f"Missing adversarial route audit field: {key}")

    blockers = audit.get(canonical("Unresolved adversarial blockers"), "").strip()
    if blockers and blockers.upper() != "NONE":
        result.errors.append(
            "Unresolved adversarial blockers must be NONE for a passing packet"
        )


def validate_target_obstruction_audit(
    result: LintResult,
    sections: dict[str, str],
    *,
    inferred_mode: str,
    pass_verdict: bool,
) -> None:
    if not pass_verdict or inferred_mode != "obstruction":
        return

    section = sections.get(canonical("Target Obstruction Audit"), "")
    if not section:
        result.errors.append(
            "Missing section: Target Obstruction Audit is required for obstruction PASS"
        )
        return

    audit = parse_bullets(section)
    for key in TARGET_OBSTRUCTION_AUDIT_KEYS:
        if canonical(key) not in audit:
            result.errors.append(f"Missing target obstruction audit field: {key}")

    hypotheses = audit.get(canonical("Object and hypotheses audit"), "")
    if hypotheses and not re.search(
        r"\b(?:satisf\w*|hold\w*|held|checked|verified)\b",
        hypotheses,
        re.I,
    ):
        result.errors.append(
            "Object and hypotheses audit must state that the original hypotheses hold"
        )

    conclusion = audit.get(canonical("Conclusion failure"), "")
    if conclusion and not re.search(
        r"\b(?:fail\w*|false|violat\w*|does not hold|not satisfied)\b",
        conclusion,
        re.I,
    ):
        result.errors.append("Conclusion failure must state how the target conclusion fails")

    reading = audit.get(canonical("Accepted reading challenge"), "").strip()
    if reading.upper() in {"", "NONE", "N/A"}:
        result.errors.append(
            "Accepted reading challenge must record the accepted reading used"
        )

    variants = audit.get(canonical("Boundary and degenerate variants checked"), "").strip()
    if variants.upper() in {"", "NONE", "N/A"}:
        result.errors.append(
            "Boundary and degenerate variants checked must record the variants checked"
        )

    process = audit.get(canonical("Process-failure dependence"), "").strip()
    if process and not process.upper().startswith("NO"):
        result.errors.append(
            "Process-failure dependence must be NO for an accepted obstruction"
        )
    if re.search(
        r"\b(?:missing|unavailable|unknown|not supplied|not provided|"
        r"unable to|cannot prove|can't prove|failed to)\b",
        process,
        re.I,
    ):
        result.errors.append(
            "Accepted obstruction cannot depend on missing-route or agent-inability claims"
        )


def lint_text(text: str, mode: str = "auto") -> LintResult:
    result = LintResult(mode=mode)
    sections = read_sections(text)

    for required in REQUIRED_SECTIONS:
        if canonical(required) not in sections:
            result.errors.append(f"Missing section: {required}")

    snapshot = parse_bullets(sections.get(canonical("Verdict Snapshot"), ""))
    for key in SNAPSHOT_KEYS:
        if canonical(key) not in snapshot:
            result.errors.append(f"Missing verdict snapshot field: {key}")

    verdict = snapshot.get(canonical("Verdict"), "").strip().upper()
    result.verdict = verdict or None
    if verdict and verdict not in {"PASS", "NEEDS_REVISION", "FAIL"}:
        result.errors.append(f"Unknown verdict: {verdict}")

    next_action = first_content_line(sections.get(canonical("Next Action"), "")).upper()
    result.next_action = next_action or None
    if next_action and next_action not in NEXT_ACTIONS:
        result.errors.append(f"Unknown next action: {next_action}")

    inferred_mode = infer_mode(mode, next_action or None)
    result.mode = inferred_mode

    pass_verdict = verdict == "PASS"
    if pass_verdict:
        allowed_actions = PASS_ACTION_BY_MODE[inferred_mode]
        if next_action not in allowed_actions:
            result.errors.append(
                f"{inferred_mode} PASS requires next action "
                f"{' or '.join(sorted(allowed_actions))}, found {next_action or 'NONE'}"
            )
        for key in PASS_AUDIT_KEYS:
            value = snapshot.get(canonical(key), "").strip().upper()
            if value != "PASS":
                result.errors.append(f"{key} must be PASS for a passing packet")

        validate_external_status(
            result,
            snapshot.get(canonical("External cross-verification"), ""),
        )

        for section_name in ["Blocking Issues", "Uncertainty"]:
            if not is_none_section(sections.get(canonical(section_name), "")):
                result.errors.append(f"{section_name} must be exactly NONE for PASS")
        if inferred_mode != "plan" and not is_none_section(
            sections.get(canonical("Open Proof Obligations"), "")
        ):
            result.errors.append(
                "Open Proof Obligations must be exactly NONE for this PASS mode"
            )

        definition_audit = parse_bullets(
            sections.get(canonical("Definition and Source-Theorem Audit"), "")
        )
        for key in ["Source theorem warrant", "Circularity check"]:
            value = definition_audit.get(canonical(key), "").strip().upper()
            if not value:
                result.errors.append(f"{key} is missing from passing packet")
            elif value != "PASS":
                result.errors.append(f"{key} must be PASS for a passing packet")

        validate_adversarial_audit(
            result,
            sections,
            pass_verdict=pass_verdict,
        )
        validate_target_obstruction_audit(
            result,
            sections,
            inferred_mode=inferred_mode,
            pass_verdict=pass_verdict,
        )

    elif verdict in {"NEEDS_REVISION", "FAIL"}:
        has_route_detail = any(
            not is_none_section(sections.get(canonical(name), ""))
            for name in ["Blocking Issues", "Open Proof Obligations", "Uncertainty"]
        )
        if next_action in {
            "MERGE",
            "PROCEED_WITH_PLAN",
            "ADOPT_REFINED_PROOF",
            "ACCEPT_OBSTRUCTION",
        }:
            result.errors.append(
                f"{verdict} packet cannot use accepting next action {next_action}"
            )
        if not has_route_detail:
            result.errors.append(
                f"{verdict} packet must leave a blocker, obligation, or uncertainty"
            )

    load_rows = parse_markdown_table(
        sections.get(canonical("Load-Bearing Obligation Ledger"), "")
    )
    check_ledger(
        result=result,
        rows=load_rows,
        label="Load-Bearing Obligation Ledger",
        mode=inferred_mode,
        pass_verdict=pass_verdict,
    )
    dep_rows = parse_markdown_table(
        sections.get(canonical("Dependency and Theorem Ledger"), "")
    )
    check_ledger(
        result=result,
        rows=dep_rows,
        label="Dependency and Theorem Ledger",
        mode=inferred_mode,
        pass_verdict=pass_verdict,
    )

    return result


def lint_file(path: Path, mode: str = "auto") -> LintResult:
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        result = LintResult(mode=mode)
        result.errors.append(f"Cannot read {path}: {exc}")
        return result
    return lint_text(text, mode=mode)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Lint an NL-Prover review packet for restartable shape."
    )
    parser.add_argument("packet", type=Path, help="Path to review_packet*.md")
    parser.add_argument(
        "--mode",
        choices=["auto", "lemma", "plan", "global", "obstruction"],
        default="auto",
        help="Packet mode. auto infers from Next Action.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print machine-readable lint output.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    result = lint_file(args.packet, mode=args.mode)

    if args.json:
        print(
            json.dumps(
                {
                    "ok": result.ok,
                    "mode": result.mode,
                    "verdict": result.verdict,
                    "next_action": result.next_action,
                    "errors": result.errors,
                    "warnings": result.warnings,
                },
                indent=2,
                sort_keys=True,
            )
        )
    else:
        status = "PASS" if result.ok else "FAIL"
        print(f"review_packet_lint: {status} ({args.packet})")
        for error in result.errors:
            print(f"ERROR: {error}")
        for warning in result.warnings:
            print(f"WARNING: {warning}")
    return 0 if result.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
