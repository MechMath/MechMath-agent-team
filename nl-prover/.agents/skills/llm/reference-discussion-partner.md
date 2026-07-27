# discussion-partner — Discuss with Gemini/GPT

Free-form mathematical discussion for proof strategy, decomposition advice, or any mathematical question.

## CLI Invocation

```bash
uv run python cli_tools/external.py discuss QUESTION [--backend BACKEND] [--model MODEL] [--context FILE]
```

| Argument | Required | Default | Description |
|----------|----------|---------|-------------|
| `QUESTION` | yes | — | Question or prompt. Use `-` to read from stdin |
| `--backend` | no | `gemini` | LLM backend: `gemini` or `gpt` |
| `--model` | no | auto | Model override. Default: `gemini-2.5-pro` (gemini) or `gpt-5.5-pro` (gpt). Prefer the latest available Pro model when overriding. When `OPENROUTER_API_KEY` is set, these route through OpenRouter. |
| `--context` | no | — | Path to a file with additional context (prepended to the question) |

## Output

Plain text response from the LLM (not JSON).

## Examples

```bash
# Ask for a proof strategy
uv run python cli_tools/external.py discuss "How should I decompose the proof of the spectral theorem for compact self-adjoint operators?" --backend gemini

# Pipe a problem statement as context
uv run python cli_tools/external.py discuss - --backend gpt < workspace/proj/problem.md

# Use a context file to provide the full sketch
uv run python cli_tools/external.py discuss "Is this decomposition correct?" --context workspace/proj/sketch/decomposition.md --backend gemini

# Heredoc for multi-line questions with special characters
uv run python cli_tools/external.py discuss --backend gemini <<'EOF'
I need to prove: ∀ ε > 0, ∃ δ > 0, |x - a| < δ → |f(x) - f(a)| < ε
What's the cleanest approach for a Lipschitz function?
EOF
```

## Notes

- `OPENROUTER_API_KEY` is preferred when available and supports both backends through OpenRouter.
- `GEMINI_API_KEY` is used only if `OPENROUTER_API_KEY` is not set and `--backend gemini` is selected.
- `OPENAI_API_KEY` is used only if `OPENROUTER_API_KEY` is not set and `--backend gpt` is selected.
- Output is advisory only — it does not produce a verifiable proof.
- **For questions with special math symbols** (`∀`, `∃`, `⊢`, `→`), use `--context` or heredoc stdin to avoid shell escaping issues.
