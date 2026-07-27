#!/usr/bin/env python3
"""Structural lint for two-sided proof-review routing artifacts.

This tool is intentionally non-mathematical. It checks that a proof review
artifact selects one restartable status and does not route process failure,
missing context, or unresolved reading obligations as a terminal mathematical
result.
"""

from __future__ import annotations

import argparse
import json
import re
from dataclasses import dataclass, field
from pathlib import Path


REQUIRED_SECTIONS = [
    "Target Reading Check",
    "Proof Route",
    "Refutation Route",
    "Decision",
]

ALLOWED_STATUSES = {
    "PROOF_REVISION",
    "SOURCE_OR_DEFINITION_RECOVERY",
    "RESKETCH",
    "OBSTRUCTION_VERIFICATION",
    "HUMAN_CLARIFICATION",
    "FINAL_PROOF_READY",
}

TERMINAL_STATUSES = {"OBSTRUCTION_VERIFICATION", "FINAL_PROOF_READY"}

PROCESS_FAILURE_PATTERNS = [
    (
        "agent/process inability",
        re.compile(
            r"\b(?:cannot|can't|unable to|failed to|do not)\s+"
            r"(?:prove|establish|show|complete|find)\b",
            re.IGNORECASE,
        ),
    ),
    (
        "missing source or route",
        re.compile(
            r"\b(?:definition|theorem|source|construction|route|context|"
            r"convention|notation)\b.{0,80}\b(?:missing|unavailable|"
            r"unknown|not supplied|not provided|not found)\b",
            re.IGNORECASE,
        ),
    ),
    (
        "undefined object or notation",
        re.compile(
            r"\b(?:symbol|term|expression|notation|object)\b"
            r".{0,40}\b(?:undefined|not defined)\b",
            re.IGNORECASE,
        ),
    ),
    (
        "insufficient context",
        re.compile(
            r"\b(?:not enough|insufficient)\s+"
            r"(?:information|context|definitions|data)\b",
            re.IGNORECASE,
        ),
    ),
    (
        "gap label",
        re.compile(r"\b(?:gap found|process gap|route gap)\b", re.IGNORECASE),
    ),
]

UNRESOLVED_PATTERNS = [
    re.compile(
        r"\b(?:unresolved|unknown|unclear|ambiguous|pending|open|"
        r"not checked|not audited|not settled|TBD|TODO)\b",
        re.IGNORECASE,
    ),
    re.compile(r"\?", re.IGNORECASE),
]

POSITIVE_HYPOTHESIS_PATTERN = re.compile(
    r"\b(?:satisf\w*|hold\w*|checked|audited|verified|met|yes)\b",
    re.IGNORECASE,
)

CONCLUSION_FAILURE_PATTERN = re.compile(
    r"\b(?:fails?|false|violated|does not hold|contradicts|impossible)\b",
    re.IGNORECASE,
)


@dataclass
class ProofReviewLintResult:
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    selected_status: str | None = None

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


def is_blankish(value: str) -> bool:
    return value.strip().upper() in {"", "-", "NONE", "N/A", "NA", "TBD", "TODO"}


def is_resolved_none(value: str) -> bool:
    return value.strip().upper() in {"", "NONE", "NO", "N/A", "NA"}


def has_unresolved_language(value: str) -> bool:
    return any(pattern.search(value) for pattern in UNRESOLVED_PATTERNS)


def process_failure_hits(value: str) -> list[str]:
    return [label for label, pattern in PROCESS_FAILURE_PATTERNS if pattern.search(value)]


def require_field(
    result: ProofReviewLintResult,
    values: dict[str, str],
    key: str,
    section_name: str,
) -> str:
    value = values.get(canonical(key), "")
    if is_blankish(value):
        result.errors.append(f"{section_name} is missing required field: {key}")
    return value


def validate_sections(
    result: ProofReviewLintResult,
    sections: dict[str, str],
) -> None:
    for section in REQUIRED_SECTIONS:
        if canonical(section) not in sections:
            result.errors.append(f"Missing required section: {section}")


def validate_decision(result: ProofReviewLintResult, decision: dict[str, str]) -> None:
    status = decision.get(canonical("Selected status"), "").strip()
    if not status:
        result.errors.append("Decision is missing required field: Selected status")
        return
    if "|" in status or "," in status:
        result.errors.append("Decision selected status must contain exactly one status")
        return
    status = status.upper()
    result.selected_status = status
    if status not in ALLOWED_STATUSES:
        result.errors.append(f"Decision selected status is not recognized: {status}")

    require_field(result, decision, "Owner", "Decision")
    require_field(result, decision, "File target", "Decision")
    require_field(result, decision, "Reason", "Decision")


