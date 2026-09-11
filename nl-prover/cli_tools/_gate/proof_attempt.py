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

from _gate import waiver

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
    # "no proof of X here" is a route-failure claim. "carries no proof weight"
    # is the invariant-16 disclaimer every discovery artifact is required to
    # write, so the noun phrase has to be excluded or the mandated sentence
    # trips a blocking check (observed: several agents hit this in one run).
    re.compile(
        r"\bno (?:self-contained )?proof\b(?!\s+(?:weight|value|force|status|obligation))",
        re.IGNORECASE,
    ),
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


REQUIREMENT = waiver.requirement_text(
    checks='the shape of a generator proof attempt: required sections, obligation ledger\nentries for load-bearing steps, and hedging that leaves a step unjustified.',
    legal='each load-bearing estimate, construction, theorem input, case split, bridge,\nand assembly step appears in the obligation ledger before it supports a proof',
    fix='Add the missing ledger entry, or justify the step. Hedged-language findings\nare warnings and do not block.',
)

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


def lint_preamble_is_mathematics(text: str) -> list[str]:
    """The block before the first `##` must not be a change log.

    Measured on the worst lemma in the corpus: that block went from 11 lines in
    `proof_v1.md` to 946 lines (61 KB) in `proof_v11.md`, an accumulated stack
    of per-round change logs each describing the one before it — 60 KB of the
    file's 92 KB total growth. Its own text says *"No mathematics is touched in
    v11"*, and the same for v10. Two rounds and two fresh verifications of a
    156 KB document, for no mathematics.

    It is also a correctness problem, not only a cost one: a change log is
    content the Verifier must certify, and v10's single blocking issue was a
    false attribution inside that front matter. A claim that cannot be made
    cannot be made falsely.

    A warning, not an error. A preamble that is long because the statement is
    long is legitimate, and this check cannot tell the difference — it reports
    the shape and names what to do about it.
    """
    lines = text.splitlines()
    end = len(lines)
    for index, line in enumerate(lines):
        if re.match(r"^#{2,} ", line):
            end = index
            break
    preamble = lines[:end]
    if len(preamble) <= PREAMBLE_LINE_BUDGET:
        return []
    body = "\n".join(preamble)
    hits = sorted({match.group(0).lower() for match in CHANGE_LOG_PATTERN.finditer(body)})
    if not hits:
        return [
            f"the block before the first '##' is {len(preamble)} lines "
            f"(budget {PREAMBLE_LINE_BUDGET}) — check it is the statement and not accreted prose"
        ]
    return [
        f"the block before the first '##' is {len(preamble)} lines and reads as a change log "
        f"({', '.join(hits[:4])}) — move it to response_to_verifier.md. The Verifier is "
        f"stateless (ADR 0003): it never read the previous version and must not be told "
        f"what changed (prompts/generator.md)"
    ]


# Deliberately narrow. These are phrases about the revision process, not about
# mathematics; a proof that needs them is describing its own history.
CHANGE_LOG_PATTERN = re.compile(
    r"what changed in v\d+|no mathematics is touched|"
    r"what v\d+ (?:removes|adds|repairs)|change[- ]log|"
    r"round[- ]\d+ verifier|previous verifier|in response to the verifier",
    re.IGNORECASE,
)
PREAMBLE_LINE_BUDGET = 60


def lint_proof_text(text: str) -> tuple[LintResult, ProofSignals]:
    result = LintResult()
    signals = ProofSignals(audited_obstruction=has_audited_obstruction(text))
    result.warnings.extend(lint_preamble_is_mathematics(text))

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


# `lemmas/<...>/generator/proof_v<N>.md` -> the sibling verifier directory and
# the round number, so the companion packet can be located without being told.
GENERATOR_PROOF = re.compile(r"^proof_v(\d+)([a-z]?)\.md$")

# How a discovery-mode artifact announces itself, in its opening lines. Same
# form the discovery gate reads; the region is a property of the artifact.
DISCOVERY_HEADER = re.compile(
    r"\bmode\b\W{0,6}\**\s*discovery\b|\bDISCOVERY\b\s*[-\u2014\u2013]", re.I
)
HEADER_LINES = 15


