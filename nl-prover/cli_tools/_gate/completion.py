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

from _gate import waiver


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

# The STATUS.md section that lets a run declare a lemma directory dead on
# purpose. Without it the only way to silence the reconciliation error would be
# to delete the directory, and a superseded statement is evidence worth keeping.
SUPERSEDED_SECTION = "Superseded Lemma Directories"

# Prefixes runs put on a lemma id in prose that never reach the directory name.
LEMMA_ID_PREFIX = re.compile(r"^(?:lem|def|thm|cor|prop)[:_-]", re.IGNORECASE)

# A token that looks like an identifier rather than a word of English: it
# carries a separator no prose word would. "Global terminal proof" is a summary
# label for a whole assembly and names no directory; `post-e8-final-assembly`
# does.
IDENTIFIER_TOKEN = re.compile(r"[A-Za-z0-9]+[_:./-][\w:./-]*")

# How a superseded bullet separates the directory from the reason it died.
SUPERSEDED_REASON = re.compile(r"\s+[—–-]\s+|:\s+")

# Directories under lemmas/ that are not lemmas.
LEMMA_DIR_SKIP = {"__pycache__"}

# How deep under lemmas/ a lemma directory may sit. Runs group lemmas by branch
# (`lemmas/<branch>/<lemma>/`), so a one-level scan reports the branch folders as
# nodes and finds no statements on them. The cap stops a stray tree from being
# walked forever; nothing observed goes past two.
LEMMA_MAX_DEPTH = 3


@dataclass
class GateResult:
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    packets_checked: list[str] = field(default_factory=list)
    lemma_reconciliation: dict = field(default_factory=dict)

    @property
    def ok(self) -> bool:
        return not self.errors


REQUIREMENT = waiver.requirement_text(
    checks=(
        'proof.tex and STATUS.md readiness before a final answer: required sections,\n'
        'review-packet coverage for load-bearing steps, and language that presents a\n'
        'pending or missing item as finished.\n'
        'The lemmas/ directory listing against the Lemma Status table: every lemma\n'
        'directory on disk must be accounted for in STATUS.md.'
    ),
    legal=(
        'status tokens: resolved | pending | open\n'
        'every load-bearing lemma needs a passing review packet cited by path\n'
        'every lemmas/<id>/ needs a Lemma Status row or a\n'
        f"  '## {SUPERSEDED_SECTION}' bullet naming it and the reason"
    ),
    fix=(
        'Cite the missing review packet, or change the claim to match what is\n'
        'actually verified. Language flagged as pending is a warning, not a block.\n'
        f"An unaccounted lemma directory: add its Lemma Status row, or a '## {SUPERSEDED_SECTION}'\n"
        '  bullet reading `- <id> — why it was abandoned`. Do not delete the directory\n'
        '  to silence this; a superseded statement is evidence.'
    ),
)

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


# Two tracking dialects exist in the corpus and they track different objects.
# `## Lemma Status` is a table of lemma directories; `## Active Branch Queue` is
# a table of routes. Census of 54 STATUS.md: 6 carry only the first, 18 only the
# second, 22 both, 8 neither -- and 19 have lemma directories with no Lemma
# Status section at all, the newest run in the corpus among them.
#
# The branch queue is not a substitute: a run tracking only routes has no
# lemma-level accounting, and that is a real gap, not a parser problem. What was
# wrong is that the gate reported the gap once per directory, at the end. It
# reports it once, and `gate dag` now reports it while the run is still going.
BRANCH_QUEUE_SECTION = "Active Branch Queue"


def tracking_dialect(sections: dict[str, str]) -> str:
    """Which table this STATUS.md uses to track proof work."""
    has_lemma = canonical("Lemma Status") in sections
    has_queue = canonical(BRANCH_QUEUE_SECTION) in sections
    if has_lemma and has_queue:
        return "both"
    if has_lemma:
        return "lemma-status"
    if has_queue:
        return "branch-queue"
    return "none"


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
        # Process-language findings are advisory (ADR 0023 P.1): the regex
        # cannot tell an honest "this round did not prove X" from a false
        # claim, and the two error directions cost very differently --
        # a miss is one uncaught line, a false positive blocks a correct route.
            result.warnings.append(f"proof.tex has {label} at line {line_no}")


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


# A STATUS.md line claiming an artifact was retained, with the path it names.
RETENTION_CLAIM = re.compile(
    r"\b(?:retain(?:ed|s)?|preserv(?:ed|es)|kept)\b[^\n]{0,120}?"
    r"[`\"]?((?:[\w.\-]+/)+[\w.\-]+\.(?:tex|md|json|pdf))",
    re.IGNORECASE,
)
# Roughly the size of a wrapper that only \input{}s something else.
RETENTION_MIN_BYTES = 4096


