#!/usr/bin/env bash
# Wrapper around `lean.py check` for shells whose Lean toolchain env is broken
# (a stale ELAN_HOME, or a PATH without a working `lake`).
#
# Usage: cli_tools/leancheck.sh <FILE.lean> [lean.py check flags...]
#   e.g. cli_tools/leancheck.sh path/to/File.lean --compact
#
# Set LEAN_ELAN_HOME in .env (or the environment) if elan does not live in
# ~/.elan on this machine.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

if [[ -f "$REPO_ROOT/.env" ]]; then
  # shellcheck disable=SC1091
  set -a; source "$REPO_ROOT/.env"; set +a
fi

export ELAN_HOME="${LEAN_ELAN_HOME:-${ELAN_HOME:-$HOME/.elan}}"
export PATH="$ELAN_HOME/bin:$PATH"

exec uv run --project "$REPO_ROOT" python "$REPO_ROOT/cli_tools/lean.py" check "$@"
