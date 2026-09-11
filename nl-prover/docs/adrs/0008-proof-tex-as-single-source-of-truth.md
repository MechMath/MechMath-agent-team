# ADR 0008: proof.tex as Single Source of Truth

## Status
Accepted

## Context

In a multi-agent system where proofs are generated, verified, and revised across many files, there must be a single authoritative document that represents "the proof" at any point in time. Without this, it's unclear which version of which lemma is canonical, and the final assembly becomes error-prone.

The Archon project uses `PROGRESS.md` as the single source of truth for proof state. The Prover project uses `BLUEPRINT.md`. Both follow the pattern of a single, centrally maintained document that all agents reference.

For NL-Prover, the deliverable is a LaTeX document — the proof itself. Making the deliverable the single source of truth (rather than a separate tracking document) ensures there is never drift between "what we think is proved" and "what the document says."

## Decision

### `proof.tex` is the Canonical Proof Document

- **Only the Orchestrator** may write to `proof.tex`
- `proof.tex` reflects the current best-known state of the proof
- A lemma appears in `proof.tex` **only after** it has been verified (Verifier PASS)
- Lemmas appear in dependency order
- The document is always valid LaTeX. PDFs are built with
  `pdflatex`, `bibtex`, `pdflatex`, `pdflatex` when bibliography data is
  present; without bibliography data, build with two `pdflatex` passes and skip
  `bibtex`.

### Merge Protocol

When a lemma is verified:

1. Orchestrator reads the verified `generator/proof_v<N>.md`
2. Orchestrator translates the proof into LaTeX format
3. Orchestrator inserts the lemma and proof into `proof.tex` at the correct position (respecting dependency order)
4. Orchestrator updates `STATUS.md` to reflect the merge

### What `proof.tex` Contains at Each Phase

| Phase | Contents |
|-------|----------|
| After setup | Preamble, problem statement, empty sections |
| During proving | Verified lemmas with proofs, `sorry`-marked placeholders for unverified lemmas |
| After completion | Complete proof document, no placeholders |

### `sorry` Convention for Unverified Lemmas

Unverified lemmas that have been decomposed by the Sketcher appear as:

```latex
\begin{lemma}[lem:3 — Monotonicity of $f$]\label{lem:3}
$f$ is monotonically increasing on $[0, 1]$.
\end{lemma}
\begin{proof}
\textbf{[SORRY — proof pending]}
\end{proof}
```

This ensures the document always compiles and gives a clear picture of what remains.

### Relationship to STATUS.md

`STATUS.md` tracks operational state (attempts, verdicts, agent assignments). `proof.tex` tracks mathematical content. They must be consistent:

- If `STATUS.md` says lem:X is `verified` → `proof.tex` must contain lem:X's proof
- If `STATUS.md` says lem:X is `in_progress` → `proof.tex` has a SORRY placeholder for lem:X
- The Orchestrator maintains both and ensures consistency

## Consequences

### Pros
- **No drift** — the deliverable IS the source of truth, not a copy of it
- **Always compilable** — valid LaTeX at every stage makes progress visible (PDF can be generated anytime with the repository LaTeX build policy)
- **Clear completion criteria** — the proof is done when `proof.tex` has no SORRY markers
- **Human-readable** — anyone can read the LaTeX and understand the current proof state

### Cons
- **Merge complexity** — the Orchestrator must translate Markdown proofs to LaTeX and insert them at the right position
- **LaTeX dependency** — agents must understand LaTeX conventions (mitigated: only the Orchestrator writes LaTeX; generators write Markdown)
- **Potential merge conflicts** — if re-decomposition changes lemma structure, the Orchestrator must carefully update `proof.tex` (mitigated: SORRY placeholders make insertion points clear)