def validate_retention_claims(
    result: GateResult, *, workspace: Path, status_text: str
) -> None:
    """A claim that a prior artifact was retained must be true.

    One run stated that a previously verified 53-page assembly was retained at a
    path holding a 2,277-byte \\VerbatimInput wrapper. Nothing checked, so the
    claim stood (ADR 0023 Q.2). This checks existence and that the file is not
    obviously a stub; it does not read the mathematics.
    """
    for match in RETENTION_CLAIM.finditer(status_text):
        rel = match.group(1)
        path = workspace / rel
        if not path.exists():
            result.errors.append(
                f"STATUS.md claims {rel} was retained, but that file does not exist"
            )
            continue
        try:
            size = path.stat().st_size
        except OSError:
            continue
        if size < RETENTION_MIN_BYTES:
            result.warnings.append(
                f"STATUS.md claims {rel} was retained, but it is only {size} bytes "
                "— check it is the artifact and not a wrapper around one"
            )


def validate_phase(result: GateResult, sections: dict[str, str]) -> None:
    phase = first_content_line(sections.get(canonical("Phase"), ""))
    if not phase:
        # 18 of 54 STATUS.md in the corpus carry no `## Phase` section. Saying
        # what to write is the difference between a report and a complaint.
        result.errors.append(
            "STATUS.md has no '## Phase' section; a completion claim needs one "
            "naming the phase reached (write `## Phase` followed by `complete`)"
        )
        return
    if "complete" not in status_tokens(phase):
        result.errors.append(f"STATUS.md Phase is not complete: {phase!r}")


def _child_dirs(directory: Path) -> list[Path]:
    """Subdirectories of `directory` that could hold a lemma, sorted."""
    try:
        entries = sorted(directory.iterdir())
    except OSError:
        return []
    return [
        entry
        for entry in entries
        if entry.is_dir()
        and not entry.name.startswith(".")
        and entry.name not in LEMMA_DIR_SKIP
    ]


def _is_lemma_dir(directory: Path) -> bool:
    """True when this directory IS a lemma rather than a folder holding lemmas.

    A lemma is recognised by what it owns, not by how deep it sits: a statement,
    or the Generator/Verifier workspaces that only a lemma has. Recognising it by
    depth is what made a grouped run read as twelve empty nodes.
    """
    return (
        (directory / "statement.md").is_file()
        or (directory / "generator").is_dir()
        or (directory / "verifier").is_dir()
    )


def _has_lemma_below(directory: Path, depth: int) -> bool:
    """True when some directory strictly below this one is a lemma.

    This is what keeps the flat layout behaving exactly as before: a directory
    with nothing lemma-shaped underneath is reported as a node itself, empty or
    not, because "a lemma directory holding no statement" is a finding and must
    not be silently replaced by its children.
    """
    if depth >= LEMMA_MAX_DEPTH:
        return False
    for entry in _child_dirs(directory):
        if _is_lemma_dir(entry) or _has_lemma_below(entry, depth + 1):
            return True
    return False


def lemma_directories(workspace: Path) -> list[str]:
    """Every lemma directory under lemmas/, as a path relative to lemmas/.

    Flat runs return bare names exactly as before (`post-e8-final-assembly`).
    Runs that group lemmas under a branch return the grouped path
    (`twosided_rectangle_ordinary_restart_1/tro_section_words`), which joins onto
    `lemmas/` the same way and which `lemma_aliases` also matches by its leaf, so
    a STATUS.md row or a `Depends-on:` label naming the lemma alone still
    resolves.

    Why this is not still one level down: a real run grouped 39 statements under
    11 branch folders, and every caller -- the reconciliation check here and the
    whole dependency graph in dag.py -- saw 11 nodes, 0 edges and 0 findings. An
    empty graph and a graph nobody could read printed the same thing.

    `lemmas/<id>/verifier/` is still part of a lemma and never a lemma itself:
    owning a verifier/ is one of the things that makes a directory a lemma, so
    the walk stops there. Statements also live in `sketch/refined_lemmas/` in
    some runs, and this deliberately does not go looking there -- a check that
    guesses where the lemmas are cannot say what it did not find.
    """
    root = workspace / "lemmas"
    if not root.is_dir():
        return []

    found: list[str] = []

    def walk(rel: str, directory: Path, depth: int) -> None:
        if rel and (_is_lemma_dir(directory) or not _has_lemma_below(directory, depth)):
            found.append(rel)
            return
        for entry in _child_dirs(directory):
            walk(f"{rel}/{entry.name}" if rel else entry.name, entry, depth + 1)

    walk("", root, 0)
    return sorted(found)


