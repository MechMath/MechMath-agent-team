---
name: proof-summarize
description: "Use when producing a concise human-readable proof_summary.tex from the final accepted proof, extracting reusable correct/error knowledge, and updating memory.md for recurring proof errors."
---

# Produce a Human-Readable Proof Summary

You are preparing two different outputs from one NL-Prover problem:

1. `proof_summary.tex`: a concise, normal mathematical proof for human readers.
2. Optional reusable knowledge notes and recurring-error memory.

Do not confuse these outputs. `proof_summary.tex` is not a run report, not a
post-mortem, and not a list of attempts. It should read like a short proof one
would send to a mathematician who only wants the final argument.

For reusable knowledge, extract only information that is worth retaining for
future work. Write ordinary correct/error notes into `../data/inbox` when useful
and maintain recurring error memory in the repository-root `memory.md`.

## Arguments

- Prefer the user-supplied problem directory name, for example `iwasawa_selmer`.
- If no problem directory name is supplied, choose the most recently modified
  directory under `../data/workspace`.

Call the selected directory:

- `../data/workspace/<problem_id>/`

It will usually contain at least:

- `problem.md`
- `STATUS.md`
- `proof.tex`
- optionally `sketch/`
- optionally `lemmas/*/generator/`
- optionally `lemmas/*/verifier/`
- optionally `[human-review]...[/human-review]` and `[review-content]...[/review-content]` blocks in proof artifacts

## Required Work

1. Read `problem.md` and identify the main goal and any top-level subproblems.
2. Read `STATUS.md` and extract:
   - the final completion state
   - any final result, lemma, reduction, proof pattern, or citation that looks reusable beyond this one problem
   - any meaningful failures, revisions, bottlenecks, strengthened hypotheses, corrected statements, or protocol issues recorded in the history
3. If present, inspect `lemmas/*/verifier/`, `lemmas/*/generator/response_to_verifier.md`, `sketch/revision_*.md`, `refinement/`, and any `[human-review]...[/human-review]` / `[review-content]...[/review-content]` blocks to recover concrete error causes and how they were fixed.
4. Read `proof.tex` to confirm the final accepted answer. If `STATUS.md` and `proof.tex` conflict, treat the final retained version in `proof.tex` as authoritative and explicitly note the mismatch.
5. Generate `proof_summary.tex`: a concise, human-readable LaTeX proof based on
   the final accepted `proof.tex`. It should present the shortest clear final
   route justified by the accepted proof, not a transcript of generated lemmas or
   verifier history.
6. Identify recurring-error memory candidates: repeated mistakes, human-reviewed complaints that the system "often", "again", "always", "keeps", "repeatedly", "usually", "frequently", "again made", or equivalent non-English wording makes the same error, or verifier failures that recur across multiple attempts.
7. Decide whether this run produced knowledge that is actually worth saving.
8. If yes, produce concise but information-dense Markdown notes and write them into `../data/inbox/`.
9. If no, do not create low-value notes. Still write `proof_summary.tex` when an accepted proof exists.

## Save Only High-Value Information

Do not write a note just because a problem was completed. Only save information that is likely to be useful later.

Good candidates for saving:

- an important lemma that emerged and can be reused in later proofs
- a proof technique, reduction pattern, or verification trick that generalizes
- a corrected statement that is easy to get wrong in future work
- a subtle hypothesis that turned out to be genuinely necessary
- a reliable citation or black-box theorem that resolved a recurring bottleneck
- a nontrivial counterexample that prevents repeating the same mistake
- a recurring proof mistake that future agents should actively avoid
- a human-stated workflow preference tied to an error pattern, such as "do not add hidden hypotheses" or "always check terminal lemmas entail the main theorem"

Do not save:

- routine progress logs
- obvious facts already standard in the project
- problem-specific details that are unlikely to matter again
- generic comments with no future reuse value
- one-off verifier complaints that were purely local and do not indicate a reusable error pattern

## What the Notes Must Capture

This is not a simple timeline. It must clearly separate three possible kinds of reusable information.

### 1. Final Correct Answers

- Only include reusable correct knowledge
- Prefer items such as:
  - a reusable lemma
  - a proof template or argument pattern
  - a corrected final formulation worth reusing
  - an essential assumption or citation that should be remembered

### 2. Error Causes and Fixes

Prioritize substantive mathematical or workflow mistakes, not vague comments like "there was a bug".

