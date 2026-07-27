#!/usr/bin/env python3
"""Final-result contract lint for NL-Prover workspaces.

This tool is intentionally non-mathematical. It catches terminal artifacts that
present a missing route, unavailable source, or agent inability as if it were a
proof or a mathematical obstruction.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path


# Sibling lint module in the same _gate package.
from _gate import review_packet as review_packet_lint


PROCESS_FAILURE_PATTERNS = [
    (
        "gap/process-gap claim",
        re.compile(r"\b(?:gap found|process gap|workflow gap|route gap)\b", re.IGNORECASE),
    ),
    (
        "agent inability claim",
        re.compile(
            r"\b(?:cannot|can't|unable to|do not)\s+"
            r"(?:prove|establish|show|complete)\b",
            re.IGNORECASE,
        ),
    ),
    (
        "insufficient context claim",
        re.compile(
            r"\b(?:not enough|insufficient)\s+"
            r"(?:information|context|definitions|data)\b",
            re.IGNORECASE,
        ),
    ),
    (
        "missing route/source claim",
        re.compile(
            r"\b(?:definition|theorem|source|construction|route|convention|notation)\s+"
            r"(?:is\s+|are\s+)?(?:missing|unavailable|unknown|not supplied|"
            r"not provided)\b",
            re.IGNORECASE,
        ),
    ),
    (
        "undefined notation claim",
        re.compile(
            r"\b(?:symbol|term|expression|notation|object)\s+"
            r"(?:is|are|remains)?\s*(?:undefined|not defined)\b",
            re.IGNORECASE,
        ),
    ),
    (
        "no-proof claim",
        re.compile(r"\bno (?:self-contained |complete )?proof\b", re.IGNORECASE),
    ),
    (
        "stuck route claim",
        re.compile(r"\b(?:stuck|failed to find|failed to prove)\b", re.IGNORECASE),
    ),
    (
        "unresolved case claim",
        re.compile(
            r"\b(?:case|subcase|branch|regime|range)\b.{0,100}"
            r"\b(?:unresolved|unproved|unaddressed|not covered|left open|"
            r"omitted)\b",
            re.IGNORECASE,
        ),
    ),
    (
        "unresolved case claim",
        re.compile(
            r"\b(?:unresolved|unproved|unaddressed|not covered|left open|"
            r"omitted)\b.{0,100}\b(?:case|subcase|branch|regime|range)\b",
            re.IGNORECASE,
        ),
    ),
]

OBSTRUCTION_EVIDENCE = [
    (
        "concrete obstruction kind",
        re.compile(
            r"\b(?:counterexample|obstruction|contradiction|"
            r"inconsistent hypotheses|impossible precondition)\b",
            re.IGNORECASE,
        ),
    ),
    (
        "original hypotheses audit",
        re.compile(
            r"\b(?:original hypotheses|hypotheses|hypothesis)\b"
            r".{0,120}\b(?:satisf|audit|checked|hold)\b",
            re.IGNORECASE | re.DOTALL,
        ),
    ),
    (
        "target conclusion failure",
        re.compile(
            r"\b(?:conclusion|target conclusion|target)\b"
            r".{0,120}\b(?:fails?|false|does not hold|violated)\b",
            re.IGNORECASE | re.DOTALL,
        ),
    ),
]

TERMINAL_OBSTRUCTION_PATTERNS = [
    (
        "target false/defective claim",
        re.compile(
            r"\b(?:therefore|hence|thus|so|we conclude|this shows|"
            r"the conclusion is)\b.{0,100}"
            r"\b(?:statement|claim|theorem|target|assertion|problem)\b.{0,100}"
            r"\b(?:false|fails?|invalid|ill-posed|not well-posed|"
            r"unprovable|cannot be true|defective)\b",
            re.IGNORECASE,
        ),
    ),
    (
        "counterexample conclusion claim",
        re.compile(
            r"\b(?:counterexample|obstruction)\b.{0,160}"
            r"\b(?:satisf\w*|meets?|obeys?|fulfills?|has)\b.{0,160}"
            r"\b(?:hypotheses|assumptions|conditions)\b.{0,160}"
            r"\b(?:conclusion|target|claim)\b.{0,100}"
            r"\b(?:fails?|false|violated|does not hold)\b",
            re.IGNORECASE,
        ),
    ),
]


@dataclass
class RouteFailure:
    label: str
    line_no: int
    line: str


@dataclass
class ContractResult:
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    route_failures: list[RouteFailure] = field(default_factory=list)
    terminal_obstruction_claims: list[RouteFailure] = field(default_factory=list)
    packets_checked: list[str] = field(default_factory=list)
    obstruction_packets: list[str] = field(default_factory=list)

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


def iter_result_lines(text: str):
    """Yield proof/result lines while skipping the copied problem statement."""

    in_problem_statement = False
    for line_no, line in enumerate(text.splitlines(), start=1):
        section = re.match(r"\s*\\section\{([^}]*)\}", line)
        if section:
            in_problem_statement = "problem statement" in section.group(1).casefold()
        if in_problem_statement:
            continue
        yield line_no, line


def find_process_failures(text: str) -> list[RouteFailure]:
    failures: list[RouteFailure] = []
    for line_no, line in iter_result_lines(text):
        stripped = line.strip()
        if not stripped:
            continue
        for label, pattern in PROCESS_FAILURE_PATTERNS:
            if pattern.search(stripped):
                failures.append(RouteFailure(label=label, line_no=line_no, line=stripped))
                break
        if len(failures) == 8:
            break
    return failures


def find_terminal_obstruction_claims(text: str) -> list[RouteFailure]:
    claims: list[RouteFailure] = []
    for line_no, line in iter_result_lines(text):
        stripped = line.strip()
        if not stripped:
            continue
        if re.search(
            r"\b(?:no|not|without)\b.{0,40}\b(?:counterexample|obstruction)\b",
            stripped,
            re.IGNORECASE,
        ):
            continue
        for label, pattern in TERMINAL_OBSTRUCTION_PATTERNS:
            if pattern.search(stripped):
                claims.append(RouteFailure(label=label, line_no=line_no, line=stripped))
                break
        if len(claims) == 8:
            break
    return claims


def validate_no_process_failure(result: ContractResult, proof_path: Path) -> None:
    if not proof_path.exists():
        result.errors.append(f"Missing proof file: {proof_path}")
        return
    try:
        proof_text = proof_path.read_text(encoding="utf-8")
    except OSError as exc:
        result.errors.append(f"Cannot read proof file {proof_path}: {exc}")
        return
    for failure in find_process_failures(proof_text):
        result.route_failures.append(failure)
        result.errors.append(
            f"proof.tex line {failure.line_no} has {failure.label}: {failure.line!r}"
        )
    result.terminal_obstruction_claims.extend(
        find_terminal_obstruction_claims(proof_text)
    )


def validate_terminal_obstruction_certificate(result: ContractResult) -> None:
    if not result.terminal_obstruction_claims or result.obstruction_packets:
        return
    for claim in result.terminal_obstruction_claims:
        result.errors.append(
            f"proof.tex line {claim.line_no} has uncertified {claim.label}: "
            f"{claim.line!r}; supply a fresh accepted obstruction review packet "
            "via --packet or route the claim as restart state"
        )


def has_obstruction_evidence(text: str) -> list[str]:
    missing: list[str] = []
    for label, pattern in OBSTRUCTION_EVIDENCE:
        if not pattern.search(text):
            missing.append(label)
    return missing


def validate_obstruction_packet(result: ContractResult, packet_path: Path) -> None:
    lint = review_packet_lint.lint_file(packet_path, mode="obstruction")
    result.packets_checked.append(str(packet_path))
    for error in lint.errors:
        result.errors.append(f"{packet_path}: {error}")
    for warning in lint.warnings:
        result.warnings.append(f"{packet_path}: {warning}")

    try:
        text = packet_path.read_text(encoding="utf-8")
    except OSError as exc:
        result.errors.append(f"Cannot read obstruction packet {packet_path}: {exc}")
        return

    missing = has_obstruction_evidence(text)
    if missing:
        result.errors.append(
            f"{packet_path}: accepted obstruction lacks positive evidence for "
            + ", ".join(missing)
        )


def inspect_extra_packet(result: ContractResult, packet_path: Path) -> None:
    try:
        text = packet_path.read_text(encoding="utf-8")
    except OSError as exc:
        result.errors.append(f"Cannot read packet {packet_path}: {exc}")
        return
    next_action = first_content_line(read_sections(text).get(canonical("Next Action"), ""))
    if next_action.upper() == "ACCEPT_OBSTRUCTION":
        result.obstruction_packets.append(str(packet_path))
        validate_obstruction_packet(result, packet_path)


def lint_workspace(
    workspace: Path,
    extra_packets: list[Path] | None = None,
) -> ContractResult:
    result = ContractResult()
    workspace = workspace.resolve()
    validate_no_process_failure(result, workspace / "proof.tex")

    for packet in extra_packets or []:
        packet_path = packet if packet.is_absolute() else workspace / packet
        inspect_extra_packet(result, packet_path)

    validate_terminal_obstruction_certificate(result)

    return result


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Check that final NL-Prover artifacts do not present a missing "
            "route or process failure as a mathematical result."
        )
    )
    parser.add_argument(
        "workspace",
        type=Path,
        help="Problem workspace containing proof.tex.",
    )
    parser.add_argument(
        "--packet",
        action="append",
        default=[],
        type=Path,
        help="Additional refined-proof or obstruction review packet to inspect.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print machine-readable lint output.",
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
                    "route_failures": [
                        {
                            "label": failure.label,
                            "line": failure.line_no,
                            "text": failure.line,
                        }
                        for failure in result.route_failures
                    ],
                    "terminal_obstruction_claims": [
                        {
                            "label": claim.label,
                            "line": claim.line_no,
                            "text": claim.line,
                        }
                        for claim in result.terminal_obstruction_claims
                    ],
                    "packets_checked": result.packets_checked,
                    "obstruction_packets": result.obstruction_packets,
                },
                indent=2,
                sort_keys=True,
            )
        )
    else:
        status = "PASS" if result.ok else "FAIL"
        print(f"result_contract_lint: {status} ({args.workspace})")
        for error in result.errors:
            print(f"ERROR: {error}")
        for warning in result.warnings:
            print(f"WARNING: {warning}")
        if result.obstruction_packets:
            print("Obstruction packets checked:")
            for packet in result.obstruction_packets:
                print(f"- {packet}")
    return 0 if result.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