def clean_lemma_cell(cell: str) -> str:
    """The bare lemma id inside a table cell's markdown decoration.

    Real cells arrive as ``` `post-e8-final-assembly` ``` and ``**main**``; the
    decoration is never part of the directory name, and echoing it back put the
    backticks inside the path in the diagnostic.
    """
    return cell.strip().replace("**", "").replace("__", "").strip("` ").strip()


def lemma_aliases(name: str) -> set[str]:
    """Every spelling of a lemma id that could name the same directory.

    A row writes `lem:test` for a directory called `lem:test` in one run and
    `test` in the next, so both the cleaned cell and its prefix-stripped form are
    matched against both forms of the directory name. Matching one form only
    made the check fire on correct workspaces.
    """
    text = clean_lemma_cell(name)
    if not text:
        return set()
    forms = {text, LEMMA_ID_PREFIX.sub("", text)}
    # A grouped directory is `<branch>/<lemma>`, but every reference to it -- a
    # STATUS.md row, a `Depends-on:` label, a packet -- names the lemma alone.
    # Two branches can hold the same leaf name; the caller resolves exact
    # directory names before aliases, so the collision costs a resolution, not a
    # wrong answer.
    if "/" in text:
        leaf = text.rsplit("/", 1)[-1]
        forms |= {leaf, LEMMA_ID_PREFIX.sub("", leaf)}
    return {alias.casefold() for alias in forms if alias}


def is_summary_label(cell: str) -> bool:
    """True when a Lemma Status cell names a whole assembly, not a directory.

    One run's table has a single row reading "Global terminal proof" against six
    lemma directories. That is a real thing to write and it is not a missing
    directory, so the inverse check has to let it through.
    """
    text = clean_lemma_cell(cell)
    return " " in text and not IDENTIFIER_TOKEN.search(text)


def parse_superseded(section: str) -> tuple[list[str], list[str]]:
    """(directory names declared superseded, names declared without a reason).

    A bare name is not a disposition -- it reads as "I noticed this directory"
    rather than "this route was abandoned because X". The reason is the whole
    value of the section, so a bullet without one is an error even though the
    name still counts as accounted for; reporting both would blame the same
    bullet twice.
    """
    names: list[str] = []
    reasonless: list[str] = []
    for line in content_lines(section):
        if not line.startswith(("- ", "* ", "+ ")):
            continue
        body = line[2:].strip()
        if not body or body.upper() == "NONE":
            continue
        split = SUPERSEDED_REASON.split(body, maxsplit=1)
        name = split[0].strip().replace("**", "").strip("` /").strip()
        reason = split[1].strip() if len(split) > 1 else ""
        if not name:
            continue
        names.append(name)
        if not reason:
            reasonless.append(name)
    return names, reasonless


def validate_lemma_reconciliation(
    result: GateResult,
    *,
    workspace: Path,
    lemma_section: str,
    superseded_section: str,
    dialect: str = "lemma-status",
) -> None:
    """The lemmas/ listing must agree with STATUS.md in both directions.

    Four runs shipped a proof.pdf at phase `complete` over lemma directories
    holding a statement and nothing else, because every check read STATUS.md and
    proof.tex and none of them ever listed the directory. STATUS.md was
    internally consistent in each case -- the omission is invisible from inside
    the document, and only the filesystem can report it.
    """
    directories = lemma_directories(workspace)
    rows = parse_markdown_table(lemma_section)
    superseded, reasonless = parse_superseded(superseded_section)

    result.lemma_reconciliation = {
        "lemmas_dir": "present" if (workspace / "lemmas").is_dir() else "absent",
        "directories": len(directories),
        "status_rows": len(rows),
        "unaccounted": 0,
        "superseded": len(superseded),
        "rows_without_directory": 0,
    }

    for name in reasonless:
        result.errors.append(
            f"STATUS.md '## {SUPERSEDED_SECTION}' entry {name!r} needs a reason "
            "(write `- <id> — why the route was abandoned`)"
        )

    if not (workspace / "lemmas").is_dir():
        # Statements live elsewhere in some runs (sketch/refined_lemmas/). There
        # is nothing to reconcile against and guessing would be worse than
        # saying so.
        return

    claimed: set[str] = set()
    for row in rows:
        claimed |= lemma_aliases(row.get("lemma", ""))
    for name in superseded:
        claimed |= lemma_aliases(name)

    unaccounted = [name for name in directories if not (lemma_aliases(name) & claimed)]
    result.lemma_reconciliation["unaccounted"] = len(unaccounted)
    # When the section is absent altogether, validate_lemma_rows has already
    # said so once, with the count. Repeating it per directory turns one fact
    # into twelve lines and buries the other findings under it: `gate complete`
    # on the newest run produced ~25 errors carrying one fact.
    if dialect in {"branch-queue", "none"} and not rows:
        result.lemma_reconciliation["cascade_suppressed"] = len(unaccounted)
        return
    for name in unaccounted:
        result.errors.append(
            f"lemmas/{name}/ is not accounted for in STATUS.md (add a Lemma Status "
            f"row or a '## {SUPERSEDED_SECTION}' entry)"
        )

    on_disk: set[str] = set()
    for name in directories:
        on_disk |= lemma_aliases(name)
    orphan_rows = [
        clean_lemma_cell(row.get("lemma", ""))
        for row in rows
        if not is_summary_label(row.get("lemma", ""))
        and lemma_aliases(row.get("lemma", ""))
        and not (lemma_aliases(row.get("lemma", "")) & on_disk)
    ]
    result.lemma_reconciliation["rows_without_directory"] = len(orphan_rows)
    for lemma in orphan_rows:
        # A warning, not an error: one run's table legitimately carries 17 rows
        # against 6 directories because the extra rows are sub-steps refined
        # under sketch/refined_lemmas/. Blocking those would be wrong more often
        # than it would be right.
        result.warnings.append(
            f"STATUS.md Lemma Status row {lemma} names no lemmas/{lemma}/ directory "
            "— check the row is not describing a lemma that was never written"
        )


