#!/usr/bin/env bash
# Launch the FL-Prover session runner with OpenRouter-backed specialist tooling.
# Requires OPENROUTER_API_KEY in the environment / .env.
python -m scripts.run_claude run projects/experiments/Example/Target.lean \
  --prompt-file prompts/orchestration.md \
  --result-dir projects/output \
  --max-rounds 5
