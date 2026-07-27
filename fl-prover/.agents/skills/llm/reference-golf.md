# code-golf — Simplify Lean Proof via Gemini

Uses Gemini to suggest a shorter or more elegant version of an existing Lean proof.

## CLI Invocation

```bash
python cli_tools/external.py golf LEAN_CODE [OPTIONS]
```

| Argument | Required | Default | Description |
|----------|----------|---------|-------------|
| `LEAN_CODE` | yes | — | Lean code to simplify. Use `-` to read from stdin |
| `--model` | no | `gemini-3.1-pro-preview` | Gemini model name |
| `--temperature` | no | 0.7 | Generation temperature |

## Examples

```bash
python cli_tools/external.py golf "theorem foo : 1 + 1 = 2 := by norm_num"
cat proof.lean | python cli_tools/external.py golf -
python cli_tools/external.py golf - --model gemini-2.5-pro < proof.lean
```

## Notes

- `GEMINI_API_KEY` is required.
- Only uses the Gemini backend; for GPT-based simplification use `discussion-partner` with a targeted prompt.
- Always verify the simplified output with `python cli_tools/lean.py check FILE` — the model may introduce subtle errors.
