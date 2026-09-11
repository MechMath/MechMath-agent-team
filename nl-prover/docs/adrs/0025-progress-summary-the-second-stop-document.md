# ADR 0025 — A Stop Owes Two Documents: the Progress Summary

- **Status**: Accepted — implemented, 2026-08-25.
- **Extends**: ADR 0021 (mandatory progress notes at every stop). **ADR 0021 is
  not superseded.** Its artifact, its five sections, and its central trade —
  "length here buys restartability" — all stand unchanged. This ADR adds a
  *second* artifact with a *different reader*, and amends ADR 0021 only in that
  a non-proof stop now owes two files rather than one.
- **Evidence**: the 24 progress notes in the workspace corpus (line counts and
  mtimes as of 2026-08-25); `cli_tools/_gate/summary.py`, `prompts/writer.md`
  §"Progress Summary", `.agents/skills/article-writing/references/progress-note.md`.

> **Why a new ADR and not an amendment to 0021.** The mechanical test used here
> is the one ADR 0020 §SSOT applies to documents: an amendment records that a
> decision's *implementation* moved; a new ADR records that a *new object* now
> exists with its own reader, its own format SSOT, and its own gate. All three
> are true. `progress_summary.tex` is not a variant of `progress_notes.tex` and
> must never become a truncation of it — the two are permitted to contradict
> each other on length and density, which is precisely the relationship an
> in-place amendment cannot express without making ADR 0021 argue with itself.
> ADR 0021 carries a pointer here; nothing in the record now asserts that a stop
> produces one document.

## Context

ADR 0021 made the progress note mandatory at every non-proof stop and made it a
**restart document**: full proofs inlined, no length cap, reader = the next run.
It said so explicitly, and accepted the consequence — *"Progress notes get
longer, because they now inline full proofs. This is intended: length here buys
restartability."*

That trade was correct for the reader it named. Measured across the corpus, it
was also complete: the 24 notes on disk split at ADR 0021's date into **16
written before, averaging 463 lines**, and **8 written after, averaging 4,613
lines** — a factor of ten, exactly as designed. The most recent, `connes`, is
**21,215 lines**.

The defect is that ADR 0021 named one reader and there are two.

**1. The person deciding what to do about the run cannot use the note.** They
want one thing — what happened, and what is in the way — and the mandated
section order puts the blocker in §4 of 5, after every route explored and every
proof written out in full. Measured over the 11 notes carrying an identifiable
blocker: **it sits past 85% of the file in 7 of them**, and past 99% in the
longest. That is a property of the section order, not of the writing, so no
instruction to "write better notes" reaches it.

**2. Length invited pasting, and pasting was not what was bought.** ADR 0021's
"write the complete proof out in full" and the Core Rules' "do not alter proof
logic" read together as permitting verbatim reproduction. In `connes`, **20,655
of 21,215 lines — 97.4% — sit inside `\begin{verbatim}`**: 42 internal packets
pasted into LaTeX, markdown headings and all. It is a directory with a preamble.
It is also **the only file in 24 with any verbatim dumping**, so this is a
failure of an under-specified rule, not the corpus norm.

**3. Nothing in the note was mechanically checkable, and correctly so.** "Too
long · misses the point · badly structured · too much self-invented vocabulary ·
does not accurately summarise progress" — every one of those complaints is
decidable on a bounded markdown file and none of them is decidable on an
unbounded restart document.

## Decision

### A. A non-proof stop produces two documents, not one

| file | reader | cap | contains |
|---|---|---|---|
| `writer/progress_notes.tex` (+ `progress_notes.pdf`) | the next run | none | full proofs, all five ADR 0021 sections |
| `writer/progress_summary.tex` (+ `progress_summary.pdf`) | the person deciding what to do about the run | ≤ 300 body lines / 32 KB / 10 pages | the statement; each result as statement + sketch + path |

Both are required by `gate stop` (`validate_stop_export`), as **errors**, on the
same non-proof stop path ADR 0021 established.

*(Row amended twice on 2026-08-28 — see the two Amendments at the end. As first written the
summary was markdown at the workspace root, capped at 120 lines / 12 KB.)*

They are two files with two readers. **Do not merge them, and do not make one a
truncation of the other.**

### B. Six fixed headings, the blocker second

```
## Where this stands
## What is blocked
## What is established
## What was ruled out
## What to do next
## Terms coined here
```

