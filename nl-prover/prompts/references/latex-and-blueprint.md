# LaTeX and Blueprint

`proof.tex` is the authoritative proof document. It uses a lightweight
leanblueprint-style format with labels and dependency declarations.

Blueprint rules:

- Every theorem-like environment has a unique `\label{type:name}`.
- `\uses{}` in statements records what is needed to state the result.
- `\uses{}` in proofs records what is used to prove the result.
- No circular dependencies.
- Unverified results use `\sorry{}`.
- The proof is complete only when no `\sorry{}` remains.

Minimal skeleton:

```latex
\documentclass{article}
\usepackage[]{KLMM/klmm}
\usepackage{amsmath,amssymb,amsthm}

\newtheorem{theorem}{Theorem}
\newtheorem{lemma}[theorem]{Lemma}
\newcommand{\uses}[1]{\marginpar{\footnotesize\texttt{uses: #1}}}
\newcommand{\sorry}{\textbf{[SORRY -- proof pending]}}

\begin{document}
\section{Problem Statement}
<original problem>
\section{Main Results}
<verified theorem/lemma statements and proofs>
\end{document}
```


## Document template (KLMM)

When generating a PDF from `proof.tex`, `proof_summary.tex`, or a Writer output,
compile from the directory containing the `.tex` file.

The repository ships a house template at repo-root `tex/template.tex` and a
style directory at `tex/KLMM/` containing `klmm.sty` and `klmm.bst`. Every
reader-facing PDF must be built with this template family unless the user
explicitly supplies another venue or format.

Before compiling **any** `.tex` (`proof.tex`, `proof_summary.tex`, or Writer
output) to PDF:

1. Copy the repository's `tex/KLMM/` directory into the same directory as the
   `.tex` file, so that `KLMM/klmm.sty` and `KLMM/klmm.bst` are reachable from
   the `.tex` being compiled. For a `.tex` at `data/workspace/<problem_id>/`,
   that is:

   ```bash
   cp -R tex/KLMM data/workspace/<problem_id>/
   ```

   (adjust the source path so it points at the repo-root `tex/` directory).
2. For Writer outputs, use repo-root `tex/template.tex` as the structural
   starting point and replace its placeholder text with grounded mathematical
   prose. Do not `\input` the repo template from the generated file.
3. Make sure the document preamble loads the style with
   `\usepackage[]{KLMM/klmm}`.
4. If a bibliography is used, select the template's BibTeX style with
   `\bibliographystyle{KLMM/klmm}`.

When generating a PDF from `proof.tex` or `proof_summary.tex`, compile from the
directory containing the `.tex` file (which is where you just copied `KLMM/`).

With bibliography:

```bash
pdflatex proof.tex
bibtex proof
pdflatex proof.tex
pdflatex proof.tex
```

Without bibliography:

```bash
pdflatex proof.tex
pdflatex proof.tex
```

## Presentation and PDF export (SSOT)

This section is the single source for the presentation/PDF flow; `orchestration.md`
and `orchestrator-cookbook.md` point here. Presentation is a reader-facing layer,
never a mathematical stop condition — Writer outputs are mechanical exports, not
mathematical evidence, and a presentation failure never reopens a verified proof's
status (record it as pending in `writer/revision_notes.md` or `STATUS.md`).

Final article, after a verified proof (and after Refiner is accepted, rejected, or
skipped):

1. Dispatch Writer (`FULL_ARTICLE` or `COMPLETE_PROOF`); Writer owns
   `writer/article_candidate.tex`.
2. Generate the bibliography: `uv run python cli_tools/workspace.py refs-bib
   <workspace>` → `references/refs.bib`.
3. Run the citation audit (ADR 0019 §5): `uv run python cli_tools/gate.py
   citation-audit <workspace> --tex writer/article_candidate.tex` (the mechanical
   half) plus a fresh Verifier for the attribution/sign-off half. This gate blocks
   PDF acceptance but, like all presentation, does not change mathematical status.
4. Compile `writer/article_candidate.tex` from `writer/` (copy `KLMM/` first, per
   above) and copy the resulting PDF to the workspace root as
   `proof.pdf`.

Progress notes, required before any stop that is not a verified proof (blocked
route, verified obstruction, human-needed ambiguity, exhausted branch budget, or
a human-requested pause): compile `writer/progress_notes.tex` from `writer/` and
copy the resulting PDF to the workspace root as `progress_notes.pdf`. A progress
PDF must state that it is not a final proof or obstruction.

Note on names: `proof.pdf` is the Writer export, not a compilation product of the
authoritative `proof.tex`. Never compile `proof.tex` into the workspace root, or
it will overwrite the export.
