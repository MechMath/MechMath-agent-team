# Progress Summary — worked example

This is what `writer/progress_summary.tex` looks like when it passes
`gate summary`. It is a shape to copy, not content to reuse; the mathematics
below is invented.

The gate checks structure, budget, vocabulary and honesty — it cannot check
whether the summary is *true*. That part is still yours.

Compile it from `writer/` and copy the PDF to the workspace root as
`progress_summary.pdf`, exactly as `progress_notes.tex` is handled. **The PDF is
the deliverable**; `gate stop` requires both it and the source.

---

```latex
\documentclass[11pt,a4paper]{article}
\usepackage[margin=1in]{geometry}
\usepackage{amsmath,amssymb,url}
\usepackage{parskip}
\providecommand{\path}[1]{\texttt{#1}}
\title{Connes embedding for the cloning overgroup family}
\date{}

\begin{document}
\maketitle

\section{The statement}

Let $G_k$ be the cloning overgroup of the free group $F_k$, $k\ge2$, and let
$\Lambda(G_k)$ be its group von Neumann algebra. The claim under consideration
is that $\Lambda(G_k)$ embeds into an ultrapower of the hyperfinite
$\mathrm{II}_1$ factor for every $k\ge2$. Throughout, a \emph{fold move} is the
elementary Nielsen move on a presentation that identifies two generators.

\section{Where this stands}

Open. Two of its three reductions are proved and the third is blocked on a
finite computation nobody has run. Nothing found so far suggests the statement
is false.

\section{What is blocked}

Whether the vertical Fox derivative detector is well defined on the order-$103$
global list. Every route to the main statement now passes through it, and it
needs an explicit check on a single finite presentation --- not a new idea.

\section{What is established}

\begin{itemize}
  \item \textbf{Statement.} For every $k\ge2$ the expansion map factors as
        $\varepsilon_k=\pi_k\circ\iota_k$, with $\iota_k$ injective and $\pi_k$
        trace-preserving.
        \textbf{Sketch.} Both maps are built from the fold move, which acts on
        the presentation two generators at a time; injectivity is the rank
        computation on the resulting $2\times2$ blocks, and trace preservation
        holds because the move is measure-preserving on each block.
        \path{lemmas/cloning_fold_restart_2/cf2_expansion_factorization/}
  \item \textbf{Statement.} Every resolvent of Hodge type admits a unique
        mixed-root normal form $\sum_i a_i\,\rho_i$ with
        $a_i\in\mathbb{Z}[\zeta]$.
        \textbf{Sketch.} Existence is the division algorithm in the mixed-root
        basis; uniqueness follows from linear independence of the $\rho_i$ over
        $\mathbb{Q}(\zeta)$, which is the discriminant computation in Section~3.
        \path{lemmas/hodge_mixed_root_restart_1/hmr2_mixed_root_normal_form/}
\end{itemize}

\section{What was ruled out}

\begin{itemize}
  \item Deriving the detector from the twisted coset funnel: the injectivity it
        needs fails already at the edge map, and no weakening of the hypotheses
        recovers it.
  \item The greedy allocation route, which gives a bound weaker than the one
        the statement needs by a factor growing in the presentation length.
\end{itemize}

\section{What to do next}

\begin{enumerate}
  \item Run the finite check on the order-$103$ list; it is a day of computation.
  \item If it fails, the fold factorisation still gives a conditional statement
        worth writing up on its own.
\end{enumerate}

\section{Terms coined here}

\begin{itemize}
  \item \emph{vertical Fox derivative detector} --- the map sending a relator to
        the vector of its Fox derivatives evaluated along the vertical subgroup.
  \item \emph{fold family} --- the presentations obtained by iterating the fold
        move from the base presentation.
\end{itemize}

\end{document}
```

---

## What makes it pass

- **68 body lines, two pages.** The caps are 300 body lines, 32 KB and 10 pages.
  *Body* means everything after `\begin{document}`, so a longer preamble is not
  a shorter document. The restart document that accompanies it has no cap and
  must not acquire one.
- **It is LaTeX, like the note.** Not because the note is — because the summary
  is the document a person opens, and the format follows the reader. What
  separates the two is the cap and the section order, never the typesetting.
- **It states the problem before reporting on it.** `\section{The statement}`
  comes first and gives the claim, the notation and the standing conventions.
  The first real summary written under this spec never stated its problem at
  all: the title said "Sumset-Complement Claim for Eight Forms Modulo 24", the
  lead said it was open, and a reader still could not say what the eight forms
  were. A status is about something, and the document a person opens is the
  worst possible place to assume they already know what.
- **The blocker is the third section**, at body line 17. The reader came for it.
  In the corpus measured before this gate existed, it sat past 85% of the file
  in 7 notes of 11 — a consequence of the section order, not of the writing.
  The rule is absolute (first 40 body lines) *or* proportionate (first 40%),
  either one; a correct short summary must not be refused for its shape.
- **Each established result is a statement, a sketch, and a path** — labelled
  `\textbf{Statement.}` and `\textbf{Sketch.}`, with the path in `\path{...}`,
  and all three are required. The statement is the mathematics: what was
  proved, in symbols, standing on its own. The sketch is why it is true in two
  or three sentences — the mechanism, not the proof. The path is where the
  proof actually lives.

  The rule this replaces read *"one line each, plus the path"*. It was written
  against a note that was 97% pasted internal packets, and it overshot: the
  first summary produced under it listed thirteen results as thirteen noun
  phrases and thirteen paths, so a two-page document about mathematics
  contained none. "The polynomial factorisation for all eight forms" is a label
  for a theorem, not a theorem.

  The markup matters: the gate exempts a marked-up path from its vocabulary
  scan — `restart_2` is harness machinery in prose — and it cannot exempt a
  path written bare.
- **Every coined term is defined.** Runs mint vocabulary constantly and define
  it nowhere. If there is genuinely nothing to define, write the empty-state
  line — never an empty section.
- **No numbers about distance.** Not "80% done", not "two more runs". Distance
  to a proof is qualitative; a number there is a guess wearing a measurement as
  a costume.
- **No process.** No specialist names, no verdict tokens, no counts of anything
  the harness did, no wall-clock. A path to a proof is the one exception, and it
  belongs in `\path{}`.
- **No verbatim environment**, of any kind — `verbatim`, `lstlisting`, `minted`,
  `alltt`. A paste is refused outright rather than judged on its contents:
  restating is the whole job, and anything genuinely unrestatable belongs in the
  note, cited by path from here.

## What is a warning rather than a refusal

Words that are both machinery here and ordinary mathematics — `row`, `owner`,
`ledger`, `slot`, `record`, `accepted`, `audit`, `packet`, `generator` — are not
banned. One use of any of them is silent. A dozen raises a warning, because at
that density they have stopped being mathematics: the worst note in the corpus
carries them at **0.49 per line against a median of 0.04**, and has section
headings like "Nested-Forest Scale Hierarchy Ledger" and a `\begin{lemma}` whose
statement is built entirely from scheduling nouns.

Read the warning and decide. It is a question, not a verdict.

The same applies to a short sketch. Some results genuinely have a four-word
one — "a finite range checked by machine" is complete and correct — so a length
minimum there would be a lint the run learns to route around. The gate counts
short sketches and asks; it does not refuse them.
