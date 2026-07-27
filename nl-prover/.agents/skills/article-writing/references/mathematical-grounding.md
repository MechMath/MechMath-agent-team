# Mathematical Grounding

Every substantive mathematical claim in Writer output must be grounded.
Writer does not prove, verify, repair, or infer missing mathematics.

## Accepted Sources

A claim may be used when it comes from:

- accepted `proof.tex`;
- accepted `proof_summary.tex`;
- accepted Verifier packet;
- source-theorem package with recorded statement and preconditions;
- target contract or accepted definition/notation reading;
- human instruction;
- a route artifact explicitly marked as progress/restart state, only for a
  progress note.

## Citation Policy (ADR 0019)

Inputs: the provenance ledger `references/ledger.jsonl` and the generated
`references/refs.bib` (from `workspace.py refs-bib`, real BibTeX — no TODO).

- **Cite at the first load-bearing use, once.** Use natbib KLMM `\citet{key}` /
  `\citep{key}` at the first point where an external result supports a step. Do
  not re-cite it at every later mention, and do not pile citations at the end.
- **Attribute existing results (#5).** A ledger row with `trust:
  cite-as-existing` is written as an attributed theorem
  (`\begin{theorem}[{\citet{key}}]…`), never as an original contribution. A
  theorem whose statement matches a ledger `original theorem` row but carries no
  citation is a failure the final `gate.py citation-audit` will catch.
- **Load-bearing citations come only from the ledger** (audited:
  `cite-as-existing`, or a discharged `borrowed`). Do not fabricate a
  load-bearing citation.
- **Related-work / background citations may be added freely** (not limited to the
  ledger), because they support no proof step and need no trust audit — but they
  must be real references with resolvable BibTeX and must not quietly become
  load-bearing. The audit governs *support*, not *mention*.
- Every `\cite` key must resolve in `references/refs.bib`. If metadata is
  missing, surface it to the Orchestrator; never leave a `TODO` in the prose.
- Do not convert a source-search failure into a mathematical claim.
- Do not cite internal agent files in the main body as if they were literature.
  If useful, put short evidence notes at the end.

## Stop Conditions For Writer

Stop and write a handoff when drafting would require:

- changing a theorem statement or hypotheses;
- adding or deleting a proof case;
- supplying a missing construction, estimate, or theorem precondition;
- deciding whether a route is valid;
- deciding whether an obstruction is genuine;
- replacing a citation with an unaudited theorem;
- changing accepted notation or definitions.

## Grounding Review Checklist

Before finishing, check:

- theorem statements are preserved;
- hypotheses are preserved;
- proof logic is preserved;
- every major claim has a source;
- every `\cite` key resolves in `references/refs.bib` (no `TODO` placeholders);
- every `cite-as-existing` ledger result is cited at its first use, and no
  ledger `original theorem` is presented as the article's own;
- progress/restart state is labeled as such;
- no internal path list substitutes for mathematical explanation.
