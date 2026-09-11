"""Progress summary gate: the document a person reads, checked mechanically.

The complaint this implements was specific, and each half of it gets its own
check rather than one instruction asking for "a good summary":

    too long · misses the point · badly structured · too much jargon and
    self-invented vocabulary · does not accurately summarise progress

Every one of those is mechanically decidable on the summary source, and none of
them was decidable on `progress_notes.tex`, which is a restart document and is
correctly unbounded. So this gate checks the summary and never the note.

The summary is LaTeX compiled to a PDF, not markdown. Both stop documents are
read by a person, and the one carrying mathematics that a person is expected to
read in one sitting is the one that most needs typesetting: raw `$\\pi_1(X)$` in
a markdown file is not a summary of anything. The line and byte caps below are
therefore measured on the **body** of the `.tex` -- everything after
`\\begin{document}` -- so that a preamble cannot eat the budget and so that the
"blocker near the top" rule keeps counting from the first line the reader sees.

What it deliberately does NOT do: repair. It reports and blocks the stop. A
clean artifact that exists and a clean artifact that was produced must not be
allowed to diverge, and a gate that rewrites the file it is judging makes them
diverge silently.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from _gate import waiver  # noqa: E402


# Authored here, compiled from here, exported to the workspace root beside
# `progress_notes.pdf`. Same split as the note: source under `writer/`, the
# artifact a person opens at the root.
SUMMARY_NAME = "writer/progress_summary.tex"
SUMMARY_PDF = "progress_summary.pdf"

# 2026-08-28, raised from 120 lines / 12 KB on the human's instruction ("一屏是
# 不是有点太少了"). 120 body lines was one screen, and one screen cannot hold six
# sections once the established results and the ruled-out routes are each more
# than one line -- the cap was being met by dropping content rather than by
# writing tightly. These are measured on the body, so the old number was in
# practice tighter still: the preamble counted against it.
#
# The failure this cap exists to prevent is 21,215 lines and 49 pages. 300 is
# two orders of magnitude below that and still fits in a sitting. If summaries
# start arriving at exactly 300, the cap is doing the writing and that is the
# finding -- it is one constant here, deliberately.
MAX_LINES = 300
MAX_BYTES = 32_768

# The complaint was phrased in pages, so one check is phrased in pages. Read
# from the pdflatex log rather than the PDF, because no PDF tooling is
# guaranteed present and the log line is stable. Absent log => not checked, and
# `pages` reports null so that "not checked" never reads as "passed".
MAX_PAGES = 10

# The blocker is what the reader came for. Measured over the corpus it sat past
# 85% of the file in 7 notes of 11 and past 99% in the longest, which is a
# property of the mandated section order, not of the writing.
#
# Absolute, not a fraction. A fraction made the two rules in this file pull
# against each other: MAX_LINES rewards a short document and a percentage
# rewards a late-heavy one, so the only way to lower the ratio was to pad after
# the blocker. A correct 20-line summary with a full-length lead measured 55%
# and was refused. What the rule actually means is "near the top", and the top
# of a document is a number of lines, not a share of it.
# Raised 24 -> 40 with the arrival of `The statement` above it. The rule means
# "near the top", and the top moved: a reader who does not yet know the problem
# cannot use the blocker, so stating it first is worth the lines it costs.
BLOCKER_MAX_LINE = 40
BLOCKER_MAX_DEPTH = 0.40  # only applies once a file is long enough to have one

REQUIRED_SECTIONS = (
    # 2026-08-28. The first real summary never stated the problem it was about.
    # The title said "Sumset-Complement Claim for Eight Forms Modulo 24", the
    # lead said it was open and equivalent to a Goldbach problem, and a reader
    # still could not say what $S$ was or what the eight forms were. The
    # restart document is required to open with the exact statement
    # (progress-note.md); the summary asked for a status and never for the
    # thing the status is about, so the one document a person opens was the one
    # that assumed they already knew.
    "The statement",
    "Where this stands",
    "What is blocked",
    "What is established",
    "What was ruled out",
    "What to do next",
    "Terms coined here",
)

# LaTeX, not markdown italics. The exact string is compared verbatim, so it has
# to be the exact string the author types into a `.tex` file.
EMPTY_STATE = {
    "What is blocked": (
        "\\emph{(nothing is blocked; the run stopped for another reason --- say which above)}"
    ),
    "What is established": "\\emph{(nothing has been verified yet)}",
    "What was ruled out": (
        "\\emph{(no route has been ruled out; absence here does not mean the route set is small)}"
    ),
    "What to do next": "\\emph{(no next step is identified --- that is itself the finding)}",
    "Terms coined here": "\\emph{(this document coins no terms)}",
}

# Raised from 5 with the budget, and for the same reason. Five sentences was a
# lead for a one-screen document; the lead still has to answer one question --
# proved, disproved, partially proved, or open -- and it is the first thing
# read, so it stays capped.
LEAD_MAX_SENTENCES = 8

# Words that are only ever harness machinery, matched case-insensitively.
# Nothing here is also ordinary mathematical English -- that is the entry
# condition for this list, and the reason the two lists below exist.
HARNESS_TERMS = (
    r"review[ _]packet",
    r"NEEDS_REVISION",
    r"AUDIT_PASS",
    r"ce-hunter",
    r"kb-manager",
    r"code[_-]executor",
    r"sub[- ]?agent",
    r"Depends-on",
    r"dispatch(?:ed|es|ing)?\b",
    r"branch queue",
    r"shadow owner",
    r"obligation ledger",
    r"discovery mode",
    r"certification mode",
    r"STATUS\.md",
    r"proof\.tex",
    r"lemma_id",
    r"route_history",
    r"\bgate\.py",
    # NOT a bare `gate <word>`: "gate set", "gate complexity" and "gate
    # teleportation" are ordinary mathematics. Only the real subcommands.
    r"\bgate (?:complete|stop|proof-attempt|proof-review|review-packet|"
    r"result-contract|citation-audit|discovery|speed|dag|summary|contracts)\b",
    r"cli_tools",
    r"workspace/",
    r"Certified dossier",
    r"restart_\d",
)

# Role names, matched CASE-SENSITIVELY, because several of them are also
# ordinary nouns. `Verifier` capitalised mid-sentence is this harness's
# specialist; `verifier` is not necessarily anything. The one that forced this
# split is `generator`: in a group-theory workspace it is one of the commonest
# words in the subject, and a lint that refuses "each generator of the group"
# is a lint the run learns to route around. It sits in the density list below
# instead, where a single ordinary use is silent and twelve are not.
ROLE_NAMES = (
    r"\bSketcher\b",
    r"\bOrchestrator\b",
    r"\bSynthesizer\b",
    r"\bCE-Hunter\b",
    r"\bKB-Manager\b",
)

# `Generator` is deliberately absent from the list above and present on the
# density list below. A review flagged that as a mismatch with a commit message
# claiming it was caught case-sensitively — and the commit message was the thing
# that was wrong. In a group-theory workspace `generator` is one of the
# commonest nouns in the subject, and capitalisation does not separate the two
# senses reliably at the start of a sentence.
#
# Role names that are ALSO standard mathematical nouns. `Verifier`
# is standard in interactive proofs and PCP; `Regulator` is the regulator of a
# number field, conventionally `R_K`; `Refiner` is rarer but a refinement is
# not. Refusing a summary about class numbers for saying "Regulator" is the
# false-positive machine this gate's own comments warn about -- and the
# epilogue tells the run not to waive, so the only way out would be to rename
# the mathematics. They go on the density list with `generator`.
MATHEMATICAL_ROLE_NAMES = (
    r"\bVerifier\b",
    r"\bRegulator\b",
    r"\bRefiner\b",
)

# Words that are ALSO mathematics. Blacklisting these outright builds a
# false-positive machine that a run learns to route around, so they are judged on
# density instead.
#
# Recomputed 2026-08-25 with these exact patterns over the 21 progress notes in
# the corpus, because the figures first written here (0.53 / 0.11 / below 0.05)
# did not reproduce:
#
#   0.492  CLT/problem33_conj36            <- the pathological case
#   0.150  ESConjecture/0806/newtestb (short)
#   0.147  ESConjecture/old
#   0.120  ESConjecture/0714/tcts5
#   median 0.040, and 8 of 21 above 0.05
#
# The separation is real but it is 3.3x, not the order of magnitude claimed, and
# the threshold sits exactly on the second value — which is why the comparison
# below is `>=` and not `>`. A boundary case that does not fire is a threshold
# chosen to be flattered by its own corpus.
AMBIGUOUS_TERMS = (
    r"\bowner\b",
    r"\brows?\b",
    r"\bledgers?\b",
    r"\bslots?\b",
    r"\brecords?\b",
    r"\baccepted\b",
    r"\baudit(?:s|ed|ing)?\b",
    r"\bpackets?\b",
    r"\bgenerators?\b",
    r"\bverifiers?\b",
    r"\bregulators?\b",
    r"\brefiners?\b",
)
AMBIGUOUS_MAX_DENSITY = 0.15

NUMERIC_DISTANCE = (
    r"\b\d{1,3}\s?%\s*(?:done|complete|of the way|there)\b",
    r"\b(?:roughly|about|approximately|~|≈)\s*\d+\s*[–—-]\s*\d+\s*(?:lemma|fact|step|run)",
    r"\b(?:two|three|four|a few|several)\s+more\s+(?:runs?|rounds?|days?)\b",
    r"\b\d+\s*(?:more\s+)?(?:runs?|rounds?)\s+(?:to go|remain|left)\b",
)

TELEMETRY = (
    r"\b\d+\s+dispatch(?:es)?\b",
    r"\bmtimes?\b",
    r"\brun id\b",
    r"\bwall[- ]clock\b",
    r"\bconcurrency\b",
    r"\btokens? spent\b",
)

PASTE = (r"\\begin\{(?:verbatim|lstlisting|minted|Verbatim|alltt)\}",)

# The markdown fence scanner that used to live here went with markdown. A
# verbatim environment in a document for a person is banned outright rather
# than judged on its contents: the summary's whole job is to restate, and the
# note next to it is where anything unrestatable belongs.

REQUIREMENT = """
If it fails:
  Fix the summary, do not waive it. This gate exists because a restart document
  was being handed to a person for a month and every gate passed. The restart
  document is not the thing being judged here and must not be shortened to
  satisfy this.
