---
name: article-writing
description: "Use when NL-Prover needs reader-facing mathematical exposition: a final proof PDF after verified proof completion, a full LaTeX article candidate, a local proof/article rewrite candidate, or the mandatory progress notes written before any stop without a verified proof. Trigger on proof.pdf, progress_notes.pdf, article_candidate.tex, local_revision_candidate.tex, progress_notes.tex, writing for proof.tex adoption, style_profile.md, reader-facing research-note/paper prose, or avoiding agent-run history in mathematical text."
---

# Article-Writing Skill

Use this skill inside the Writer agent. It is not a proof-search workflow.
Writer turns verified or explicitly state-marked material into reader-facing
LaTeX prose without changing the mathematics.

## Load Only What You Need

| Need | Reference |
|------|-----------|
| Create or reuse the writing style profile | [style-profile.md](references/style-profile.md) |
| Ground mathematical claims and citations | [mathematical-grounding.md](references/mathematical-grounding.md) |
| Rewrite a local passage | [local-revision.md](references/local-revision.md) |
| Explain unfinished/restartable state (mandatory before any non-proof stop) | [progress-note.md](references/progress-note.md) |
| Build a full research-note/paper or complete-proof candidate | [latex-research-note-template.md](references/latex-research-note-template.md) |

For full article or complete-proof candidates, read `style-profile.md`,
`mathematical-grounding.md`, and `latex-research-note-template.md`.

For local rewrites, read `style-profile.md`, `mathematical-grounding.md`, and
`local-revision.md`.

For progress notes, read `mathematical-grounding.md` and `progress-note.md`;
read `style-profile.md` only if the note must match an existing document.

## Core Rules

- Write only under the assigned `writer/` directory.
- Prefer `.tex` for reader-facing output.
- For full article and progress-note outputs, write standalone LaTeX files that
  can be compiled directly from `writer/`.
- For `COMPLETE_PROOF`, `FULL_ARTICLE`, and `PROGRESS_NOTES` outputs, when the
  user supplies no template, venue, or format, default to the repository house
  KLMM template: read repo-root `tex/template.tex` and use it as the structural
  starting point. Keep the package and bibliography paths compatible with a
  sibling `KLMM/` directory: `\usepackage[]{KLMM/klmm}` and, if a bibliography is
  present, `\bibliographystyle{KLMM/klmm}`. The Orchestrator copies `tex/KLMM/`
  next to the `.tex` before compiling. Local rewrites instead match the
  surrounding document. Only depart from the KLMM template when the user
  explicitly provides another template or venue.
- Default to English research-note/paper style unless the user explicitly asks
  for another article language or venue.
- Do not write agent scheduling history in reader-facing prose.
- Do not invent citations. Cite from the provenance ledger via
  `references/refs.bib`; every `\cite` key must resolve there. No `TODO`
  placeholders — surface missing metadata to the Orchestrator (ADR 0019; see
  `references/mathematical-grounding.md`).
- Do not present restartable state, missing source theorems, failed tools, or
  open blockers as final mathematical results.
- Complete-proof outputs are used after proof completion or explicit human
  request. Progress notes cover unfinished state, and are required before any
  stop that is not a verified proof — not only when the human asks.
- Progress notes must begin with the precise mathematical statement, scope,
  hypotheses, and notation, then carry the five required sections in order:
  routes explored; verified results **with their complete proofs written out**;
  failed explorations with the reason each failed; possible next paths including
  the atomic blocker; and a short summary of the collected literature. See
  `references/progress-note.md`.
- If a requested edit changes mathematical content, stop and write a handoff
  for the Orchestrator.

## Standard Outputs

- Full article or complete proof: `writer/article_candidate.tex`
- Local rewrite: `writer/local_revision_candidate.tex`
- Progress notes: `writer/progress_notes.tex`
- Style profile: `writer/style_profile.md`
- Optional plan: `writer/article_plan.md`
- Audit/handoff notes: `writer/revision_notes.md`
