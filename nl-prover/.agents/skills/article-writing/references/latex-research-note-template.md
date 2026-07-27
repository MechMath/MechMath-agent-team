# LaTeX Research Note Template

Use this structure for `writer/article_candidate.tex` unless the user supplies a
different venue or format. The same file is used for `FULL_ARTICLE` and
`COMPLETE_PROOF` requests. The file must be standalone LaTeX that the
Orchestrator can compile and export as `well-written-proof.pdf`.

## Default Template

When the user supplies no template, venue, or format, default to the repository
KLMM template. Read repo-root `tex/template.tex` and use it as the structural
starting point for `writer/article_candidate.tex`. Keep the generated output
standalone: do not `\input` the repo template. Load the style with
`\usepackage[]{KLMM/klmm}` and, when a bibliography is present, select
`\bibliographystyle{KLMM/klmm}`. The Orchestrator copies the repo-root
`tex/KLMM/` directory next to the `.tex` before compiling. Only depart from the
KLMM template when the user explicitly provides a different template or venue.

## Planning

Write `writer/article_plan.md` when it helps. Keep it short and skip irrelevant
sections.

Possible plan fields:

- main theorem;
- motivation;
- notation setup;
- proof idea;
- technical lemmas;
- final proof route;
- remarks or examples, if genuinely useful;
- citation obligations.

## Default Article Shape

```tex
\documentclass{article}
\usepackage[]{KLMM/klmm}

\begin{document}
\maketitle

\section{Introduction}

<Short problem statement and main result. Avoid run history.>

\section{Notation and Preliminaries}

<Only the notation and standard facts needed for the proof.>

\section{Main Argument}

<Theorem/proof-centered exposition. Lemmas may be included when they improve
readability.>

\section{Remarks}

<Optional. Include only useful comments, examples, limitations, or citation
TODOs.>

% Include only when references are present.
\bibliographystyle{KLMM/klmm}
\bibliography{refs}

\end{document}
```

Do not force all sections. For a short proof, a theorem statement followed by a
well-structured proof may be better.

## Exposition Rules

- State the main theorem before technical details.
- Introduce notation before dense formulas.
- Keep hypotheses visible.
- State dependency lemmas and source-theorem inputs before their first
  load-bearing use.
- Separate intuition from formal proof.
- Merge routine lemmas into the proof only when the justification remains clear.
- Keep load-bearing estimates, constructions, case splits, and theorem
  preconditions explicit.
- Do not include Orchestrator or subagent history.
- Use `TODO` for missing citations rather than inventing references.
