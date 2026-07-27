# gpt-verify — Cross-Verify a Proof with GPT

Independently scores a proof using GPT-5.5 Pro with high reasoning effort. Returns a structured score (0, 0.5, or 1) and detailed analysis. Uses the same scoring rubric as gemini-verify.

Scoring rubric:
- **1** — Completely correct; all steps properly executed and demonstrated
- **0.5** — Generally correct but with minor omissions or errors
- **0** — Fatal errors, severe omissions, or does not prove the stated lemma

## CLI Invocation

```bash
uv run python cli_tools/external.py gpt PROOF_FILE [--problem FILE] [--lemma FILE] [--model MODEL] [--temperature FLOAT]
```

| Argument | Required | Default | Description |
|----------|----------|---------|-------------|
| `PROOF_FILE` | yes | — | Path to the proof file to verify |
| `--problem` | no | — | Path to the problem statement file |
| `--lemma` | no | — | Path to the lemma statement file |
| `--model` | no | `gpt-5.5-pro` | GPT model name. Prefer the latest available GPT Pro model when overriding. |
| `--temperature` | no | `0.3` | Sampling temperature |

## Output

JSON object:
```json
{
  "ok": true,
  "score": 0.5,
  "analysis": "Here is my evaluation of the proof: ..."
}
```

`score` is `-1` if the model response did not contain a `\boxed{...}` score.

## Examples

```bash
uv run python cli_tools/external.py gpt workspace/proj/lemmas/lem2/generator/proof_v1.md \
  --problem workspace/proj/problem.md \
  --lemma workspace/proj/lemmas/lem2/statement.md
```

## Notes

- `OPENROUTER_API_KEY` is preferred and will route GPT requests through OpenRouter.
- `OPENAI_API_KEY` must be set only if `OPENROUTER_API_KEY` is unavailable.
- Uses `reasoning={"effort": "high"}` internally for maximum accuracy.
