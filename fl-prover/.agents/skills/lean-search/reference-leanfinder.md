# leanfinder — Mathlib Semantic Search

Searches Mathlib theorems/definitions semantically by mathematical concept or proof state.

## CLI Invocation

```bash
python cli_tools/lean.py search leanfinder QUERY [-n NUM_RESULTS]
```

| Argument | Required | Default | Description |
|----------|----------|---------|-------------|
| `QUERY` | yes | — | Mathematical concept, proof state, or statement definition |
| `-n, --num-results` | no | 5 | Maximum number of results |

## Examples

```bash
python cli_tools/lean.py search leanfinder "sum of squares is non-negative"
python cli_tools/lean.py search leanfinder "injectivity of composition"
python cli_tools/lean.py search leanfinder "⊢ Finset.sum s f ≤ Finset.sum s g" -n 8
```

## Notes

- Best for: natural language math statements, proof states, statement fragments.
- Multiple targeted queries beat one complex query.
- For exact pattern matching, prefer `loogle`. For identifier search, prefer `leandex`.
