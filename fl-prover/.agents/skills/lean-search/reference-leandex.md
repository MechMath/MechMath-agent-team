# leandex — Semantic Search

Searches Lean theorems/definitions using natural language, Lean terms, concept names, or identifiers. This is the recommended first-choice search tool.

> **Limit**: Do NOT run more than 5 leandex queries in parallel. Issue them one at a time or in small batches (≤5).

## CLI Invocation

```bash
python cli_tools/lean.py search leandex QUERY [-n NUM_RESULTS]
```

| Argument | Required | Default | Description |
|----------|----------|---------|-------------|
| `QUERY` | yes | — | Search query: natural language, Lean terms, concept names, identifiers |
| `-n, --num-results` | no | 5 | Maximum number of results to return |

## Examples

```bash
python cli_tools/lean.py search leandex "Cauchy Schwarz inequality"
python cli_tools/lean.py search leandex "List.sum" -n 10
python cli_tools/lean.py search leandex "{f : A → B} (hf : Injective f) : ∃ h, Bijective h"
```

## Notes

- Works best when you phrase the query as a mathematical concept, a Lean identifier, or a partial type signature.
- For proof-state-style queries, prefer `state-search` or `hammer-premise` instead.
- **Limit**: Do NOT run more than 5 leandex queries in parallel.
