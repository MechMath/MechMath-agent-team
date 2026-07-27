#!/usr/bin/env python3
"""Structural lint for NL-Prover generator proof attempts.

This tool checks whether a generator artifact has the restartable proof-attempt
shape expected before it is sent to a Verifier. It does not check mathematics.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from _workspace import ledger as _ledger  # noqa: E402

CLAIM_ID_RE = re.compile(r"claim[_ ]?id\s*[:=]\s*([A-Za-z0-9._-]+)", re.IGNORECASE)


REQUIRED_PROOF_SECTIONS = [
    "Setup",
    "Proof",
    "Hypotheses and Preconditions Audit",
]

REQUIRED_AUDIT_SUBSECTIONS = [
    "Lemma Statement Hypotheses",
    "Dependency Lemmas Used",
    "Theorem Preconditions Used",
    "Definitions and Notation Used",
    "Problem Reading and Normalization",
    "Proof Obligations",
    "Load-Bearing Obligation Ledger",
    "Added or Strengthened Hypotheses",
]

PENDING_PATTERNS = [
    ("explicit pending marker", re.compile(r"\b(?:TODO|FIXME|TBD)\b")),
    ("LaTeX pending proof marker", re.compile(r"\\sorry(?:\b|\{)")),
    ("human-review marker", re.compile(r"\[/?human-review\]", re.IGNORECASE)),
    (
        "template placeholder",
        re.compile(r"<[^>\n]*(?:proof|statement|lemma|theorem|path|name)[^>\n]*>"),
    ),
]

ROUTE_FAILURE_PATTERNS = [
    re.compile(r"\bgap found\b", re.IGNORECASE),
    re.compile(r"\bnot enough (?:information|context|definitions)\b", re.IGNORECASE),
    re.compile(r"\binsufficient (?:information|context|definitions)\b", re.IGNORECASE),
    re.compile(r"\b(?:cannot|can't|unable to)\s+(?:prove|establish|show|complete)\b", re.IGNORECASE),
    re.compile(
        r"\b(?:definition|theorem|source|construction|route)\s+"
        r"(?:is\s+)?(?:missing|unavailable|unknown)\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"\b(?:symbol|term|expression|notation|object)\s+"
        r"(?:is|are|remains)?\s*(?:undefined|not defined)\b",
        re.IGNORECASE,
    ),
    re.compile(r"\bno (?:self-contained )?proof\b", re.IGNORECASE),
]

THEOREM_LIKE_CITATION_PATTERNS = [
    re.compile(
        r"\bby\s+(?:the\s+|a\s+)?(?:standard|classical|well-known|known|usual)\s+"
        r"(?:theorem|lemma|proposition|result|estimate|bound|inequality|"
        r"criterion|classification|regularity)\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"\b(?:use|apply|invoke|appeal to)\s+(?:the\s+|a\s+)?"
        r"(?:standard|classical|well-known|known|usual)\s+"
        r"(?:theorem|lemma|proposition|result|estimate|bound|inequality|"
        r"criterion|classification|regularity)\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"\bby\s+(?:the\s+)?[A-Z][A-Za-z0-9'_-]*"
        r"(?:[/ -][A-Z][A-Za-z0-9'_-]*){0,3}(?:'s)?\s+"
        r"(?:theorem|lemma|proposition|result|estimate|bound|inequality|"
        r"criterion|classification|regularity)\b",
    ),
    re.compile(
        r"\b(?:theorem|lemma|proposition|result|estimate|bound|inequality|"
        r"criterion|classification|regularity)\s+of\s+"
        r"[A-Z][A-Za-z0-9'_-]*(?:[/ -][A-Z][A-Za-z0-9'_-]*){0,3}\b",
    ),
]

CIRCULAR_DEFINITION_PATTERNS = [
    re.compile(
        r"\b(?:define|defines|defined|set|declare|take)\b.{0,160}"
        r"\b(?:to be|as|by|via)\b.{0,160}"
        r"\b(?:iff|if and only if|exactly when|precisely when|"
        r"criterion|characterization|condition|satisfying|such that)\b",
        re.IGNORECASE,
    ),
]

TAUTOLOGICAL_PROOF_PATTERNS = [
    re.compile(
        r"\b(?:by|from|after)\s+(?:the\s+)?"
        r"(?:definition|definitions|unfolding|unwinding)\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"\b(?:tautolog(?:y|ical)|is exactly the definition|"
        r"nothing remains to prove|nothing to prove)\b",
        re.IGNORECASE,
    ),
]

INDEPENDENT_DEFINITION_AUDIT_PATTERNS = [
    re.compile(
        r"\b(?:accepted|external|independent|source|problem|dependency|"
        r"research|kb-manager|human)\b.{0,100}\bdefinition\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"\bdefinition\b.{0,100}\b(?:accepted|external|independent|source|"
        r"problem|dependency|research|kb-manager|human)\b",
        re.IGNORECASE,
    ),
]

BAD_STATUS_TOKENS = {
    "assigned",
    "blocked",
    "blocker",
    "fail",
    "failed",
    "missing",
    "open",
    "pending",
    "stuck",
    "todo",
    "unresolved",
    "unjustified",
}

COMPLETED_STATUS_TOKENS = {"done", "complete", "completed", "proved", "resolved"}
STUCK_STATUS_TOKENS = {"stuck", "blocked", "in_progress", "needs_revision"}


@dataclass
class LintResult:
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    proof_status: str | None = None
    completion_classification: str | None = None

    @property
    def ok(self) -> bool:
        return not self.errors


@dataclass
class ProofSignals:
    unresolved_ledger_rows: list[str] = field(default_factory=list)
    route_failure_lines: list[str] = field(default_factory=list)
    theorem_like_citation_lines: list[str] = field(default_factory=list)
    circular_definition_lines: list[str] = field(default_factory=list)
    added_hypotheses: str = ""
    remaining_obligations: str = ""
    audited_obstruction: bool = False


def canonical(name: str) -> str:
    return re.sub(r"\s+", " ", name.strip()).casefold()


def read_sections(text: str, level: int = 2) -> dict[str, str]:
    sections: dict[str, list[str]] = {}
    current: str | None = None
    pattern = re.compile(rf"^{'#' * level}\s+(.+?)\s*$")
    for line in text.splitlines():
        match = pattern.match(line)
        if match:
            current = canonical(match.group(1))
            sections.setdefault(current, [])
            continue
        if current is not None:
            sections[current].append(line)
    return {name: "\n".join(lines).strip() for name, lines in sections.items()}


def read_subsections(section: str, level: int = 3) -> dict[str, str]:
    return read_sections(section, level=level)


def content_lines(section: str) -> list[str]:
    return [
        line.strip()
        for line in section.splitlines()
        if line.strip() and not line.strip().startswith("<!--")
    ]


def is_none_or_empty(section: str) -> bool:
    lines = content_lines(section)
    return not lines or (len(lines) == 1 and lines[0].upper() == "NONE")


def first_content_line(section: str) -> str:
    lines = content_lines(section)
    return lines[0] if lines else ""


def parse_bullets(section: str) -> dict[str, str]:
    values: dict[str, str] = {}
    for line in section.splitlines():
        match = re.match(r"^\s*[-*]\s*([^:]+):\s*(.*?)\s*$", line)
        if match:
            values[canonical(match.group(1))] = match.group(2).strip()
    return values


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


def row_status(row: dict[str, str]) -> str:
    if "status" in row:
        return row["status"].strip()
    if "current status" in row:
        return row["current status"].strip()
    if row:
        return next(reversed(row.values())).strip()
    return ""


def first_matching_lines(text: str, patterns: list[re.Pattern[str]]) -> list[str]:
    matches: list[str] = []
    for line in text.splitlines():
        stripped = line.strip()
        if any(pattern.search(stripped) for pattern in patterns):
            matches.append(stripped)
            if len(matches) == 5:
                break
    return matches


def has_any_match(text: str, patterns: list[re.Pattern[str]]) -> bool:
    return any(pattern.search(text) for pattern in patterns)


def has_audited_obstruction(text: str) -> bool:
    lower = text.casefold()
    has_obstruction = "counterexample" in lower or "obstruction" in lower
    hypothesis_audit = re.search(r"hypoth(?:esis|eses).{0,80}satisf", lower)
    conclusion_failure = re.search(r"conclusion.{0,80}(?:fail|false|does not hold)", lower)
    accepted_reading = "accepted definition" in lower or "accepted reading" in lower
    return bool(has_obstruction and hypothesis_audit and conclusion_failure and accepted_reading)


def has_independent_definition_audit(section: str) -> bool:
    return has_any_match(section, INDEPENDENT_DEFINITION_AUDIT_PATTERNS)


def lint_proof_text(text: str) -> tuple[LintResult, ProofSignals]:
    result = LintResult()
    signals = ProofSignals(audited_obstruction=has_audited_obstruction(text))

    sections = read_sections(text, level=2)
    for section in REQUIRED_PROOF_SECTIONS:
        if canonical(section) not in sections:
            result.errors.append(f"Missing proof section: {section}")

    for label, pattern in PENDING_PATTERNS:
        match = pattern.search(text)
        if match:
            line_no = text[: match.start()].count("\n") + 1
            result.errors.append(f"proof attempt has {label} at line {line_no}")

    audit = sections.get(canonical("Hypotheses and Preconditions Audit"), "")
    audit_subsections = read_subsections(audit, level=3)
    for section in REQUIRED_AUDIT_SUBSECTIONS:
        if canonical(section) not in audit_subsections:
            result.errors.append(f"Missing audit subsection: {section}")

    proof_obligations = audit_subsections.get(canonical("Proof Obligations"), "")
    proof_obligation_bullets = parse_bullets(proof_obligations)
    signals.remaining_obligations = proof_obligation_bullets.get(
        canonical("Remaining obligations"),
        proof_obligations,
    )
    source_theorem_obligations = proof_obligation_bullets.get(
        canonical("Source theorem obligations invoked"),
        "",
    )

    dependency_lemmas = audit_subsections.get(canonical("Dependency Lemmas Used"), "")
    theorem_preconditions = audit_subsections.get(
        canonical("Theorem Preconditions Used"),
        "",
    )
    definitions_used = audit_subsections.get(canonical("Definitions and Notation Used"), "")

    proof_body = sections.get(canonical("Proof"), "")
    signals.theorem_like_citation_lines = first_matching_lines(
        proof_body,
        THEOREM_LIKE_CITATION_PATTERNS,
    )
    has_theorem_or_dependency_audit = (
        not is_none_or_empty(dependency_lemmas)
        or not is_none_or_empty(theorem_preconditions)
        or not is_none_or_empty(source_theorem_obligations)
    )
    if signals.theorem_like_citation_lines and not has_theorem_or_dependency_audit:
        result.errors.append(
            "theorem-like citation in proof body requires Dependency Lemmas Used, "
            "Theorem Preconditions Used, or Source theorem obligations invoked "
            "to record the exact statement and preconditions"
        )

    ledger = audit_subsections.get(canonical("Load-Bearing Obligation Ledger"), "")
    for index, row in enumerate(parse_markdown_table(ledger), start=1):
        status = row_status(row)
        if status_tokens(status) & BAD_STATUS_TOKENS:
            signals.unresolved_ledger_rows.append(f"row {index}: {status}")

    added = audit_subsections.get(canonical("Added or Strengthened Hypotheses"), "")
    signals.added_hypotheses = first_content_line(added)

    tail = "\n".join(text.splitlines()[-40:])
    conclusion = sections.get(canonical("Conclusion"), "")
    route_scope = "\n".join(part for part in [conclusion, tail] if part)
    signals.route_failure_lines = first_matching_lines(
        route_scope,
        ROUTE_FAILURE_PATTERNS,
    )
    if signals.route_failure_lines and not signals.audited_obstruction:
        result.errors.append(
            "proof attempt presents a route-failure or missing-context claim near "
            "the conclusion without an audited counterexample/obstruction"
        )

    definition_scope = "\n".join(
        part
        for part in [
            sections.get(canonical("Setup"), ""),
            proof_body,
            conclusion,
            tail,
        ]
        if part
    )
    signals.circular_definition_lines = first_matching_lines(
        definition_scope,
        CIRCULAR_DEFINITION_PATTERNS,
    )
    has_tautological_finish = has_any_match(
        definition_scope,
        TAUTOLOGICAL_PROOF_PATTERNS,
    )
    if (
        signals.circular_definition_lines
        and has_tautological_finish
        and not has_independent_definition_audit(definitions_used)
    ):
        result.errors.append(
            "potential theorem-as-definition circularity: a definition appears "
            "to be introduced by the target criterion and then used tautologically; "
            "Definitions and Notation Used must name an accepted independent "
            "definition source"
        )

    return result, signals


def parse_status_value(text: str) -> str | None:
    match = re.search(r"^##\s*Status:\s*(.+?)\s*$", text, re.MULTILINE)
    if match:
        return match.group(1).strip()
    sections = read_sections(text, level=2)
    status_section = sections.get(canonical("Status"), "")
    if status_section:
        return content_lines(status_section)[0] if content_lines(status_section) else None
    return None


def parse_completion_classification(text: str) -> str | None:
    sections = read_sections(text, level=2)
    section = sections.get(canonical("Completion Classification"), "")
    lines = content_lines(section)
    return lines[0] if lines else None


def lint_status_text(
    text: str,
    *,
    result: LintResult,
    signals: ProofSignals,
) -> None:
    status = parse_status_value(text)
    classification = parse_completion_classification(text)
    result.proof_status = status
    result.completion_classification = classification

    if not status:
        result.errors.append("status file is missing a Status value")
        return

    tokens = status_tokens(status)
    done = bool(tokens & COMPLETED_STATUS_TOKENS)
    stuck_or_active = bool(tokens & STUCK_STATUS_TOKENS)

    sections = read_sections(text, level=2)
    status_obligations = sections.get(canonical("Proof Obligations"), "")
    status_ledger = sections.get(canonical("Load-Bearing Obligation Ledger"), "")
    status_notes = sections.get(canonical("Notes"), "")

    status_unresolved_rows = [
        f"row {index}: {row_status(row)}"
        for index, row in enumerate(parse_markdown_table(status_ledger), start=1)
        if status_tokens(row_status(row)) & BAD_STATUS_TOKENS
    ]

    if done:
        if signals.unresolved_ledger_rows:
            result.errors.append(
                "done status cannot accompany unresolved proof ledger rows: "
                + "; ".join(signals.unresolved_ledger_rows)
            )
        if status_unresolved_rows:
            result.errors.append(
                "done status cannot accompany unresolved status ledger rows: "
                + "; ".join(status_unresolved_rows)
            )
        if not is_none_or_empty(status_obligations):
            result.errors.append("done status requires Proof Obligations to be NONE")
        if not is_none_or_empty(signals.remaining_obligations):
            result.errors.append("done status requires proof Remaining obligations to be NONE")
        if not is_none_or_empty(signals.added_hypotheses):
            result.errors.append("done status cannot include added or strengthened hypotheses")
        if classification and "restartable incomplete" in classification.casefold():
            result.errors.append("done status conflicts with restartable incomplete classification")

    if stuck_or_active:
        has_restart_detail = (
            not is_none_or_empty(status_obligations)
            or status_unresolved_rows
            or not is_none_or_empty(status_notes)
        )
        if not has_restart_detail:
            result.errors.append(
                "stuck/in-progress status must name a proof obligation, ledger item, or note"
            )

    if signals.route_failure_lines and not stuck_or_active and not signals.audited_obstruction:
        result.errors.append(
            "route-failure language requires a stuck/in-progress status or an audited obstruction"
        )


def check_ledger(text: str, signals: ProofSignals, workspace: Path, result: LintResult) -> None:
    """Cross-check theorem-like citations against the provenance ledger (ADR 0019 §1).

    A theorem-like citation in the proof body must name a `claim_id` that resolves
    to a ledger row whose trust is not `pending-audit`. `borrowed` passes with a
    warning (an unresolved obligation the final gate will enforce).
    """
    if not signals.theorem_like_citation_lines:
        return
    claim_ids = CLAIM_ID_RE.findall(text)
    if not claim_ids:
        result.errors.append(
            "theorem-like citation in proof body requires a `claim_id: <id>` "
            "recorded against references/ledger.jsonl (ADR 0019)"
        )
        return
    try:
        rows = {r.get("claim_id"): r for r in _ledger.load_rows(workspace)}
    except ValueError as exc:
        result.errors.append(f"cannot read provenance ledger: {exc}")
        return
    for cid in claim_ids:
        row = rows.get(cid)
        if row is None:
            result.errors.append(f"claim_id {cid!r} is not recorded in references/ledger.jsonl")
            continue
        trust = row.get("trust")
        if trust == "pending-audit":
            result.errors.append(
                f"claim_id {cid!r} is still pending-audit; dispatch a fresh Verifier "
                "before using it as a load-bearing step (ADR 0019 §2)"
            )
        elif trust == "borrowed":
            result.warnings.append(
                f"claim_id {cid!r} is borrowed (unresolved verification obligation); "
                "it must be discharged before the final article gate (ADR 0019 §2/§5)"
            )


def lint_files(
    proof_path: Path,
    status_path: Path | None = None,
    ledger_workspace: Path | None = None,
) -> LintResult:
    try:
        text = proof_path.read_text(encoding="utf-8")
    except OSError as exc:
        result = LintResult()
        result.errors.append(f"Cannot read proof attempt {proof_path}: {exc}")
        return result

    result, signals = lint_proof_text(text)

    if ledger_workspace is not None:
        check_ledger(text, signals, ledger_workspace, result)

    if status_path is not None:
        try:
            status_text = status_path.read_text(encoding="utf-8")
        except OSError as exc:
            result.errors.append(f"Cannot read status file {status_path}: {exc}")
            return result
        lint_status_text(status_text, result=result, signals=signals)
    elif signals.unresolved_ledger_rows:
        result.errors.append(
            "unresolved proof ledger rows require a status file: "
            + "; ".join(signals.unresolved_ledger_rows)
        )

    return result


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Lint an NL-Prover generator proof attempt for shape readiness."
    )
    parser.add_argument("proof", type=Path, help="Path to proof_v<N>.md")
    parser.add_argument(
        "--status",
        type=Path,
        help="Optional generator/status.md to cross-check completion state.",
    )
    parser.add_argument(
        "--ledger",
        type=Path,
        metavar="WORKSPACE",
        help="Workspace root; cross-check theorem-like citations against "
        "references/ledger.jsonl (ADR 0019).",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print machine-readable lint output.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    result = lint_files(args.proof, status_path=args.status, ledger_workspace=args.ledger)

    if args.json:
        print(
            json.dumps(
                {
                    "ok": result.ok,
                    "proof_status": result.proof_status,
                    "completion_classification": result.completion_classification,
                    "errors": result.errors,
                    "warnings": result.warnings,
                },
                indent=2,
                sort_keys=True,
            )
        )
    else:
        status = "PASS" if result.ok else "FAIL"
        print(f"proof_attempt_lint: {status} ({args.proof})")
        for error in result.errors:
            print(f"ERROR: {error}")
        for warning in result.warnings:
            print(f"WARNING: {warning}")
    return 0 if result.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
