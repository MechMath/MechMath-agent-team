# leansearch — Natural Language + Lean Term Search

Searches Lean theorems using natural language descriptions or Lean terms.

## CLI Invocation

```bash
python cli_tools/lean.py search leansearch QUERY [-n NUM_RESULTS]
```

| Argument | Required | Default | Description |
|----------|----------|---------|-------------|
| `QUERY` | yes | — | Natural language description or Lean terms |
| `-n, --num-results` | no | 5 | Maximum number of results |

## Examples

```bash
python cli_tools/lean.py search leansearch "commutativity of addition for natural numbers"
python cli_tools/lean.py search leansearch "List.map preserves length" -n 8
python cli_tools/lean.py search leansearch "Nat.add_comm"
```

## Notes

- Accepts both plain English and Lean identifier/term queries.
- Complements `leandex` and `leanfinder`; use multiple search tools in parallel when unsure which lemma name to look for.