def validate_lemma_rows(
    result: GateResult,
    *,
    workspace: Path,
    lemma_section: str,
    has_lemma_directories: bool = False,
    dialect: str = "lemma-status",
    directory_count: int = 0,
) -> None:
    rows = parse_markdown_table(lemma_section)
    if not rows:
        # An empty table over an empty workspace is a run that did no lemma
        # work. An empty table over directories on disk is the shipped-with-no-
        # verdicts failure: statements exist, nothing tracks them.
        if not has_lemma_directories:
            result.warnings.append("STATUS.md has no parseable Lemma Status rows")
            return
        if dialect == "branch-queue":
            result.errors.append(
                f"STATUS.md tracks routes in '## {BRANCH_QUEUE_SECTION}' and has no "
                f"'## Lemma Status' section, so {directory_count} lemma "
                "director"
                + ("y is" if directory_count == 1 else "ies are")
                + " accounted for nowhere at lemma level. The branch queue tracks "
                "routes, not lemmas; add a Lemma Status table"
            )
        elif dialect == "none":
            result.errors.append(
                f"STATUS.md has neither a '## Lemma Status' nor a "
                f"'## {BRANCH_QUEUE_SECTION}' section, so {directory_count} lemma "
                "director"
                + ("y is" if directory_count == 1 else "ies are")
                + " tracked nowhere"
            )
        else:
            result.errors.append(
                "STATUS.md has no parseable Lemma Status rows but lemmas/ "
                "contains lemma directories"
            )
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
    validate_retention_claims(result, workspace=workspace, status_text=status_text)
    validate_phase(result, sections)
    validate_open_obligations(
        result,
        sections.get(canonical("Open Proof Obligations"), ""),
    )
    dialect = tracking_dialect(sections)
    directories = lemma_directories(workspace)
    validate_lemma_rows(
        result,
        workspace=workspace,
        lemma_section=sections.get(canonical("Lemma Status"), ""),
        has_lemma_directories=bool(directories),
        dialect=dialect,
        directory_count=len(directories),
    )
    validate_lemma_reconciliation(
        result,
        workspace=workspace,
        lemma_section=sections.get(canonical("Lemma Status"), ""),
        superseded_section=sections.get(canonical(SUPERSEDED_SECTION), ""),
        dialect=dialect,
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
        description="Check completion readiness before an NL-Prover final answer.",
        epilog=REQUIREMENT,
        formatter_class=argparse.RawDescriptionHelpFormatter,
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
    waiver.add_waiver_arg(parser)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    result = lint_workspace(args.workspace, extra_packets=args.packet)

    # Waive before reporting. Reporting first published a verdict computed
    # before the waiver was applied, so `--json` listed errors the waiver
    # had already excused and carried an `ok` that disagreed with the
    # human output on the same run. The two views are one computation.
    result.errors, _waived = waiver.apply_waiver(
        result.errors, args.waive, gate="completion",
        workspace=args.workspace,
    )
    if args.json:
        print(
            json.dumps(
                {
                    "ok": result.ok,
                    "errors": result.errors,
                    "warnings": result.warnings,
                    "packets_checked": result.packets_checked,
                    "lemma_reconciliation": result.lemma_reconciliation,
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
