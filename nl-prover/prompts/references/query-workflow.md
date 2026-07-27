# Query Workflow

All research and knowledge-base queries use the problem-local `queries/`
directory. Sketcher and Generator agents describe what they need; the
Orchestrator owns routing, execution, and status updates.

`queries/<query_id>/request.md`:

```markdown
# Query Request

## Requested By
Sketcher | Generator:<lemma_id> | Orchestrator

## Query ID
<stable_id>

## Question
<natural-language question>

## Purpose
analysis-preflight | decomposition | lemma-proof | stuck-debugging | theorem-lookup | background

## Sources Requested
kb-manager | matlas | arxiv | all

## Context Files
- <path>

## Search Terms
- <term>

## Desired Output
precise statement | proof strategy | references | counterexamples | previous failures | proof hygiene | related results

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

- `kb-manager.md`: written by a fresh KB-Manager subagent.
- `matlas.md`: normalized summary from `search.py matlas`.
- `arxiv.md`: normalized summary from `search.py arxiv`.

Index outputs:

- `index.json` and `index.md`: mechanical summaries from
  `search.py index summarize`.
- The Orchestrator runs
  `uv run python cli_tools/search.py index refresh <workspace>`
  whenever query outputs exist, as part of the required per-cycle index refresh
  (see `AGENTS.md` Routing preconditions), to summarize existing query outputs
  and append source findings to `memory/source_findings.jsonl`.
- Use
  `uv run python cli_tools/search.py index latest <workspace> --source matlas --limit 5`
  when an agent needs the latest query outcomes without scanning all of
  `queries/`.

Source-selection rules:

- Use `kb-manager` for local wiki background, reusable proven notes, and
  analysis preflight.
- Use `matlas` for precise theorem statements and published statement anchors.
- Use `arxiv` for recent or preprint literature.
- Use `all` only when the route genuinely needs local memory, theorem lookup,
  and literature survey.

Analysis preflight results must propagate into `sketch/decomposition.md`,
affected `lemmas/<lemma_id>/statement.md`, and Verifier risk audits. Checklist
items are known-risk prompts, not proof facts.