Verbatim, in this order, none omitted. The order is the whole point of the
document: `## Where this stands` is at most five sentences and its first
sentence says whether the original statement is proved, disproved, partially
proved, or open — never what the run *did* — and the blocker is second rather
than measured at 85% depth.

A section with nothing to report carries a fixed empty-state line rather than
being blank or dropped (`_(nothing has been verified yet)_` and its four
siblings). An absent section and an empty one are different findings.

Further hard rules, each answering one clause of the complaint above: **no proof
text** (a verified result is one line — the statement in words, and the path
where its proof lives); **no verbatim blocks**; **no harness vocabulary** (no
review packets, verdict tokens, role names, gate names, `Depends-on:` lines,
`STATUS.md`, run ids, workspace paths beyond the one path per established
result); **no numeric distance** ("80% done", "≈8–12 lemmas left" — a number
here is a guess wearing a measurement as a costume); **every coined term
defined** in `## Terms coined here`, because runs mint vocabulary constantly
(`CV5-C`, `Owner Bridge`, "printed apparatus") and define it nowhere.

### C. `gate summary` checks all of it, and never repairs

`cli_tools/_gate/summary.py`, wired into the facade as `gate summary`. Each
clause of the complaint gets its own mechanical check — structure, lead,
budget (`MAX_LINES = 120`, `MAX_BYTES = 12_288`), vocabulary, honesty — rather
than one instruction asking for "a good summary".

**It reports and blocks; it does not rewrite the file it is judging.** A clean
artifact that exists and a clean artifact that was *produced* must not be
allowed to diverge, and a gate that repairs makes them diverge silently.

`gate summary` reads `writer/progress_summary.tex` and **never**
`progress_notes.tex`.
The restart document has no cap and must not acquire one through this gate.

### D. A verified proof is restated, or its path is cited — never pasted

ADR 0021 §B.2 asked for the complete proof "written out in full". That stands,
with one clause added: **not by pasting the artifact.** Restating a proof in
prose, with its own theorem environment and its own notation, is not altering
its logic — it is the work.

If a result genuinely cannot be restated without changing what it claims, that
is a finding: state the result, cite the artifact's path, and say in one
sentence why it resisted. That is the only case in which a path replaces a
proof.

`gate stop` (`validate_notes_are_written_not_pasted`) warns on verbatim bulk in
the note. **Warning, not error** — ADR 0021 bought that length deliberately and
this must not become a back door to capping it. What is counted is pasting, not
length.

## Consequences

- A stop now costs one more artifact. The summary is ≤ 120 lines against a
  restart document that averages 4,613, so the marginal cost is ~2.5%, and it is
  paid once per stop.
- The two documents will diverge in tone and density. That is the design, not
  drift, and no gate should ever be written to reconcile them.
- Per ADR 0020's SSOT discipline the six-heading format is stated once, in
  `prompts/writer.md` §"Progress Summary", with the worked example in
  `.agents/skills/article-writing/references/progress-summary-example.md`, and
  pointed at from `article-writing/SKILL.md`, `stop-conditions.md`, `AGENTS.md`
  and `CLAUDE.md`. The five-section restart format keeps its own SSOT at
  `.agents/skills/article-writing/references/progress-note.md`.
- `HARNESS_TERMS` is a growing list inside a gate. Its entry condition is
  narrow — a term qualifies only if it is *never* also ordinary mathematical
  English — and that condition, not the list, is the thing to defend when it is
  next extended.
- The blocker-depth measurement (85% in 7 of 11) was taken once, before the
  summary existed. It is not re-derivable after the fact and is recorded here
  and in `summary.py` for that reason.

## Amendment, 2026-08-28 — the summary is typeset, and the cap is three times higher

Two corrections from the human, before the first run under this ADR had
produced a single summary. Both are about the same mistake: the length axis and
the format axis were conflated, so the document tiers came out as *long and
typeset* versus *short and plain*, and the cell a person actually wants — short
and typeset — was the one that did not exist.

**A. The summary is LaTeX compiled to `progress_summary.pdf`.** Format follows
the reader, not the length. The summary is the document a person opens; it
carries mathematics they are expected to read in one sitting, and a raw
`$\pi_1(X)$` in a markdown file is not a summary of anything. The restart
document was being typeset for a reader — "a mathematician resuming the work" —
whose existence this ADR asserted and never checked, while the document with a
named, present reader was the plain one. What separates the two documents is now
only the cap and the section order, which is what was ever different about them.