def validate_terminal_common(
    result: ProofReviewLintResult,
    *,
    target: dict[str, str],
    decision: dict[str, str],
) -> None:
    unresolved_key = canonical("Unresolved reading obligations")
    if unresolved_key not in target:
        result.errors.append(
            "Target Reading Check is missing required field: "
            "Unresolved reading obligations"
        )
    elif not is_resolved_none(target[unresolved_key]):
        result.errors.append(
            "Terminal proof-review status requires Unresolved reading obligations: NONE"
        )

    for key in ["Reason"]:
        value = decision.get(canonical(key), "")
        hits = process_failure_hits(value)
        if hits:
            result.errors.append(
                f"Terminal proof-review decision relies on {', '.join(hits)}: {value!r}"
            )


def validate_obstruction_status(
    result: ProofReviewLintResult,
    *,
    refutation: dict[str, str],
) -> None:
    object_value = require_field(
        result,
        refutation,
        "Proposed object, contradiction, or impossible precondition",
        "Refutation Route",
    )
    if process_failure_hits(object_value):
        result.errors.append(
            "OBSTRUCTION_VERIFICATION requires a mathematical object, "
            "contradiction, or impossible precondition, not process failure"
        )

    hypotheses = require_field(
        result,
        refutation,
        "Hypotheses satisfied under accepted reading",
        "Refutation Route",
    )
    if hypotheses and (
        has_unresolved_language(hypotheses)
        or not POSITIVE_HYPOTHESIS_PATTERN.search(hypotheses)
    ):
        result.errors.append(
            "OBSTRUCTION_VERIFICATION requires a positive hypotheses-satisfied audit"
        )

    conclusion = require_field(
        result,
        refutation,
        "Conclusion failure under accepted reading",
        "Refutation Route",
    )
    if conclusion and (
        has_unresolved_language(conclusion)
        or not CONCLUSION_FAILURE_PATTERN.search(conclusion)
    ):
        result.errors.append(
            "OBSTRUCTION_VERIFICATION requires a positive conclusion-failure audit"
        )

    boundary = refutation.get(canonical("Boundary/presentation dependence"), "")
    if is_blankish(boundary) or has_unresolved_language(boundary):
        result.errors.append(
            "OBSTRUCTION_VERIFICATION requires boundary/presentation dependence "
            "to be checked or explicitly absent"
        )

    refutation_text = "\n".join(refutation.values())
    hits = process_failure_hits(refutation_text)
    if hits:
        result.errors.append(
            "OBSTRUCTION_VERIFICATION refutation route still contains "
            f"process/context failure language: {', '.join(sorted(set(hits)))}"
        )


def validate_final_proof_status(
    result: ProofReviewLintResult,
    *,
    proof_route: dict[str, str],
) -> None:
    require_field(result, proof_route, "Best available proof route", "Proof Route")
    missing_key = canonical("Missing evidence, if any")
    if missing_key not in proof_route:
        result.errors.append("Proof Route is missing required field: Missing evidence, if any")
    elif not is_resolved_none(proof_route[missing_key]):
        result.errors.append("FINAL_PROOF_READY requires Missing evidence, if any: NONE")

    proof_text = "\n".join(proof_route.values())
    hits = process_failure_hits(proof_text)
    if hits:
        result.errors.append(
            "FINAL_PROOF_READY proof route still contains process/context "
            f"failure language: {', '.join(sorted(set(hits)))}"
        )


def lint_text(text: str) -> ProofReviewLintResult:
    result = ProofReviewLintResult()
    sections = read_sections(text)
    validate_sections(result, sections)
    if result.errors:
        return result

    target = parse_bullets(sections[canonical("Target Reading Check")])
    proof_route = parse_bullets(sections[canonical("Proof Route")])
    refutation = parse_bullets(sections[canonical("Refutation Route")])
    decision = parse_bullets(sections[canonical("Decision")])

    validate_decision(result, decision)
    status = result.selected_status
    if status not in ALLOWED_STATUSES:
        return result

    if status in TERMINAL_STATUSES:
        validate_terminal_common(result, target=target, decision=decision)
    if status == "OBSTRUCTION_VERIFICATION":
        validate_obstruction_status(result, refutation=refutation)
    if status == "FINAL_PROOF_READY":
        validate_final_proof_status(result, proof_route=proof_route)

    return result


def lint_file(path: Path) -> ProofReviewLintResult:
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        result = ProofReviewLintResult()
        result.errors.append(f"Cannot read proof review artifact {path}: {exc}")
        return result
    return lint_text(text)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Check that a proof-review routing artifact has one valid decision "
            "and does not turn missing context into a terminal result."
        )
    )
    parser.add_argument("proof_review", type=Path, help="Path to proof_review.md")
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print machine-readable lint output.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    result = lint_file(args.proof_review)
    if args.json:
        print(
            json.dumps(
                {
                    "ok": result.ok,
                    "errors": result.errors,
                    "warnings": result.warnings,
                    "selected_status": result.selected_status,
                },
                indent=2,
                sort_keys=True,
            )
        )
    else:
        status = "PASS" if result.ok else "FAIL"
        print(f"proof_review_lint: {status} ({args.proof_review})")
        for error in result.errors:
            print(f"ERROR: {error}")
        for warning in result.warnings:
            print(f"WARNING: {warning}")
        if result.selected_status:
            print(f"Selected status: {result.selected_status}")
    return 0 if result.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