Examples of valuable failure analysis:

- a statement was false as written, and what the corrected statement is
- an argument was missing a hypothesis, and which hypothesis had to be added
- a local calculation, sign convention, group-action argument, dimension count, or local-global passage was wrong
- why a verifier returned `NEEDS_REVISION` or `FAIL`
- how the final accepted version repaired the issue

If you cannot find reusable error knowledge, do not create an error note. Do not invent one.

### 3. Error Memory

Maintain error memory only for high-confidence recurring mistakes or human-stated correction patterns that should guide future proofs.

Good triggers:

- Human review explicitly says the system "often", "again", "always", "keeps",
  "repeatedly", "usually", "frequently", "again made", or equivalent
  non-English wording makes this mistake. In this case, you MUST update
  `memory.md` unless the statement is incoherent or unsafe.
- The same verifier complaint appears in multiple attempts, lemmas, or problem runs visible in this workspace.
- The error is a common mathematical failure mode with a clear prevention rule.
- The human explicitly says to remember the issue.

Examples:

- Do not assume compactness from continuity.
- Do not use Noetherian induction unless Noetherian hypotheses are stated or proved.
- Terminal lemmas must entail the main theorem, not just local facts.
- Do not add hidden hypotheses to repair a failing proof.

Do not create memory for:

- a single typo,
- a one-off missing citation,
- a proof-local gap that has no general lesson,
- an uncertain diagnosis.

Human workflow preferences should be folded into error memory only when they are tied to a concrete recurring error pattern. For example, "When human review flags an added assumption, treat it as a blocker and repair without strengthening hypotheses" is valid memory. A generic preference like "be careful" is not.

Memory is stored only in repository-root `memory.md`, not in KB-Manager and not in
`../data/inbox`. Before editing `memory.md`, read the existing file if present.
Merge, deduplicate, and tighten entries instead of appending blindly. Keep the
entire file at 100 lines or fewer. If adding a new entry would exceed 100 lines,
compress older entries, merge related rules, or remove lower-value details while
preserving high-priority human-stated recurring errors.

Write `memory.md` in English only, even when the trigger feedback was written in
another language.

## Output Format

Write separate Markdown notes when justified:

1. a `correct` note for reusable correct knowledge
2. an `errors` note for reusable mistakes, failure modes, and fixes
3. an update to repository-root `memory.md` for high-confidence recurring error patterns

You may write only the categories that contain high-value material.

Always write `proof_summary.tex` when `proof.tex` contains an accepted proof.
This file is the human-facing concise proof, not blueprint dependency tracking
and not a proof-run report. It should be much shorter than `proof.tex`, usually
2 to 6 pages when compiled unless the problem itself has many independent parts.

The summary may merge routine lemmas into the main argument, omit bookkeeping
lemmas, and streamline notation, but only when the resulting proof remains
mathematically justified by the accepted `proof.tex`.

Use these templates by default.

```md
# <problem_id> Correct Knowledge

## Source
- ...

## Reusable Results
- ...

## Reusable Techniques
- ...

## Final Assumptions and References Used
- ...
```

```md
# <problem_id> Error Knowledge

## Source
- ...

## Failure Modes
- Mistake:
  Cause:
  Fix:

## Things To Watch Next Time
- ...
```

Use this compact format for `memory.md`:

```md
# NL-Prover Error Memory

- Rule: <short imperative rule>
  Why: <brief reason>
  Trigger: <human-review/repeated verifier/source problem_id>
```

Each memory item should normally be 2 to 4 lines. Prefer durable rules over
long narratives.

Use an article-style proof structure for `proof_summary.tex`. The exact section
names should fit the problem, but the document should look like a compact final
proof rather than a report. Prefer this pattern:

```tex
\documentclass{article}
\usepackage[]{KLMM/klmm}

\title{Concise Proof: <problem_id>}
\author{NL-Prover}
\date{\today}

\begin{document}
\maketitle

\section{<problem name or main case>}
<brief self-contained setup: notation, hypotheses, and definitions needed for
the proof. Do not include workflow history.>

\begin{theorem}[<main result>]
<faithful statement of the theorem proved by the accepted proof>
\end{theorem}

\section{<essential condition, construction, or ingredient>}
<state only the definitions or standard inputs needed for the final proof.>

\begin{proposition}[<essential intermediate claim>]
<claim needed for the theorem>
\end{proposition}
\begin{proof}
<concise proof, merging routine sublemmas into the text when possible>
\end{proof}

\section{Final assembly}
\begin{proof}[Proof of the theorem]
<short final derivation from the essential ingredients>
\end{proof}

\begin{remark}[Scope]
<optional: only if the accepted proof proves a restricted case or relies on a
specific branch/hypothesis that a reader might otherwise miss>
\end{remark}
\end{document}
```

