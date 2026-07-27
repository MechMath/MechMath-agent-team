# gemini-verify — Cross-Verify a Proof with Gemini

Independently scores a proof using Gemini. Returns a structured score (0, 0.5, or 1) and detailed analysis.

Scoring rubric:
- **1** — Completely correct; all steps properly executed and demonstrated
- **0.5** — Generally correct but with minor omissions or errors
- **0** — Fatal errors, severe omissions, or does not prove the stated lemma

> Citing an external result without providing its justification does **not** make a step valid.

## CLI Invocation

```bash
uv run python cli_tools/external.py gemini PROOF_FILE [--problem FILE] [--lemma FILE] [--model MODEL] [--temperature FLOAT]
```

| Argument | Required | Default | Description |
|----------|----------|---------|-------------|
| `PROOF_FILE` | yes | — | Path to the proof file to verify |
| `--problem` | no | — | Path to the problem statement file |
| `--lemma` | no | — | Path to the lemma statement file |
| `--model` | no | `gemini-2.5-pro` | Gemini model name |
| `--temperature` | no | `0.3` | Sampling temperature |

## Output

JSON object:
```json
{
  "ok": true,
  "score": 1.0,
  "analysis": "Here is my evaluation of the proof: ..."
}
```

`score` is `-1` if the model response did not contain a `\boxed{...}` score.

## Examples

```bash
uv run python cli_tools/external.py gemini workspace/proj/lemmas/lem1/generator/proof_v2.md \
  --problem workspace/proj/problem.md \
  --lemma workspace/proj/lemmas/lem1/statement.md
```

## Notes

- `OPENROUTER_API_KEY` is preferred and will route Gemini requests through OpenRouter.
- `GEMINI_API_KEY` must be set only if `OPENROUTER_API_KEY` is unavailable.
- External scores are evidence for the detailed Verifier, not merge authority.
  Merge still requires a passing detailed review packet and the repository
  acceptance gate. A score of 0 is strong evidence that the proof should be
  revised or rerouted.
