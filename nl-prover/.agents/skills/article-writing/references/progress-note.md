# Progress Notes

Write `writer/progress_notes.tex` whenever the run stops without a verified
proof of the original statement — a blocked route, an exhausted branch budget, a
human-requested pause, or a human-needed ambiguity. This is mandatory before
stopping, not an optional report (see
`.agents/skills/nl-prover/references/stop-conditions.md`). A progress note is not
a final mathematical result. The file must be standalone LaTeX that the
Orchestrator can compile and export as `progress_notes.pdf`.

The note is a **restart document**: a mathematician (or a later run) who reads
only this file should be able to resume the work without reading the workspace.
That is why it carries full proofs of what is already verified, not summaries of
them.

## Required Sections

Open with the exact problem or theorem under consideration — statement, scope,
hypotheses, and notation — then write these five sections in this order. None may
be omitted; a section with nothing to report says so explicitly in one sentence.

### 1. Routes explored

The route portfolio actually attempted, each as a mathematical strategy, not as
an agent transcript: the idea, the objects it introduces, and what it would have
yielded had it closed. Include routes that are still open or partially advanced.

### 2. Verified results, with their detailed proofs

Every lemma, proposition, or intermediate theorem that carries a fresh Verifier
`PASS`, stated exactly and followed by its **complete proof**, written out in
full. Do not compress a verified proof into a sketch, a pointer to an internal
path, or a claim that it "was verified" — reproduce the mathematics. These are
the run's durable output and must survive independently of the workspace.

Mark the verification status of each result explicitly, and keep unverified
material out of this section (it belongs in section 1 or 4).

### 3. Failed explorations

Routes that were tried and abandoned, each with the precise reason it failed:
the step that could not be justified, the false or unprovable intermediate
claim, the counterexample or boundary case found, the theorem whose precondition
could not be met, or the estimate that was too weak. State what would have to
change for the route to become viable again. A route recorded here without a
reason is not a useful record.

### 4. Possible next paths

Concrete restartable next work, ordered by judged promise. For each: the
mathematical idea, the atomic obligation it would discharge, and the evidence or
construction needed to attempt it. This section must name the current atomic
blocker — a missing construction, theorem statement, definition, computation,
bridge, or counterexample audit — and what kind of idea would resolve it.

### 5. Literature summary

A short summary of the sources collected during the run: for each load-bearing
reference, what it provides, the exact form of the statement used or sought, and
whether its preconditions were confirmed. Cite with the ledger-backed keys (see
[mathematical-grounding.md](mathematical-grounding.md)). Keep it to the
mathematically relevant content — this is a reading guide for whoever resumes,
not a bibliography dump. Say so explicitly if no external source was
load-bearing.

## Forbidden Content

Do not include:

- owner or agent scheduling details;
- a transcript of which agent did what;
- long internal path lists;
- terminal language such as "there is no proof" unless a verified obstruction
  exists;
- unsupported claims that a missing source theorem makes the target false;
- a verified result stated without its proof.

## Suggested LaTeX Shape

When the user supplies no template, default to the repository KLMM template.
Read repo-root `tex/template.tex` and adapt its structure to a progress note.
Keep the generated output standalone. Load the style with
`\usepackage[]{KLMM/klmm}` and, when a bibliography is present, select
`\bibliographystyle{KLMM/klmm}`. The Orchestrator copies the repo-root
`tex/KLMM/` directory next to the `.tex` before compiling.

```tex
\documentclass{article}
\usepackage[]{KLMM/klmm}

\begin{document}

\section*{Progress Notes}

This note records the current mathematical state. It is not a final proof or a
final obstruction.

\section{Problem}
% exact statement, scope, hypotheses, notation
...

\section{Routes explored}
...

\section{Verified results}
% each stated exactly, each followed by its complete proof
\begin{lemma}...\end{lemma}
\begin{proof}...\end{proof}

\section{Failed explorations}
% each with the precise reason it failed
...

\section{Possible next paths}
% including the current atomic blocker
...

\section{Literature}
...

\end{document}
```

State the current state as a partial theorem, progress proposition, or
conditional statement wherever that is honest — it is more useful to a reader
than prose about what is missing. Verified results carry their proofs in full;
everything else is clearly labelled as candidate or failed.
