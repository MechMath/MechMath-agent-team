#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if [ "$#" -eq 0 ]; then
  echo "Usage:"
  echo "  ./run.sh run <target> --prompt-file <file> [options]"
  echo "  ./run.sh batch <config-file> [options]"
  echo "  ./run.sh from-folder <folder> --prompt-file <file> [options]"
  exit 2
fi

command -v uv >/dev/null 2>&1 || {
  echo "ERROR: uv is required." >&2
  exit 1
}

cd "$ROOT_DIR"
exec uv run python -m scripts.run_claude "$@"
