#!/usr/bin/env python3
"""DAG gate — read the lemma dependency graph back and say what it says.

Every other gate in this package reads one artifact at a time: a proof, a review
packet, a STATUS.md. The lemma graph is the one object in a workspace that no
tool has ever traversed. `prompts/references/verification-modes/plan-logic.md`
asks a *model* to confirm the DAG is acyclic by reading it, and nothing checks
the answer; `gate complete` reconciles the lemma directory listing against
STATUS.md but never follows an edge. So the ordering facts live in the run and
are read by nobody.

    gate dag <workspace> [--json] [--strict]

What the ordering facts look like when you do read them, across an audit of 20
workspaces (345 lemma directories, 196 accepted lemmas, 111 dependency-bearing):

- 11 of 111 lemmas were accepted before a dependency they declare reached its
  own accepting verdict.
- 8 of 111 had a dependency's proof rewritten *after* the dependent's PASS with
  no re-verification, which is exactly what CLAUDE.md invariant 15 forbids: "A
  prior Verifier PASS applies only to the exact artifact it checked."
- 7 obligation-ledger rows still read `open`/`blocker` inside a proof carrying a
  PASS verdict.
- An obligation left open in a dependency does not stop there: a lemma standing
  on it inherits the hole, whichever verdict its own proof earned.
- 55 of 286 statement.md files declare their dependencies in a form nothing can
  parse.

**This gate reports a shape, not a mathematical judgement.** It exits 1 when it
finds an error — a cycle, or a lemma accepted ahead of a dependency it declares —
and 0 otherwise; `--strict` promotes warnings to that same exit. It reports a
shape, never a mathematical judgement: a lemma legitimately gets accepted ahead
of a dependency when the dependency is quoted from a contract file rather than
consumed, and a "later" mtime is sometimes just a copy. What it will not do is
let those cases hide the ones that are real, by never being counted at all.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

from _gate import waiver
from _gate.completion import (  # the parsing rules are shared on purpose (commit 21078b7)
    canonical,
    clean_lemma_cell,
    content_lines,
    lemma_aliases,
    lemma_directories,
    read_sections,
)


# Assembly nodes: the roots a finished run is supposed to reach. Named
# explicitly because an assembly lemma usually *does* have dependents in some
# other run's vocabulary, and "no dependents" alone would miss it.
TOP_NAMES = ("main", "main_assembly", "thm_main", "final_assembly")

ACCEPTING_VERDICT = "PASS"
VERDICT_VALUES = ("PASS", "FAIL", "NEEDS_REVISION")

# `# Verdict: PASS` in a verdict file; `- Verdict: PASS` in a review packet's
# Verdict Snapshot. Both spellings are in the corpus and neither is wrong.
VERDICT_LINE = re.compile(
    r"^\s*(?:#+\s*|[-*+]\s*)?Verdict\s*:\s*\**\s*([A-Za-z_]+)", re.MULTILINE
)
STATUS_LINE = re.compile(r"^\s*(?:#+\s*|[-*+]\s*)?Status\s*:\s*\**\s*([A-Za-z_]+)", re.MULTILINE)

# `verdict_v3.md`, `verdict_v3a.md`. The letter suffix is a re-issue of the same
# round and sorts after the bare number.
VERDICT_VERSION = re.compile(r"^verdict_v(\d+)([a-z]?)\.md$")
PACKET_VERSION = re.compile(r"^review_packet_v(\d+)([a-z]?)\.md$")
PROOF_VERSION = re.compile(r"^proof_v(\d+)([a-z]?)\.md$")

# A machine-readable declaration, written by Sketcher (prompts/sketcher.md, the
# `## Dependencies` template). It is authoritative: where the line is present the
# prose below it is the reason a dependency is needed, never the list of ids.
DEPENDS_ON_LINE = re.compile(r"^\s*Depends-on\s*:\s*(.*)$", re.IGNORECASE | re.MULTILINE)

# Phrases that turn a named lemma into a *non*-dependency. Four of the audit's
# seven false positives were this: "No dependency on `<lemma>`" was read as an
# edge to `<lemma>`, which is the opposite of what the sentence says.
NEGATION = re.compile(
    r"\b(?:no\s+dependenc(?:y|ies)|does\s+not\s+depend|do\s+not\s+depend|"
    r"not\s+depend\s+on|none\s+consumed|independent\s+of|"
    r"no\s+(?:\w+\s+){0,3}lemma\s+is\s+consumed|this\s+node\s+is\s+a\s+root|"
    r"are\s+not\s+dependencies|is\s+not\s+a\s+dependency)\b",
    re.IGNORECASE,
)

# "exactly one of `A` or `B`" is one obligation, not two. Recorded as a group
# and satisfied when any member is accepted; scoring it as two edges reports a
# false unproved-reachable for whichever branch was not taken.
DISJUNCTION = re.compile(r"\bexactly\s+one\s+of\b", re.IGNORECASE)
OR_JOINED = re.compile(r"`[^`\n]+`(?:\s*,\s*`[^`\n]+`)*\s+or\s+`[^`\n]+`")

CODE_SPAN = re.compile(r"`([^`\n]+)`")
# A bare word that could be an identifier. Stops at any bracket or space, so
# `y_i(n)` yields `y_i` and `S_{i,k}` yields `S_`, both of which the length
# filter then rejects.
BARE_TOKEN = re.compile(r"[A-Za-z][A-Za-z0-9_:./-]*")

# Documents, not lemmas. `audit/reading.md` is a real and common dependency
# declaration; it is just not a node in this graph.
DOC_SUFFIXES = (".md", ".tex", ".json", ".py", ".c", ".txt", ".pdf", ".bib")

# Prefixes a run puts on a label that names something outside lemmas/ by
# convention: `def:` for a definition in sketch/target_contract.md, `thm:` for a
# quoted source theorem. Reported, but not as a missing lemma.
OFF_GRAPH_PREFIX = re.compile(r"^(?:def|thm|axiom|conv)\s*:", re.IGNORECASE)

# Below this length a token is a mathematical variable (`T_k`, `y_i`), not a
# lemma id. The shortest real directory name in the corpus is 7 characters.
MIN_TOKEN_LEN = 5

# Ledger statuses that mean the row is not closed. Matched against the *first
# word* of the cell, which is the only rule that survives the corpus: real rows
# read `**open**`, `open (Sketcher)`, `**open — Orchestrator**`, while
# "relatively open", "quoted not assumed" and "resolved" must not fire and a
# substring match fires on all three.
OPEN_LEDGER_WORDS = {"open", "blocker", "unresolved", "blocked", "pending"}
LEDGER_HEADING = re.compile(r"^#+\s*Load-Bearing Obligation Ledger", re.IGNORECASE)

DEFAULT_TOP_N = 8

REQUIREMENT = waiver.requirement_text(
    checks=(
        "the lemma dependency graph, traversed: cycles, assembly nodes that were never\n"
        "accepted, dependencies that were never proved, dependents accepted before the\n"
        "dependency they declare, dependencies\n"
        "rewritten after the dependent's PASS, obligation-ledger rows still open inside\n"
        "an accepted proof, and dependency declarations nothing can parse."
    ),
    legal=(
        "any workspace with a lemmas/ directory. Without one the gate reports\n"
        "  lemmas_dir: absent and stops.\n"
        "dependency declarations: a '## Dependencies' section holding `lemma_id`\n"
        "  tokens, the word NONE, or a machine-readable 'Depends-on: a, b' line.\n"
        "Exits 1 on an error; --strict promotes warnings to an error too."
    ),
    fix=(
        "A dependency accepted after its dependent, or rewritten after it, means the\n"
        "dependent's PASS was taken against an artifact that no longer exists:\n"
        "re-dispatch the Verifier on the dependent (CLAUDE.md invariant 15).\n"
        "An unparseable dependency field: write the ids as `lemma_id` in a\n"
        "'## Dependencies' section, or NONE. Nothing downstream can read prose."
    ),
)


@dataclass
class DagResult:
    ok: bool = True
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    metrics: dict = field(default_factory=dict)


@dataclass
class Node:
    name: str
    status: str = "statement-only"
    rule: str = "statement-only"
    source: str | None = None
    # mtime of the file carrying the accepting verdict; None when not accepted.
    accepted_at: float | None = None
    latest_proof: Path | None = None
    latest_proof_mtime: float | None = None

    @property
    def accepted(self) -> bool:
        return self.status == ACCEPTING_VERDICT


def _version_key(match: re.Match) -> tuple[int, str]:
    return int(match.group(1)), match.group(2)


def _latest(directory: Path, pattern: re.Pattern) -> Path | None:
    """The highest-versioned file matching `pattern`, or None.

    Version-sorting rather than name-sorting is load-bearing: `verdict_v10.md`
    sorts before `verdict_v9.md` as a string, and 44 versioned verdict files in
    the corpus supersede a stale `verdict.md` sitting beside them. Reading the
    stale one mis-reports 5 lemmas as FAIL.
    """
    if not directory.is_dir():
        return None
    best: tuple[tuple[int, str], Path] | None = None
    for entry in directory.iterdir():
        if not entry.is_file():
            continue
        match = pattern.match(entry.name)
        if not match:
            continue
        key = _version_key(match)
        if best is None or key > best[0]:
            best = (key, entry)
    return best[1] if best else None


def _mtime(path: Path) -> float | None:
    try:
        return path.stat().st_mtime
    except OSError:
        return None


def _read(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""


def _verdict_in(text: str) -> str | None:
    match = VERDICT_LINE.search(text)
    if not match:
        return None
    value = match.group(1).strip().upper()
    return value if value in VERDICT_VALUES else None


def read_node(root: Path, name: str) -> Node:
    """Status of one lemma, and the rule that produced it.

    The rule is reported alongside the status because the fallbacks are not
    equivalent. A verdict file is the Verifier's own word; a review packet is
    the packet the verdict was written from; `generator/status.md` is the
    Generator describing itself and is not a verdict at all. A gate that reports
    only the answer makes the third look like the first.
    """
    directory = root / name
    node = Node(name=name)
    verifier = directory / "verifier"

    candidates: list[tuple[str, Path | None]] = [
        ("verdict_v<N>", _latest(verifier, VERDICT_VERSION)),
        ("verdict.md", verifier / "verdict.md" if (verifier / "verdict.md").is_file() else None),
        ("review_packet_v<N>", _latest(verifier, PACKET_VERSION)),
    ]
    for rule, path in candidates:
        if path is None:
            continue
        verdict = _verdict_in(_read(path))
        if verdict is None:
            # The file exists but says nothing readable. Fall through rather
            # than reporting a missing verdict as a failing one.
            continue
        node.status, node.rule, node.source = verdict, rule, path.name
        node.accepted_at = _mtime(path) if verdict == ACCEPTING_VERDICT else None
        break
    else:
        status_file = directory / "generator" / "status.md"
        if status_file.is_file():
            match = STATUS_LINE.search(_read(status_file))
            if match:
                node.status = match.group(1).strip().lower()
                node.rule, node.source = "generator/status.md", "status.md"

    generator = directory / "generator"
    proof = _latest(generator, PROOF_VERSION)
    if proof is None and (generator / "proof.md").is_file():
        proof = generator / "proof.md"
    node.latest_proof = proof
    node.latest_proof_mtime = _mtime(proof) if proof else None
    return node


def dependency_section(statement: Path) -> str | None:
    """The text of the '## Dependencies' section, or None if there is not one.

    Deliberately *not* '## Dependency Preconditions'. That section is a table of
    what must hold when a dependency is applied, and its cells are full of
    backticked mathematics (`K_j`, `a_0`, `p in Q_t`) that reads as identifier
    tokens. Harvesting it turns a correct statement file into a dozen phantom
    dependencies on lemmas that were never named.
    """
    sections = read_sections(_read(statement))
    for name, body in sections.items():
        if name == canonical("Dependencies"):
            return body
    for name, body in sections.items():
        if name.startswith("dependencies"):
            return body
    return None


def _blocks(section: str) -> list[str]:
    """Bullets and paragraphs, each as one string.

    Negation and disjunction scope over a clause, not over the section: a
    section whose first sentence is "None consumed — this node proves nothing"
    and whose remainder lists lemmas "for the framing only" declares no
    dependencies, while its neighbour lists four real ones in four bullets.
    """
    blocks: list[str] = []
    current: list[str] = []
    for line in section.splitlines():
        stripped = line.strip()
        if stripped.startswith(("- ", "* ", "+ ")) or not stripped:
            if current:
                blocks.append(" ".join(current))
                current = []
            if stripped:
                current = [stripped[2:].strip()]
            continue
        current.append(stripped)
    if current:
        blocks.append(" ".join(current))
    return [block for block in blocks if block]


def _acceptable(token: str, known: set[str]) -> bool:
    """Is this token a lemma id rather than a word of English or a variable?

    Two rules, and the second exists because of `load-bearing`. A bare
    (un-backticked) hyphenated word is overwhelmingly English prose, so a bare
    token is only taken when it carries a `_` or `:` — or when it names a
    directory that actually exists, which settles the question outright and
    keeps hyphen-only ids like `post-e8-final-assembly` working.
    """
    if len(token) < MIN_TOKEN_LEN:
        return False
    if token.lower().endswith(DOC_SUFFIXES):
        return False
    if lemma_aliases(token) & known:
        return True
    return "_" in token or ":" in token


def _tokens(text: str, known: set[str]) -> list[str]:
    found: list[str] = []
    spans = [match.group(1).strip() for match in CODE_SPAN.finditer(text)]
    for span in spans:
        # A code span holding whitespace is a formula (`D | 840`, `k -> oo`),
        # not an identifier.
        if not span or any(char.isspace() for char in span):
            continue
        token = clean_lemma_cell(span).strip(".,;:")
        if token and _acceptable(token, known):
            found.append(token)
    if not spans:
        # Some runs write dependencies bare: `lem:data_semantics,
        # lem:product_columns.` Only consulted when the block backticks nothing
        # at all. A block that *does* use code spans has already said which of
        # its words are identifiers, and second-guessing it reads the prose:
        # one such block yielded a dependency on `ACCEPT_READING`, a marker
        # word, because its three real spans were all document paths.
        for match in BARE_TOKEN.finditer(CODE_SPAN.sub(" ", text)):
            token = match.group(0).strip(".,;:")
            if token and _acceptable(token, known):
                found.append(token)
    ordered: list[str] = []
    for token in found:
        if token not in ordered:
            ordered.append(token)
    return ordered


def parse_dependencies(
    statement: Path, *, owner: str, known: set[str]
) -> tuple[list[list[str]], str]:
    """(dependency groups, how the field was read).

    A group of one is a plain edge; a group of several is a disjunction,
    satisfied when any member is accepted. The second element is the reading:
    `depends-on` | `prose` | `declared-none` | `unreadable` | `no-section`.
    """
    if not statement.is_file():
        return [], "no-statement"
    section = dependency_section(statement)
    if section is None:
        return [], "no-section"

    machine = DEPENDS_ON_LINE.search(section)
    if machine:
        body = machine.group(1).strip()
        if body.upper().startswith("NONE"):
            return [], "depends-on"
        # Comma separates independent dependencies, `|` separates alternatives
        # within one. The field has to be able to say everything the prose can,
        # or a disjunctive lemma is forced back into prose and out of reach.
        groups = []
        for part in body.split(","):
            alternatives = [
                token
                for token in (
                    clean_lemma_cell(alt).strip(".,;:") for alt in part.split("|")
                )
                if token and token.casefold() != owner.casefold()
            ]
            if alternatives:
                groups.append(alternatives)
        return groups, "depends-on" if groups else "unreadable"

    groups: list[list[str]] = []
    declared_none = False
    for block in _blocks(section):
        if NEGATION.search(block):
            declared_none = True
            continue
        tokens = [t for t in _tokens(block, known) if t.casefold() != owner.casefold()]
        if not tokens:
            if content_lines(block) and content_lines(block)[0].upper().startswith("NONE"):
                declared_none = True
            continue
        if DISJUNCTION.search(block) or OR_JOINED.search(block):
            groups.append(tokens)
        else:
            groups.extend([token] for token in tokens)
    if groups:
        return groups, "prose"
    if declared_none or not section.strip():
        return [], "declared-none"
    return [], "unreadable"


def _status_column(cells: list[str]) -> int | None:
    """Index of the Status column in a header row, or None if this is not one."""
    for index, cell in enumerate(cells):
        name = clean_lemma_cell(cell).strip("*_ ").casefold()
        if name == "state" or "status" in name:
            return index
    return None


def ledger_rows(text: str) -> list[tuple[str, str]]:
    """(obligation, status) for each row of the Load-Bearing Obligation Ledger.

    The status is located by *header name*, not by position. Reading `cells[-1]`
    made `open_rows` return nothing whenever anything followed the Status column
    — `| ... | Current status | Requested next action |`, which is already in
    `prompts/generator.md`, hid exactly the open obligations the gate exists to
    surface. Rows with no recognisable header still fall back to `cells[-1]`:
    the corpus contains ledger tables with no header line at all.
    """
    rows: list[tuple[str, str]] = []
    inside = False
    status_index: int | None = None
    header_seen = False
    for line in text.splitlines():
        if LEDGER_HEADING.match(line.strip()):
            inside = True
            # Each ledger is parsed on its own header; a stale index from the
            # previous table would point at the wrong column in this one.
            status_index = None
            header_seen = False
            continue
        if inside and line.strip().startswith("#"):
            inside = False
            continue
        if not inside:
            continue
        stripped = line.strip()
        if not stripped.startswith("|"):
            continue
        cells = [cell.strip() for cell in stripped.strip("|").split("|")]
        if len(cells) < 2:
            continue
        if all(re.fullmatch(r":?-{2,}:?", cell.replace(" ", "")) for cell in cells if cell):
            continue
        if not header_seen:
            # Only the first row of the table can be a header, so a data row
            # whose text happens to contain "status" cannot be mistaken for one.
            header_seen = True
            index = _status_column(cells)
            if index is not None or cells[0].casefold() == "obligation":
                status_index = index
                continue
        if status_index is not None and status_index < len(cells):
            rows.append((cells[0], cells[status_index]))
        else:
            rows.append((cells[0], cells[-1]))
    return rows


def _first_word(cell: str) -> str:
    text = clean_lemma_cell(cell).strip("*_ ")
    match = re.match(r"[A-Za-z_]+", text)
    return match.group(0).casefold() if match else ""


def open_rows(text: str) -> list[str]:
    """Ledger rows whose status is still open.

    Only the *first word* of the status cell is consulted. A substring match
    fires on "relatively open", on "quoted not assumed", and — because
    "resolved" contains no such word but its neighbours do — on rows whose long
    explanation happens to mention an obligation that closed. All three are in
    the corpus and none is a finding.
    """
    out = []
    for obligation, status in ledger_rows(text):
        if _first_word(status) in OPEN_LEDGER_WORDS:
            out.append(f"{obligation.strip()[:80]} [{clean_lemma_cell(status)[:60]}]")
    return out


def _find_cycles(edges: dict[str, set[str]]) -> list[list[str]]:
    """Every cycle a plain DFS reaches, one representative path each.

    Nothing in this harness has ever checked this. The plan-logic reference asks
    a model to confirm the graph is acyclic; that answer has never been tested
    against the graph.
    """
    cycles: list[list[str]] = []
    seen_signatures: set[frozenset[str]] = set()
    colour: dict[str, int] = {}
    stack: list[str] = []

    def visit(node: str) -> None:
        colour[node] = 1
        stack.append(node)
        for nxt in sorted(edges.get(node, ())):
            if colour.get(nxt, 0) == 0:
                visit(nxt)
            elif colour.get(nxt) == 1:
                loop = stack[stack.index(nxt):] + [nxt]
                signature = frozenset(loop)
                if signature not in seen_signatures:
                    seen_signatures.add(signature)
                    cycles.append(loop)
        stack.pop()
        colour[node] = 2

    for node in sorted(edges):
        if colour.get(node, 0) == 0:
            visit(node)
    return cycles


def _untracked_in_status(workspace: Path, names: list[str]) -> tuple[list[str], str]:
    """Lemma directories that STATUS.md accounts for in no table.

    Two tracking dialects exist in the corpus and they track different objects:
    `## Lemma Status` is a table of lemma directories, `## Active Branch Queue` a
    table of routes. 19 of 54 run roots have lemma directories and no Lemma
    Status section, so their lemmas are tracked at lemma level nowhere. The
    completion gate says so — but only at the moment a run claims completion,
    which is the most expensive moment to learn it. Here it is a warning, during
    the run, where the fix is one table row.
    """
    status = workspace / "STATUS.md"
    if not status.is_file():
        return [], "no STATUS.md"
    try:
        text = status.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return [], "unreadable STATUS.md"
    headings = {
        re.sub(r"\s+", " ", m.group(1).strip()).casefold()
        for m in re.finditer(r"(?m)^#{1,6}\s+(.+?)\s*$", text)
    }
    has_lemma = "lemma status" in headings
    has_queue = "active branch queue" in headings
    dialect = (
        "both" if has_lemma and has_queue
        else "lemma-status" if has_lemma
        else "branch-queue" if has_queue
        else "neither"
    )
    if has_lemma:
        # A Lemma Status table exists; reconciling its rows against the
        # directories is the completion gate's job and is not duplicated here.
        return [], dialect
    return sorted(names), dialect


def analyse(workspace: Path) -> DagResult:
    result = DagResult()
    workspace = Path(workspace)
    if not workspace.is_dir():
        result.ok = False
        result.errors.append(f"workspace not found: {workspace}")
        return result

    names = lemma_directories(workspace)
    if not (workspace / "lemmas").is_dir():
        # Statements live in sketch/refined_lemmas/ in some runs. Going looking
        # there would be guessing, and a graph assembled from a guess cannot say
        # what it failed to find.
        result.metrics = {"lemmas_dir": "absent", "nodes": 0}
        return result

    root = workspace / "lemmas"
    known: set[str] = set()
    for name in names:
        known |= lemma_aliases(name)
    # Exact directory names first, prefix-stripped aliases only where they do
    # not collide with one. A rename leaves `lem_<name>/` beside an abandoned
    # `<name>/`; letting the prefix-stripped alias win makes every reference to
    # the former resolve to the latter, and the empty duplicate then reports as
    # an unproved dependency of the whole assembly.
    by_alias: dict[str, str] = {}
    for name in names:
        by_alias[clean_lemma_cell(name).casefold()] = name
    for name in names:
        for alias in lemma_aliases(name):
            by_alias.setdefault(alias, name)

    nodes = {name: read_node(root, name) for name in names}

    groups: dict[str, list[list[str]]] = {}
    readings: dict[str, str] = {}
    for name in names:
        parsed, reading = parse_dependencies(
            root / name / "statement.md", owner=name, known=known
        )
        groups[name] = parsed
        readings[name] = reading

    # Resolve declared labels onto directories. A label that resolves to no
    # directory is kept — it is one of the findings, not a parse error.
    resolved: dict[str, list[list[str]]] = {}
    missing: list[dict[str, str]] = []
    for name, parsed in groups.items():
        out: list[list[str]] = []
        for group in parsed:
            members = []
            for label in group:
                exact = clean_lemma_cell(label).casefold()
                target = by_alias.get(exact)
                if target is None:
                    # Longest alias first, so the deterministic answer is the
                    # most specific one rather than whatever the set iterated.
                    for alias in sorted(lemma_aliases(label), key=len, reverse=True):
                        if alias in by_alias:
                            target = by_alias[alias]
                            break
                if target is None:
                    record = {
                        "lemma": name,
                        "declares": label,
                        "off_graph_prefix": bool(OFF_GRAPH_PREFIX.match(label)),
                    }
                    # One label named in three bullets is one missing
                    # dependency, not three.
                    if record not in missing:
                        missing.append(record)
                else:
                    members.append(target)
            if members:
                out.append(members)
        resolved[name] = out

    edges: dict[str, set[str]] = {
        name: {member for group in out for member in group} for name, out in resolved.items()
    }

    # --- findings ---------------------------------------------------------
    dependents: dict[str, int] = {name: 0 for name in names}
    for name, targets in edges.items():
        for target in targets:
            dependents[target] = dependents.get(target, 0) + 1
    tops = sorted(
        name
        for name in names
        if name in TOP_NAMES or lemma_aliases(name) & set(TOP_NAMES) or dependents[name] == 0
    )
    accepted_tops = [name for name in tops if nodes[name].accepted]
    # The traversal below starts only from accepted tops, which is what makes
    # `unproved_reachable` mean "the assembly claims to be closed and is not".
    # On its own that rule goes silent on the worst case there is: a workspace
    # whose lemmas are all statement-only, at phase `complete`, with an exported
    # proof.pdf — its assembly node is statement-only too, so there is no
    # accepted top to traverse from and every list comes back empty. An
    # unaccepted top node is therefore its own finding, reported before
    # reachability rather than instead of it.
    # A directory with no statement.md is a top node only by default — it makes
    # no claim, so there is nothing for it to have failed to prove, and it is
    # already reported as a missing statement. A workspace carrying a dozen
    # abandoned duplicates would otherwise restate that line a dozen times and
    # bury the real finding.
    unaccepted_tops = [
        f"{name} is not accepted ({nodes[name].status} via {nodes[name].rule})"
        for name in tops
        if not nodes[name].accepted and readings[name] != "no-statement"
    ]

    # Traverse groups, not the flattened edge set. A disjunction is discharged
    # by any one accepted member, so the alternatives it did not use are not
    # unproved dependencies of anything — walking the flattened set reported
    # every road not taken as a hole in the proof.
    reachable: set[str] = set()
    frontier = list(accepted_tops)
    while frontier:
        current = frontier.pop()
        for group in resolved.get(current, ()):
            discharged = [m for m in group if nodes[m].accepted]
            for target in sorted(discharged or group):
                if target not in reachable:
                    reachable.add(target)
                    frontier.append(target)
    unproved_reachable = sorted(
        f"{name} ({nodes[name].status} via {nodes[name].rule})"
        for name in reachable
        if not nodes[name].accepted
    )

    accepted_before: list[str] = []
    stale_pass: list[str] = []
    for name, out in resolved.items():
        node = nodes[name]
        if not node.accepted or node.accepted_at is None:
            continue
        for group in out:
            satisfied = [nodes[m] for m in group if nodes[m].accepted]
            if not satisfied:
                continue  # an unaccepted dependency is unproved_reachable's job
            # A disjunction is discharged by whichever member closed first.
            stamps = [dep.accepted_at for dep in satisfied if dep.accepted_at is not None]
            if stamps and min(stamps) > node.accepted_at:
                earliest = min(
                    (dep for dep in satisfied if dep.accepted_at is not None),
                    key=lambda dep: dep.accepted_at,
                )
                accepted_before.append(
                    f"{name} accepted {_gap(node.accepted_at, earliest.accepted_at)} "
                    f"before its dependency {earliest.name}"
                )
            for dep in satisfied:
                if dep.latest_proof_mtime and dep.latest_proof_mtime > node.accepted_at:
                    stale_pass.append(
                        f"{name}: dependency {dep.name} rewrote "
                        f"{dep.latest_proof.name} {_gap(node.accepted_at, dep.latest_proof_mtime)} "
                        f"after this lemma's PASS"
                    )
    accepted_before = sorted(set(accepted_before))
    stale_pass = sorted(set(stale_pass))

    open_ledger: list[str] = []
    open_by_node: dict[str, list[str]] = {}
    for name in names:
        node = nodes[name]
        if node.latest_proof is None:
            continue
        rows = open_rows(_read(node.latest_proof))
        if not rows:
            continue
        open_by_node[name] = rows
        if node.accepted:
            for row in rows:
                open_ledger.append(f"{name}/{node.latest_proof.name}: {row}")

    # An obligation left open in a dependency does not stop at that dependency.
    # A lemma standing on it inherits the hole, whichever verdict its own proof
    # earned -- the citing proof is only as discharged as what it cites. The
    # per-node check above sees a lemma's own ledger; this one follows the edges,
    # which is the whole reason the graph is traversed at all.
    inherited: list[str] = []
    for name in names:
        if not nodes[name].accepted:
            continue
        seen: set[str] = set()
        frontier = [dep for group in resolved.get(name, []) for dep in group]
        while frontier:
            dep = frontier.pop()
            if dep in seen or dep == name:
                continue
            seen.add(dep)
            frontier.extend(m for group in resolved.get(dep, []) for m in group)
            for row in open_by_node.get(dep, []):
                inherited.append(f"{name} stands on {dep}, whose ledger still reads: {row}")

    cycles = [" -> ".join(cycle) for cycle in _find_cycles(edges)]
    # A directory with no statement.md at all is a different fact from a
    # dependency field nothing can parse, and folding the two together reported
    # a workspace's abandoned duplicate directories as unparseable declarations.
    unreadable = sorted(
        f"{name} ({readings[name]})"
        for name in names
        if readings[name] in ("unreadable", "no-section")
    )
    statement_missing = sorted(name for name in names if readings[name] == "no-statement")

    status_counts: dict[str, int] = {}
    for node in nodes.values():
        status_counts[node.status] = status_counts.get(node.status, 0) + 1

    untracked, dialect = _untracked_in_status(workspace, names)

    result.metrics = {
        "lemmas_dir": "present",
        "nodes": len(names),
        "status_counts": status_counts,
        "status_rules": {name: nodes[name].rule for name in names},
        "edges": sum(len(group) for out in resolved.values() for group in out),
        "disjunctive_groups": sum(
            1 for out in resolved.values() for group in out if len(group) > 1
        ),
        "top_nodes": tops,
        "accepted_top_nodes": accepted_tops,
        "dependency_readings": readings,
        "statement_missing": statement_missing,
        "findings": {
            "cycles": cycles,
            "unaccepted_top_node": unaccepted_tops,
            "unproved_reachable": unproved_reachable,
            "accepted_before_dependency": accepted_before,
            "stale_pass": stale_pass,
            "open_ledger_rows_in_accepted": sorted(open_ledger),
            "inherited_open_obligations": sorted(set(inherited)),
            "dependency_without_directory": missing,
            "unreadable_dependency_field": unreadable,
            "lemmas_untracked_in_status": untracked,
        },
        "status_dialect": dialect,
        "mtime_based": ["accepted_before_dependency", "stale_pass"],
    }

    for cycle in cycles:
        result.warnings.append(
            f"dependency cycle: {cycle} — a cycle cannot be discharged in any order, "
            f"and plan-logic.md's acyclicity check is a model reading the file"
        )
    _emit(
        result,
        "unaccepted_top_node",
        unaccepted_tops,
        lambda item: (
            f"top node {item} — nothing above it depends on it, so no accepted lemma "
            f"in this workspace vouches for it"
        ),
    )
    _emit(
        result,
        "unproved_reachable",
        unproved_reachable,
        lambda item: f"reachable from an accepted assembly but not accepted itself: {item}",
    )
    _emit(
        result,
        "accepted_before_dependency",
        accepted_before,
        lambda item: f"{item} — nothing re-verified it afterwards",
    )
    _emit(
        result,
        "stale_pass",
        stale_pass,
        lambda item: (
            f"{item} (CLAUDE.md invariant 15: a PASS applies only to the artifact it checked)"
        ),
    )
    _emit(
        result,
        "open_ledger_rows_in_accepted",
        sorted(open_ledger),
        lambda item: f"open obligation inside an accepted proof — {item}",
    )
    _emit(
        result,
        "inherited_open_obligations",
        sorted(set(inherited)),
        lambda item: f"inherited open obligation — {item}",
    )
    if untracked:
        result.warnings.append(
            f"{len(untracked)} lemma director"
            + ("y is" if len(untracked) == 1 else "ies are")
            + f" tracked nowhere in STATUS.md (it uses the {dialect} dialect). "
            "The completion gate will refuse this run; the cheap moment to fix it "
            "is now, not at the stop"
        )
    _emit(
        result,
        "dependency_without_directory",
        missing,
        lambda item: (
            f"{item['lemma']} declares {item['declares']}, which names no lemmas/ directory"
            + (
                " (a def:/thm: label — definitions legitimately live in sketch/target_contract.md)"
                if item["off_graph_prefix"]
                else ""
            )
        ),
    )
    if unreadable:
        _emit(
            result,
            "unreadable_dependency_field",
            unreadable,
            lambda item: (
                f"{item} declares dependencies in a form nothing can parse "
                f"({len(unreadable)} of {len(names)} statement.md files do)"
            ),
        )
    return result


def _emit(result: DagResult, label: str, items: list, render) -> None:
    """One warning per finding, capped, with the elision said out loud.

    The cap exists so a workspace with forty statement-only lemmas does not bury
    its one cycle. What the cap must never do is disagree silently with the
    count printed above it: one run reported `unproved_reachable 15` and then
    listed eight, and nothing on the page said the other seven existed. A reader
    who counts the lines is entitled to reach the same number the gate did.
    """
    for item in items[:DEFAULT_TOP_N]:
        result.warnings.append(render(item))
    remaining = len(items) - DEFAULT_TOP_N
    if remaining > 0:
        result.warnings.append(f"… {remaining} more {label} finding(s) not listed")


def _gap(earlier: float, later: float) -> str:
    minutes = abs(later - earlier) / 60.0
    if minutes < 90:
        return f"{minutes:.0f}m"
    return f"{minutes / 60:.1f}h"


MTIME_CAVEAT = (
    "accepted_before_dependency and stale_pass are read from file mtimes, which a copy, "
    "an archive extraction or a mechanical edit perturbs — circumstantial, not proof."
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Traverse the lemma dependency graph and report what its ordering says.",
        epilog=REQUIREMENT,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("workspace", type=Path, help="Problem workspace to traverse.")
    parser.add_argument("--json", action="store_true", help="Print machine-readable output.")
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Exit non-zero when there is a finding. Off by default: this gate reports, it does not block a run.",
    )
    waiver.add_waiver_arg(parser)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    result = analyse(args.workspace)
    metrics = result.metrics

    # Waive before reporting. Reporting first published a verdict computed
    # before the waiver was applied, so `--json` listed errors the waiver
    # had already excused and carried an `ok` that disagreed with the
    # human output on the same run. The two views are one computation.
    result.errors, _waived = waiver.apply_waiver(
        result.errors, args.waive, gate="dag", workspace=args.workspace,
    )
    if args.json:
        print(
            json.dumps(
                {
                    "ok": result.ok,
                    "errors": result.errors,
                    "warnings": result.warnings,
                    "metrics": metrics,
                    "mtime_caveat": MTIME_CAVEAT,
                },
                indent=2,
                sort_keys=True,
            )
        )
    else:
        print(f"dag_gate: {args.workspace}")
        if metrics.get("lemmas_dir") == "absent":
            print("  lemmas/                 absent — nothing to traverse")
        elif metrics:
            counts = ", ".join(
                f"{name} {total}" for name, total in sorted(metrics["status_counts"].items())
            )
            print(f"  nodes                   {metrics['nodes']}  ({counts})")
            print(
                f"  edges                   {metrics['edges']}"
                f"  ({metrics['disjunctive_groups']} disjunctive group(s))"
            )
            print(f"  top nodes               {', '.join(metrics['top_nodes']) or '(none)'}")
            findings = metrics["findings"]
            for label in (
                "cycles",
                "unaccepted_top_node",
                "unproved_reachable",
                "accepted_before_dependency",
                "stale_pass",
                "open_ledger_rows_in_accepted",
                "inherited_open_obligations",
                "dependency_without_directory",
                "unreadable_dependency_field",
                "lemmas_untracked_in_status",
            ):
                mark = "*" if label in metrics["mtime_based"] else " "
                print(f"  {label:<38}{mark} {len(findings[label])}")
            if metrics["statement_missing"]:
                print(
                    f"  {'(no statement.md at all)':<38}  {len(metrics['statement_missing'])}"
                    f"  {', '.join(metrics['statement_missing'][:DEFAULT_TOP_N])}"
                )
            print(f"  * {MTIME_CAVEAT}")
        for error in result.errors:
            print(f"ERROR: {error}")
        for warning in result.warnings:
            print(f"WARNING: {warning}")

    if not args.json:
        waiver.print_waived(_waived, args.waive or "")
    if result.errors and not args.json:
        # Not under --json: the epilogue is prose, and printing prose after a
        # JSON document makes the document unparseable exactly when it carries
        # something to report. Six of the ten gates did this; only the ones that
        # happened to pass on the workspace they were tried against looked healthy.
        print()
        print(REQUIREMENT)
    # The verdict is not part of that. It used to sit inside the block above, so
    # `--json` — the mode a script runs — reported `"ok": false` and exited 0, while
    # the same workspace in text mode exited 1. A gate whose answer depends on how it
    # was asked to print is not a gate.
    if result.errors:
        return 1
    if args.strict and result.warnings:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