""".strip()


class SummaryResult:
    def __init__(self) -> None:
        self.errors: list[str] = []
        self.warnings: list[str] = []
        self.metrics: dict = {}
        self.waived: list[str] = []

    @property
    def ok(self) -> bool:
        return not self.errors


BEGIN_DOCUMENT = re.compile(r"^\s*\\begin\{document\}")
END_DOCUMENT = re.compile(r"^\s*\\end\{document\}")

# Environments whose contents are typeset as-is. A pasted packet arrives inside
# one of these, and its own headings must not be able to supply the document's
# required structure -- the paste check and the structure check would then be
# reading the same lines for opposite purposes and certifying each other.
VERBATIM_OPEN = re.compile(r"\\begin\{(verbatim|lstlisting|minted|Verbatim|alltt)\}")
VERBATIM_CLOSE = re.compile(r"\\end\{(verbatim|lstlisting|minted|Verbatim|alltt)\}")

SECTION = re.compile(r"^\s*\\section\*?\{(.+?)\}\s*$")


def document_body(text: str) -> tuple[str, int]:
    """The lines after `\\begin{document}`, and how many lines preceded them.

    Every budget and every reported line number is relative to this, so that a
    preamble neither spends the budget nor pushes the blocker down the page.
    The reader's first line is the body's first line.

    The body ENDS at `\\end{document}`. Without that the last required section
    always carries the closing line in its body, so "this section is empty" was
    undecidable for whichever section comes last -- and that is `Terms coined
    here`, every time, by construction. Caught by testing the reject case; the
    accept case passed either way.

    A file with no `\\begin{document}` is judged whole rather than skipped: it
    is malformed, `check_preamble` says so, and silently exempting a malformed
    file from the caps is how a file gets written that way on purpose.
    """
    lines = text.splitlines()
    start = None
    for index, line in enumerate(lines):
        if BEGIN_DOCUMENT.match(line):
            start = index + 1
            break
    if start is None:
        return text, 0
    body = lines[start:]
    for index, line in enumerate(body):
        if END_DOCUMENT.match(line):
            body = body[:index]
            break
    return "\n".join(body), start


def _sections(text: str) -> list[tuple[str, int, list[str]]]:
    """(title, line number, body lines) for every `\\section{}`, in order.

    `text` is the document body, so line numbers are the ones a reader counts.
    Verbatim environments are skipped, for the reason on VERBATIM_OPEN.
    """
    out: list[tuple[str, int, list[str]]] = []
    current: tuple[str, int, list[str]] | None = None
    verbatim = False
    for number, line in enumerate(text.splitlines(), start=1):
        if not verbatim and VERBATIM_OPEN.search(line):
            verbatim = True
            if current is not None:
                current[2].append(line)
            continue
        if verbatim:
            if VERBATIM_CLOSE.search(line):
                verbatim = False
            if current is not None:
                current[2].append(line)
            continue
        match = SECTION.match(line)
        if match:
            if current is not None:
                out.append(current)
            current = (match.group(1).strip(), number, [])
            continue
        if current is not None:
            current[2].append(line)
    if current is not None:
        out.append(current)
    return out


def _body_text(body: list[str]) -> str:
    return "\n".join(body).strip()


# A backticked token containing a slash is a path — the one piece of harness
# machinery the summary is required to carry, because an established result must
# say where its proof lives. Scanning it for harness vocabulary makes the gate
# refuse the very thing it asks for: the first draft tested here was rejected for
# the `restart_1` inside a legitimate lemma path. Prose that names a path without
# backticks is still scanned, and still caught.
# A path, not "any backticked text containing a slash". The first version was
# the latter, so wrapping a paragraph in backticks and putting one `/` in it
# hid every harness term in it from the scanner -- a bypass that costs one
# character. A path has no spaces and no sentence punctuation.
# LaTeX now, so the path markup is `\path{...}` or `\texttt{...}` rather than
# backticks. Same rule as before: it must look like a path -- no spaces, no
# sentence punctuation -- so that wrapping a paragraph in `\texttt{}` with one
# slash in it cannot hide a dozen harness terms from the scanner.
PATH_SPAN = re.compile(r"\\(?:path|texttt|verb|url)\{[^{}\s]*/[^{}\s]*\}")


def _strip_paths(line: str) -> str:
    return PATH_SPAN.sub(lambda m: "\u00b7" * len(m.group(0)), line)


def _hits(
    patterns: tuple[str, ...], lines: list[str], *, ignore_case: bool = True
) -> list[tuple[int, str]]:
    flags = re.MULTILINE | (re.IGNORECASE if ignore_case else 0)
    found: list[tuple[int, str]] = []
    for number, line in enumerate(lines, start=1):
        for pattern in patterns:
            for match in re.finditer(pattern, line, flags=flags):
                found.append((number, match.group(0)))
    return found


def check_structure(result: SummaryResult, sections, total_lines: int) -> None:
    titles = [title for title, _, _ in sections]
    missing = [name for name in REQUIRED_SECTIONS if name not in titles]
    if missing:
        result.errors.append(
            "missing required section(s): "
            + ", ".join(f"\\section{{{name}}}" for name in missing)
        )
    present = [name for name in REQUIRED_SECTIONS if name in titles]
    order = [titles.index(name) for name in present]
    if order != sorted(order):
        result.errors.append(
            "required headings are out of order; the fixed order is "
            + " → ".join(REQUIRED_SECTIONS)
        )

    for title, line_number, body in sections:
        if title not in EMPTY_STATE:
            continue
        text = _body_text(body)
        if not text:
            result.errors.append(
                f"\\section{{{title}}} (body line {line_number}) is empty; write its "
                f"empty-state line verbatim instead: "
                f"{EMPTY_STATE[title]}"
            )
        elif text == EMPTY_STATE[title]:
            continue

    for title, line_number, _ in sections:
        if title != "What is blocked":
            continue
        depth = line_number / max(total_lines, 1)
        result.metrics["blocker_depth"] = round(depth, 3)
        result.metrics["blocker_line"] = line_number
        # Either test may pass. A short document satisfies the absolute rule
        # however it is laid out; a long one is allowed a proportionate lead.
        if line_number > BLOCKER_MAX_LINE and depth > BLOCKER_MAX_DEPTH:
            result.errors.append(
                f"\\section{{What is blocked}} is at body line {line_number} "
                f"({depth:.0%} of "
                f"{total_lines}); it belongs in the first {BLOCKER_MAX_LINE} "
                f"lines, or the first {BLOCKER_MAX_DEPTH:.0%} of a longer file. "
                "The reader came for this"
            )


# Mathematical prose is full of full stops that do not end sentences. A genuine
# five-sentence lead measured nine, because `Lemma 3.1.`, `Prop. 2`, `i.e.` and
# `Ref. [4]` each looked like a boundary. Splitting on "period, space, capital"
# and excusing the known abbreviations is still approximate — but a lead rule
# that refuses correct mathematics is worse than one that occasionally undercounts.
_ABBREVIATION = re.compile(
    r"(?:\b(?:i\.e|e\.g|cf|resp|viz|et al|Prop|Thm|Lem|Cor|Def|Ref|Fig|Eq|Ch|Sec|No|vs)\.|"
    r"\b\d+(?:\.\d+)*\.)\s*$"
)


def _sentences(text: str) -> list[str]:
    out: list[str] = []
    current = ""
    for piece in re.split(r"(?<=[.!?])(\s+)", text):
        if piece.isspace():
            current += piece
            continue
        if current and not _ABBREVIATION.search(current) and re.match(r"[A-Z(\\$]", piece):
            out.append(current.strip())
            current = piece
        else:
            current += piece
    if current.strip():
        out.append(current.strip())
    return [s for s in out if s]


# An established result is a statement, a sketch of why it is true, and the
# path where the full proof lives -- in that order, labelled, one \item each.
#
# The rule this replaces said "one line each, plus the path to the proof". It
# was written against a note that was 97% pasted internal packets, and it
# overshot: the first real summary produced under it listed thirteen results as
# thirteen noun phrases and thirteen paths, so the document a person opens
# contained no mathematics at all. "The polynomial factorisation for all eight
# forms" is a label for a theorem, not a theorem. The reader could not see a
# single thing that had been proved.
#
# Labels rather than a word count, deliberately. A minimum length is a
# false-positive machine here: "exhaustive machine computation" is a complete
# and correct sketch for a finite range check, and a lint that refuses it is
# one the run learns to route around. Presence is decidable; quality is the
# reader's call, which is the same split the vocabulary checks already make.
STATEMENT_LABEL = re.compile(r"\\textbf\{Statement\.\}")
SKETCH_LABEL = re.compile(r"\\textbf\{Sketch\.\}")
SKETCH_BODY = re.compile(r"\\textbf\{Sketch\.\}(.*?)(?=\\path\{|$)", re.S)
SHORT_SKETCH_WORDS = 10

# Enough to show the shape of the mistake, few enough to read.
CASCADE_LIMIT = 3


def _items(body: list[str]) -> list[tuple[int, str]]:
    r"""(line number within the section, text) for each `\item`."""
    out: list[tuple[int, str]] = []
    current: list[str] | None = None
    start = 0
    for offset, line in enumerate(body):
        if "\\item" in line:
            if current is not None:
                out.append((start, "\n".join(current)))
            current, start = [line], offset
            continue
        if current is not None:
            current.append(line)
    if current is not None:
        out.append((start, "\n".join(current)))
    return out


def check_established(result: SummaryResult, sections) -> None:
    for title, line_number, body in sections:
        if title != "What is established":
            continue
        if _body_text(body) == EMPTY_STATE[title]:
            return
        items = _items(body)
        result.metrics["established_results"] = len(items)
        if not items:
            result.errors.append(
                "\\section{What is established} has no \\item; each established "
                "result is its own item, or the section carries its empty-state "
                "line"
            )
            return
        thin = 0
        broken: list[tuple[int, list[str]]] = []
        for offset, text in items:
            missing = []
            if not STATEMENT_LABEL.search(text):
                missing.append("\\textbf{Statement.}")
            if not SKETCH_LABEL.search(text):
                missing.append("\\textbf{Sketch.}")
            if not PATH_SPAN.search(text):
                missing.append("\\path{...} to the full proof")
            if missing:
                broken.append((line_number + offset, missing))
                continue
            sketch = SKETCH_BODY.search(text)
            if sketch and len(sketch.group(1).split()) < SHORT_SKETCH_WORDS:
                thin += 1

        # Cascade suppressed. The first version of this check reported all
        # thirteen results of the run that motivated it, in thirteen identical
        # paragraphs — which is precisely the defect P45 was written to fix,
        # reintroduced by the next gate to be added. When every item is wrong
        # the shape is wrong, and that is one finding.
        result.metrics["established_malformed"] = len(broken)
        for where, missing in broken[:CASCADE_LIMIT]:
            result.errors.append(
                f"established result at body line {where} is missing "
                + ", ".join(missing)
                + ". A result is the statement, a sketch of why it holds, and "
                "where the proof lives — a name and a path is a citation, not a "
                "result, and the reader cannot see any mathematics in it"
            )
        if len(broken) > CASCADE_LIMIT:
            result.errors.append(
                f"... and {len(broken) - CASCADE_LIMIT} further results in the "
                f"same shape ({len(broken)} of {len(items)} malformed). At that "
                "count the section's shape is the finding, not each item: see "
                "the worked example in progress-summary-example.md and rewrite "
                "the section once"
            )
        if thin:
            result.metrics["short_sketches"] = thin
            result.warnings.append(
                f"{thin} of {len(items)} sketches are under {SHORT_SKETCH_WORDS} "
                "words. Some results genuinely have a four-word sketch — a finite "
                "range checked by machine is one — so this is a question, not a "
                "verdict: read them and decide whether the argument is there"
            )
        return


def check_lead(result: SummaryResult, sections) -> None:
    for title, line_number, body in sections:
        if title != "Where this stands":
            continue
        text = _body_text(body)
        if not text:
            result.errors.append(
                f"\\section{{Where this stands}} (body line {line_number}) is empty; "
                f"it must say "
                "in its first sentence whether the original statement is proved, "
                "disproved, partially proved, or open"
            )
            return
        sentences = _sentences(text)
        result.metrics["lead_sentences"] = len(sentences)
        if len(sentences) > LEAD_MAX_SENTENCES:
            result.errors.append(
                f"\\section{{Where this stands}} runs to {len(sentences)} sentences; "
                f"at most {LEAD_MAX_SENTENCES}"
            )
        return


def check_budget(result: SummaryResult, text: str) -> None:
    lines = text.splitlines()
    size = len(text.encode("utf-8"))
    result.metrics["lines"] = len(lines)
    result.metrics["bytes"] = size
    if len(lines) > MAX_LINES:
        result.errors.append(
            f"{len(lines)} body lines against a cap of {MAX_LINES}. The cap belongs to "
            "the summary; do NOT shorten writer/progress_notes.tex to compensate — "
            "its length is what buys restartability (ADR 0021)"
        )
    if size > MAX_BYTES:
        result.errors.append(f"{size} bytes against a cap of {MAX_BYTES}")


def check_vocabulary(result: SummaryResult, text: str) -> None:
    lines = text.splitlines()
    scannable = [_strip_paths(line) for line in lines]
    hard = _hits(HARNESS_TERMS, scannable)
    # Case-insensitively. `Orchestrator` and `orchestrator` are the same role;
    # only the three that are also mathematical nouns are exempt, and they are
    # exempt by being on the density list rather than by their capitalisation.
    hard += _hits(ROLE_NAMES, scannable)
    hard.sort()
    result.metrics["harness_terms"] = len(hard)
    for number, token in hard[:20]:
        result.errors.append(
            f"line {number}: {token!r} is harness machinery, not mathematics"
        )
    if len(hard) > 20:
        result.errors.append(f"... and {len(hard) - 20} further harness terms")

    soft = _hits(AMBIGUOUS_TERMS, lines)
    density = len(soft) / max(len(lines), 1)
    result.metrics["bookkeeping_density"] = round(density, 3)
    if density >= AMBIGUOUS_MAX_DENSITY:
        sample = ", ".join(sorted({token.lower() for _, token in soft})[:8])
        result.warnings.append(
            f"bookkeeping-word density {density:.2f}/line against a corpus median "
            f"of 0.04 ({sample}). These words are also ordinary mathematics, so this "
            "is a warning: read the file and decide whether they are being used as "
            "mathematics or as scheduling"
        )


def _hits_multiline(patterns: tuple[str, ...], text: str) -> list[tuple[int, str]]:
    """Patterns that span lines, matched against the whole document.

    `_hits` iterates lines, which silently disables any pattern containing
    `\\n`. Keeping both and choosing per pattern is the fix; making `_hits`
    multiline would change every other check's line numbers.
    """
    found = []
    for pattern in patterns:
        for match in re.finditer(pattern, text, flags=re.IGNORECASE | re.MULTILINE):
            found.append((text.count("\n", 0, match.start()) + 1, match.group(0)))
    return found


def check_honesty(result: SummaryResult, text: str) -> None:
    lines = text.splitlines()
    for number, token in _hits(NUMERIC_DISTANCE, lines):
        result.errors.append(
            f"line {number}: {token!r} — distance to a proof is qualitative. "
            "A number here is a guess wearing a measurement as a costume"
        )
    for number, token in _hits(TELEMETRY, lines):
        result.errors.append(
            f"line {number}: {token!r} is process telemetry; the reader is asking "
            "about the mathematics"
        )
    for number, token in _hits(PASTE, lines):
        result.errors.append(
            f"line {number}: verbatim block ({token.splitlines()[0]!r}). A packet "
            "pasted into a document for a person summarises nothing — the most "
            "recent note in the corpus was 97% pasted"
        )


def check_preamble(result: SummaryResult, text: str, had_body: bool) -> None:
    """The summary must be a compilable standalone document, not a fragment.

    Checked because the artifact a person opens is the PDF: a `.tex` that does
    not compile leaves the reader with nothing, and leaves it looking exactly
    like a run that stopped without writing anything.
    """
    if not had_body:
        result.errors.append(
            "no \\begin{document}; the summary must be a standalone LaTeX file "
            "that compiles with pdflatex from writer/. Budgets and line numbers "
            "below were measured on the whole file as a result"
        )
    if "\\documentclass" not in text:
        result.errors.append("no \\documentclass; the summary is compiled, not included")
    if had_body and "\\end{document}" not in text:
        result.errors.append("no \\end{document}")


_PAGES = re.compile(r"Output written on .*?\((\d+) pages?[,)]")


def check_pages(result: SummaryResult, log: Path | None) -> None:
    """Page count, from the pdflatex log.

    Pages are the units the complaint was made in ("49 页"), so one check is
    made in them. Read from the log rather than the PDF because no PDF tooling
    is guaranteed present on the machines this runs on. No log means not
    checked, and the metric stays null so that nobody reads silence as a pass.
    """
    result.metrics["pages"] = None
    if log is None or not log.is_file():
        return
    match = _PAGES.search(log.read_text(encoding="utf-8", errors="replace"))
    if not match:
        return
    pages = int(match.group(1))
    result.metrics["pages"] = pages
    if pages > MAX_PAGES:
        result.errors.append(
            f"{pages} pages against a cap of {MAX_PAGES}. This is the same cap as "
            f"the {MAX_LINES}-line one in the units the reader actually counts; if "
            "the line count passed and this did not, the document is dense rather "
            "than long, and the fix is still to move material into "
            "writer/progress_notes.tex rather than to shrink that file"
        )


def check_pdf(result: SummaryResult, pdf: Path | None) -> None:
    if pdf is None:
        return
    result.metrics["pdf"] = str(pdf)
    if not pdf.is_file():
        result.errors.append(
            f"no {pdf}; the summary is compiled and exported to the workspace "
            "root beside progress_notes.pdf. A .tex nobody compiled is not the "
            "document a person reads"
        )


def lint_file(
    path: Path, *, pdf: Path | None = None, log: Path | None = None
) -> SummaryResult:
    result = SummaryResult()
    if not path.is_file():
        result.errors.append(
            f"no {path}; every non-proof stop writes one (see the Progress Summary "
            "section of prompts/writer.md)"
        )
        return result
    text = path.read_text(encoding="utf-8", errors="replace")
    body, preamble_lines = document_body(text)
    result.metrics["preamble_lines"] = preamble_lines
    sections = _sections(body)
    total = len(body.splitlines())
    check_preamble(result, text, preamble_lines > 0)
    check_budget(result, body)
    check_structure(result, sections, total)
    check_lead(result, sections)
    check_established(result, sections)
    check_vocabulary(result, body)
    check_honesty(result, body)
    check_pages(result, log)
    check_pdf(result, pdf)
    return result


def _paths(workspace: Path) -> tuple[Path, Path, Path]:
    """(source, exported pdf, compile log) for a workspace."""
    workspace = Path(workspace)
    source = workspace / SUMMARY_NAME
    return source, workspace / SUMMARY_PDF, source.with_suffix(".log")


def lint_workspace(workspace: Path) -> SummaryResult:
    source, pdf, log = _paths(workspace)
    return lint_file(source, pdf=pdf, log=log)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Progress summary: the stop document a person reads.",
        epilog=REQUIREMENT,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("workspace", type=Path)
    parser.add_argument(
        "--file",
        type=Path,
        help=(
            f"Lint this file instead of <workspace>/{SUMMARY_NAME}. The PDF and "
            "page checks are skipped, because neither is derivable from a bare "
            "path — use it to check a draft, not to clear a stop."
        ),
    )
    parser.add_argument("--json", action="store_true")
    waiver.add_waiver_arg(parser)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.file:
        target, result = args.file, lint_file(args.file)
    else:
        target = Path(args.workspace) / SUMMARY_NAME
        result = lint_workspace(args.workspace)

    result.errors, _waived = waiver.apply_waiver(
        result.errors, args.waive, gate="summary", workspace=args.workspace,
    )
    if args.json:
        print(
            json.dumps(
                {
                    "ok": result.ok,
                    "errors": result.errors,
                    "warnings": result.warnings,
                    "metrics": result.metrics,
                },
                ensure_ascii=False,
                indent=2,
                sort_keys=True,
            )
        )
    else:
        print(f"summary_gate: {'PASS' if result.ok else 'FAIL'} ({target})")
        for key, value in sorted(result.metrics.items()):
            print(f"  {key:<22}{value}")
        for error in result.errors:
            print(f"ERROR: {error}")
        for warning in result.warnings:
            print(f"WARNING: {warning}")
        waiver.print_waived(_waived, args.waive or "")
    if result.errors and not args.json:
        print()
        print(REQUIREMENT)
    return 0 if result.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