**B. 120 lines was one screen, and one screen is too few.** Six sections cannot
hold an established-results list, a ruled-out list and a next-step list at one
line each without the cap doing the writing. Now 300 body lines, 32 KB, and 10
pages. *Body* means after `\begin{document}`, so a preamble does not spend the
budget — under the old rule a longer preamble made a shorter document, which is
the opposite of the point. The failure being guarded against is 21,215 lines and
49 pages; 300 is two orders of magnitude below it. The lead cap moved 5 → 8
sentences for the same reason.

**What this gives up, and why it is acceptable.** The original decision chose
markdown explicitly so that "the summary cannot fail to exist because a LaTeX
build did". That risk is now real and is answered by making the failure loud
rather than absent: `gate stop` requires the `.tex` **and** the exported PDF as
errors, and `gate summary` refuses a source with no `\begin{document}`. A build
that fails therefore blocks the stop, where before it could only have produced
nothing quietly. This is a worse failure mode traded for a better artifact, with
the trade made visible — if a run is ever blocked at a stop by a LaTeX error in
the summary, that is this decision presenting its bill, and it is the thing to
re-open, not to waive.

**Third instrument: pages.** The complaint was made in pages ("49 页"), so one
check is made in pages. It is read from the pdflatex log rather than from the
PDF, because no PDF tooling is guaranteed present; no log means the check does
not run, and the metric reports `null` rather than passing silently.

**Not changed.** The six sections, their order, the blocker-second rule, the
vocabulary split between hard terms and density, the refusal-not-repair rule,
and the restart document's freedom from any cap. The kill condition in P43
stands as written: zero refusals over six runs and this gate is deleted.

## Amendment 2, 2026-08-28 — a citation is not a result, and a status needs a subject

The first summary written under this ADR passed every check — 104 body lines
against a cap of 300, 2 pages against a cap of 10, no harness vocabulary, blocker
at body line 15 — and the human's verdict was that it was mostly references and
showed nothing. They were right, and both faults are in the spec, not the run.

**A. `\section{The statement}` is now the first required section.** The summary
reported on a problem it never stated. The title said *"Sumset-Complement Claim
for Eight Forms Modulo 24"*, the lead said the statement was open and equivalent
to a two-prime Goldbach problem, and a reader still could not say what the eight
forms were or what $S$ was. `progress-note.md` requires the restart document to
open with the exact statement, scope, hypotheses and notation; the summary asked
for a *status* and never for the thing the status is about — so the one document
a person opens was the one that assumed they already knew. The blocker rule
moves with it: third section, first 40 body lines rather than 24.

**B. An established result is a statement, a sketch, and a path.** Amendment 1's
rule — *"one line each, plus the path to the proof"* — was written against a note
that was 97% pasted internal packets, and it overshot. Thirteen results came out
as thirteen noun phrases and thirteen paths, so a two-page document about
mathematics contained none of it. "The polynomial factorisation for all eight
forms: `lemmas/identity/`" is a label for a theorem, not a theorem.

Each result now carries `\textbf{Statement.}` (what was proved, in symbols,
standing on its own), `\textbf{Sketch.}` (why it is true, in two or three
sentences — the mechanism, not the proof) and `\path{...}`. All three are
required and all three are checked.

**Labels, not a word count.** A minimum length would be a false-positive machine
here: *"exhaustive machine computation"* is a complete and correct sketch for a
finite-range check, and a lint that refuses it is one the run learns to route
around. Presence is decidable and is an error; a sketch under ten words is
counted and raised as a **warning** phrased as a question. Same split as the
bookkeeping-density check.

**The caps were never the constraint, and must not be "fixed" by moving them.**
The document was at a third of its line budget and a fifth of its page budget.
The rule was doing the shortening, so the rule is what changed; 300 / 32 KB / 10
pages stand, restated in `prompts/writer.md` as ceilings rather than targets.
A later round tempted to raise a cap here should read this paragraph first.

**One defect found in this amendment's own first draft.** It reported all
thirteen malformed results as thirteen identical errors — exactly the failure
P45 exists to fix, reintroduced by the next gate to be added. Per-item errors
are now capped at three with the full count preserved in
`established_malformed`, because when every item is wrong the *shape* is wrong
and that is one finding.

**Expectation, replacing Amendment 1's.** Over the next 6 non-proof stops: every
summary states its problem in its first section, and every established result
carries a statement and a sketch a reader can follow without opening the path.
**Falsifier** statements that are the old noun phrase with `\textbf{Statement.}`
in front of it, or sketches that restate the statement. Both satisfy the gate
and defeat the point, neither is mechanically detectable, and the human reading
one page is the instrument.
