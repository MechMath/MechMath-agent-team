# state-search — Search by Proof Goal

Searches theorems relevant to a given proof state/goal using premise-search.com.

## CLI Invocation

```bash
python cli_tools/lean.py search state GOAL [-n NUM_RESULTS]
```

| Argument | Required | Default | Description |
|----------|----------|---------|-------------|
| `GOAL` | yes | — | Proof state / goal text (paste the goal as-is) |
| `-n, --num-results` | no | 5 | Maximum number of results |

## Examples

```bash
python cli_tools/lean.py search state "⊢ n + 0 = n"
python cli_tools/lean.py search state "⊢ Nat.Prime p → p ∣ a * b → p ∣ a ∨ p ∣ b" -n 10
```

## Notes

- Paste the proof goal exactly as shown in the Lean infoview — including `⊢` and hypotheses if relevant.
- Environment variable: `LEAN_STATE_SEARCH_URL` overrides the default endpoint (`https://premise-search.com`).
