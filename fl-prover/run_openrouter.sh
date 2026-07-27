#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

openrouter_key="${OPENROUTER_API_KEY:-}"

if [ -z "$openrouter_key" ] && [ -f "$ROOT_DIR/.env" ]; then
  openrouter_key="$(
    sed -n -E \
      's/^[[:space:]]*(export[[:space:]]+)?OPENROUTER_API_KEY[[:space:]]*=[[:space:]]*(.*)$/\2/p' \
      "$ROOT_DIR/.env" |
      tail -n 1
  )"
  openrouter_key="${openrouter_key%\"}"
  openrouter_key="${openrouter_key#\"}"
  openrouter_key="${openrouter_key%\'}"
  openrouter_key="${openrouter_key#\'}"
fi

if [ -z "$openrouter_key" ] || [ "$openrouter_key" = "..." ]; then
  echo "ERROR: set OPENROUTER_API_KEY or provide it in fl-prover/.env." >&2
  exit 1
fi

# FL-Prover's external-LLM tools prefer OPENROUTER_API_KEY when it is present.
# The runner interface itself is identical to run.sh.
exec "$ROOT_DIR/run.sh" "$@"
