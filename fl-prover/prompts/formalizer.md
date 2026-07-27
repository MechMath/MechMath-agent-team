# Formalizer Prompt

Formalize a source theorem into a Lean statement skeleton.

Follow `.agents/skills/formalize/reference-formalizer.md`, especially: audit the
source definitions first, acid-test Mathlib types with the search tools before
adopting them, choose the declaration kind (`def` / `structure` / `theorem`) by
what the source does, and prefer bundled Mathlib structures over long inline
pinning.

Rules:

- preserve source meaning;
- use local definitions and book notation where appropriate;
- leave proof as `sorry`;
- record source paths and deviations;
- run `uv run python cli_tools/lean.py check FILE` if possible;
- request formalization review.

Revising an already-approved statement is legal only on an F-Reviewer rejection,
and the revision needs a fresh `VERDICT: APPROVE` plus a new guard snapshot before
any proof work resumes
(`.agents/skills/orchestration/references/statement-guard.md`).
