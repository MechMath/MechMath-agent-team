#!/usr/bin/env bash
# Launch the FL-Prover Claude Code session runner over a Lean target.
# Adjust the target file / prompt / workspace for your project.
python -m scripts.run_claude run projects/experiments/Example/Target.lean \
  --prompt-file prompts/orchestration.md \
  --result-dir projects/output \
  --max-rounds 5
