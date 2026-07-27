# Query Workflow

Literature and knowledge-base queries use the problem-local `queries/` directory.
A specialist describes what it needs; the Orchestrator owns routing, execution,
and status updates.

This is **not** Lean premise retrieval. Looking for a Mathlib lemma is
`cli_tools/lean.py search <engine>` (the `lean-search` skill) and needs no query
directory. This workflow is for *human* sources: which paper states the theorem,
what its exact hypotheses are, what the knowledge base already recorded.

`queries/<query_id>/request.md`:

```markdown
# Query Request

## Requested By
Blueprinter | Formalizer | F-Reviewer | Orchestrator

## Query ID
<stable_id>

## Question
<natural-language question>

## Purpose
source-statement | definition-check | background | prior-formalization | stuck-debugging

## Sources Requested
kb-manager | matlas | arxiv | all

## Context Files
- <path>

## Search Terms
- <term>

## Desired Output
precise statement | proof strategy | references | previous failures | related results

## Priority
required | useful | optional
```

`queries/<query_id>/status.md`:

```markdown
# Query Status

## Status
requested | running | complete | failed | skipped

## Sources
| Source | Status | Output |
|--------|--------|--------|
| kb-manager | requested | kb-manager.md |
| matlas | requested | matlas.md |
| arxiv | requested | arxiv.md |

## Notes
<execution notes or failure details>
```

Source outputs:

- `kb-manager.md`: KB tier read via `memory.py read --tier kb`.
- `matlas.md`: normalized summary from `search.py matlas`.
- `arxiv.md`: normalized summary from `search.py arxiv`.

Index outputs:

- `index.json` and `index.md`: mechanical summaries from
  `search.py index summarize`.
- The Orchestrator runs
  `uv run python cli_tools/search.py index refresh <workspace>`
  whenever query outputs exist, as part of the per-cycle index refresh, to
  summarize existing outputs and append source findings to
  `memory/source_findings.jsonl`.
- Use
  `uv run python cli_tools/search.py index latest <workspace> --source matlas --limit 5`
  when an agent needs the latest query outcomes without scanning all of
  `queries/`.

Source-selection rules:

- `kb-manager` — local knowledge base: reusable proved results, past
  formalization notes, recorded traps.
- `matlas` — precise theorem statements and published statement anchors.
- `arxiv` — recent or preprint literature.
- `all` — only when the blocker genuinely needs local memory, theorem lookup, and
  a literature survey at once.

A query result is context, not evidence. A source statement found this way still
has to be formalized, reviewed for fidelity, and proved before anything reaches
the master development.