Requirements for `proof_summary.tex`:

- Write in English.
- Keep the theorem statement mathematically faithful to `proof.tex`.
- Choose section titles that match the mathematics, such as "Article
  conditions", "Selmer membership", or "Final assembly"; avoid generic
  report-like titles when a mathematical title is available.
- Write a clean final proof, not a process summary. Do not describe what agents
  tried, which attempts failed, which verifier reports were produced, or how the
  proof was repaired.
- Prefer a direct narrative proof over a lemma-by-lemma transcript, but keep
  theorem/proposition/lemma environments for intermediate claims that are
  genuinely needed to make the argument readable.
- Include only intermediate claims that are necessary for a human to understand
  and trust the argument.
- If the final theorem depends on a small number of essential conditions,
  propositions, or local checks, present exactly those and then give a short
  final assembly proof.
- Remove internal markers such as `\uses{}`, `\sorry`, verifier scores, attempt
  numbers, and agent workflow details.
- Do not introduce new claims, new hypotheses, or shortcuts not justified by the
  accepted proof.
- Do not include failed routes, rejected refinements, implementation details,
  file paths, status history, or reusable-error notes in `proof_summary.tex`.
- Put reusable correct/error knowledge only in the Markdown notes under
  `../data/inbox/`, not in the proof summary.
- If the accepted proof is incomplete or contains `\sorry`, write a clearly
  labeled "Incomplete Proof Summary" instead of pretending the proof is complete.
- Use the KLMM document template family: the preamble must load it with
  `\usepackage[]{KLMM/klmm}`. Before compiling `proof_summary.tex` to PDF, copy
  the repository's `tex/KLMM/` directory into the same directory as
  `proof_summary.tex` (e.g.
  `cp -R tex/KLMM ../data/workspace/<problem_id>/`), then compile from that
  directory. For reader-facing article or progress outputs, Writer should use
  repo-root `tex/template.tex` as the structural starting point. See the LaTeX
  build policy for full details.

Requirements:

- Write in English.
- Keep mathematical notation, lemma labels, and Problem 1 / Problem 2 / P1 / P2 naming when helpful.
- Be specific and grounded in the files you read.
- Do not paste long raw excerpts; synthesize and compress.
- Prefer reusable items over per-problem narration.
- If there are multiple top-level problems, only mention the ones needed to explain the saved knowledge.

## Output File

For reusable correct knowledge, create:

- `<problem_id>_correct.md`

For reusable error knowledge, create:

- `<problem_id>_errors.md`

If a target filename already exists, use:

- `<problem_id>_correct_<YYYYMMDD_HHMMSS>.md`
- `<problem_id>_errors_<YYYYMMDD_HHMMSS>.md`

For recurring error memory, update repository-root:

- `memory.md`

Do not create per-problem memory files.

For the human-readable proof report, create or overwrite:

- `../data/workspace/<problem_id>/proof_summary.tex`

## Final Response Back to the User

After finishing:

1. State which `problem_id` you used.
2. State which files were created, if any.
3. State whether `memory.md` was updated.
4. State whether `proof_summary.tex` was created or updated.
5. Give a short 3 to 6 bullet report of the most important reusable conclusions.
6. If no note was created and `memory.md` was not updated, explicitly say that the run did not yield reusable knowledge worth saving.

## Strict Constraints

- Do not modify source files under `../data/workspace/<problem_id>/`, except
  that you MUST create or update `proof_summary.tex` there when an accepted proof
  exists.
- Create ordinary correct/error notes only in `../data/inbox/`.
- Maintain recurring error memory only in repository-root `memory.md`.
- Keep `memory.md` at 100 lines or fewer.
- Do not write directly into KB-Manager from this command.
- If `STATUS.md` is missing, still produce the summary from `problem.md` and `proof.tex`, and explicitly say that failure analysis is based only on the surviving files.
- If `proof.tex` still contains obvious unfinished markers such as `\sorry`, explicitly state that the problem is not fully complete.