def declares_discovery(text: str) -> bool:
    return bool(DISCOVERY_HEADER.search("\n".join(text.splitlines()[:HEADER_LINES])))


def companion_packet(proof_path: Path) -> Path | None:
    """The review packet for this exact round, or None if the path is not a
    generator proof attempt and the packet therefore cannot be located."""
    match = GENERATOR_PROOF.match(proof_path.name)
    if not match or proof_path.parent.name != "generator":
        return None
    lemma_dir = proof_path.parent.parent
    return lemma_dir / "verifier" / f"review_packet_v{match.group(1)}{match.group(2)}.md"


def check_verified_before_handoff(
    result: LintResult, proof_path: Path, text: str
) -> None:
    """In certification, an artifact arrives with a verdict or it does not arrive.

    The producer used to write the proof, lint its shape, and hand it to the
    Orchestrator, which dispatched a Verifier and passed the packet back. The
    check itself is unchanged and there is still exactly one of it per round —
    what moves is who starts it. Every round trip through the hub costs a
    dispatch, and the dispatch is the unit the wall clock is made of.

    Discovery artifacts are exempt, and not as a convenience: discovery output
    discharges no proof obligation and causes no state transition, so a verdict
    on it would be a category error.

    This is refusable like every other check here: `--waive REASON`. If the
    cold-start verifier is unavailable, that is what a waiver is for, and the
    waiver log is what tells us the route is not working.
    """
    if declares_discovery(text):
        return
    packet = companion_packet(proof_path)
    if packet is None or packet.exists():
        return
    result.errors.append(
        f"certification-mode proof attempt with no verifier packet at {packet}. "
        "Get one before handing this over: "
        f"`uv run python cli_tools/verify.py dispatch {proof_path} --mode certification "
        "--verification-mode lemma --statement <statement.md> --problem <problem.md> "
        f"--output-dir {packet.parent} --workspace <workspace> --run`"
        " -- and note `--run`, without which it prints the dispatch and writes no "
        "packet, which is the loop this message exists to break. Or ask the "
        "Orchestrator for a fresh Verifier "
        "subagent — they are the same check. If the artifact is conjectural, say so with "
        "a discovery-mode header and this stops applying."
    )


def lint_files(
    proof_path: Path,
    status_path: Path | None = None,
    ledger_workspace: Path | None = None,
    require_verdict: bool = True,
) -> LintResult:
    try:
        text = proof_path.read_text(encoding="utf-8")
    except OSError as exc:
        result = LintResult()
        result.errors.append(f"Cannot read proof attempt {proof_path}: {exc}")
        return result

    result, signals = lint_proof_text(text)

    if require_verdict:
        check_verified_before_handoff(result, proof_path, text)

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
        description="Lint an NL-Prover generator proof attempt for shape readiness.",
        epilog=REQUIREMENT,
        formatter_class=argparse.RawDescriptionHelpFormatter,
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
        "--no-verdict-required",
        action="store_true",
        help="Skip the check that a certification-mode attempt already has its "
        "verifier packet. For linting a draft mid-write; not for handing one over.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print machine-readable lint output.",
    )
    waiver.add_waiver_arg(parser)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    result = lint_files(
        args.proof,
        status_path=args.status,
        ledger_workspace=args.ledger,
        require_verdict=not args.no_verdict_required,
    )

    # Waive before reporting. Reporting first published a verdict computed
    # before the waiver was applied, so `--json` listed errors the waiver
    # had already excused and carried an `ok` that disagreed with the
    # human output on the same run. The two views are one computation.
    result.errors, _waived = waiver.apply_waiver(
        result.errors, args.waive, gate="proof-attempt",
        workspace=None,
    )
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
    if not args.json:
        waiver.print_waived(_waived, args.waive or "")
    if result.errors and not args.json:
        # Prose after a JSON document makes the document unparseable exactly
        # when it carries something to report. Six of the ten gates did this;
        # only the ones that happened to pass on the workspace they were tried
        # against looked healthy.
        print()
        print(REQUIREMENT)
    return 0 if result.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
