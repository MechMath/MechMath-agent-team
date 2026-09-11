# ADR 0021 — Mandatory Progress Notes at Every Stop, and Plain Output Names

- **Status**: Accepted — implemented, 2026-07-24
- **Supersedes**: the progress-note parts of ADR 0011 §3 and the export-name
  parts of ADR 0011/0012 (the rest of those ADRs stands).
- **Amended by**: ADR 0025 (2026-08-25). See the block below.

> **Amendment (2026-08-25, ADR 0025). A non-proof stop now produces two
> documents, not one.** Everything below stands as written — the artifact, the
> five sections, and the trade in Consequences ("length here buys
> restartability") are unchanged and are not capped. What changed is that
> §A's list of what a stop owes is no longer complete, and §B.2's "written out
> in full" acquired one clause.
>
> - **§A** — a non-proof stop also writes `writer/progress_summary.tex` and
>   exports `progress_summary.pdf` to the workspace root: six fixed sections
>   with the blocker second, ≤ 300 body lines / 32 KB / 10 pages, no proof text,
>   no harness vocabulary, every coined term defined. (Amended 2026-08-28 from
>   markdown at ≤ 120 lines / 12 KB — ADR 0025's Amendment.) Its reader is
>   the person deciding what to do about the run; the reader of
>   `progress_notes.tex` is still the next run. `gate stop`
>   (`validate_stop_export`) requires both as errors; the new `gate summary`
>   (`cli_tools/_gate/summary.py`) checks the summary and never the note.
>   Measured cause: the 24 notes on disk split into 16 written before this ADR
>   averaging 463 lines and 8 written after averaging 4,613, and across the 11
>   notes with an identifiable blocker the blocker sits past 85% of the file in
>   7 of them. The order, not the length, is what a person could not use.
> - **§B.2** — "complete proof written out in full" means restated as
>   mathematics, **never pasted as an artifact**. The most recent note is 21,215
>   lines of which 20,655 (97.4%) sit inside `\begin{verbatim}`. Where a result
>   truly cannot be restated, state it, cite the artifact's path, and say in one
>   sentence why — the only case in which a path replaces a proof. `gate stop`
>   warns (never errors) on verbatim bulk, so this cannot become a back door to
>   capping the note.
>
> Nothing else here is amended. See ADR 0025 for the reasoning and the gate.

## Context

Two defects in the presentation layer.

**1. A stopped run could leave nothing behind.** ADR 0011 made the progress note
*conditional*: Writer wrote `progress_note.tex` "only when the human asks to
pause, stop, or summarize progress", and `prompts/orchestration.md` said
explicitly "do not automatically stop to write a report … unless the human asks
for a progress note". That wording was aimed at a real failure — stopping early
in order to write a report instead of continuing the branch queue — but it had a
bad side effect: a *permitted* stop (branch budget exhausted, human-needed
ambiguity, verified obstruction) could end with no reader-facing artifact at all.
The run's verified lemmas, its dead ends, and the reasons they died stayed inside
the workspace, recoverable only by reading the whole thing.

Worse, the format that did exist was not a restart document. It asked for
"verified mathematical content already established" — a *summary*. A summary of a
verified lemma is not reusable: whoever resumes has to re-derive or re-verify it.
And it listed attempted routes only "when they explain why the blocker is the
current one", which throws away exactly the negative information — this route
failed, and here is the step that killed it — that stops a later run from
repeating the same dead end.

**2. The exported names editorialized.** `well-written-proof.pdf` and
`well-written-progress.pdf` assert a quality judgement in the filename, in the
harness's own voice, about output it produced itself.

## Decision

### A. Progress notes are mandatory before every non-proof stop

Before any stop permitted by `stop-conditions.md` that is **not** a verified
proof of the original statement, the Orchestrator dispatches Writer in
`PROGRESS_NOTES` mode and exports `progress_notes.pdf`.

The original anti-pattern stays barred, and the distinction is stated wherever
the rule appears: this is a requirement **at** a stop, never a reason **to**
stop. An incomplete proof still continues under the branch-queue rules; writing
a good progress note is not a stop condition.

### B. Five required sections

The note is a **restart document**: a reader who sees only this file should be
able to resume without the workspace. It opens with the exact statement, scope,
hypotheses, and notation, then carries five sections in order — none omitted, a
section with nothing to report says so in one sentence:

1. **Routes explored** — each as a mathematical strategy, not an agent
   transcript.
2. **Verified results, with their detailed proofs** — every result carrying a
   fresh Verifier `PASS`, stated exactly and followed by its **complete proof
   written out in full**. Not a sketch, not an internal path, not the assertion
   that it was verified. This is the change that makes the note durable output
   rather than a status report.
3. **Failed explorations** — each abandoned route with the precise reason it
   died and what would have to change to revive it.
4. **Possible next paths** — ordered by judged promise, each with the atomic
   obligation it discharges; names the current atomic blocker.
5. **Literature summary** — per load-bearing reference: what it provides, the
   exact statement form used or sought, whether preconditions were confirmed.

Format SSOT: `.agents/skills/article-writing/references/progress-note.md`.

### C. Plain output names

| Old | New |
|-----|-----|
| `well-written-proof.pdf` | `proof.pdf` |
| `well-written-progress.pdf` | `progress_notes.pdf` |
| `writer/progress_note.tex` | `writer/progress_notes.tex` |
| Writer output type `PROGRESS_NOTE` | `PROGRESS_NOTES` |

`proof.pdf` is the **Writer export**, not a compilation product of the
authoritative `proof.tex`. The two would collide if `proof.tex` were ever
compiled in place, so the rule "never compile `proof.tex` into the workspace
root" is recorded in `prompts/references/latex-and-blueprint.md` and
`prompts/orchestration.md` alongside the names.

## Consequences

- A stopped run always leaves a self-contained mathematical document. Verified
  lemmas survive the workspace; dead ends are recorded with their cause, so a
  later run does not re-walk them.
- Progress notes get longer, because they now inline full proofs. This is
  intended: length here buys restartability, and the note is written once per
  stop.
- Per ADR 0020's SSOT discipline, the five-section format is stated once (the
  skill reference) and pointed at from `prompts/writer.md`,
  `article-writing/SKILL.md`, `stop-conditions.md`, `orchestrator-cookbook.md`,
  `AGENTS.md`, and `CLAUDE.md`.
- Mechanical index globs (`_workspace/presentation.py`,
  `_memory/local.py`) match the new names; the presentation payload key
  `well_written_pdfs` became `export_pdfs`.
- Historical ADRs 0011/0012/0013/0016 keep the old names as written; they are
  records, and this ADR is the pointer that supersedes them.
