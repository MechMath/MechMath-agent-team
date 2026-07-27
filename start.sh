#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DATA_DIR="$ROOT_DIR/data"
export DATA_DIR

die() {
  echo "ERROR: $*" >&2
  exit 1
}

require_directory() {
  [ -d "$1" ] || die "Missing directory: $1 (run ./init.sh first)"
}

require_command() {
  command -v "$1" >/dev/null 2>&1 ||
    die "Required command not found: $1"
}

print_menu() {
  echo "MMAT launcher"
  echo "Shared data directory:"
  echo "  DATA_DIR=$DATA_DIR"
  echo
  echo "Select a session:"
  echo "  1) KBManager via Codex"
  echo "  2) NL-Prover via Codex"
  echo "  3) FL-Prover via Codex"
  echo "  4) NL-Prover via Claude Code"
  echo "  5) FL-Prover via Claude Code"
  echo "  6) Help"
  echo "  Any other input exits."
  echo
}

print_help() {
  echo
  echo "KBManager maintains the persistent wiki, source registry, download queue,"
  echo "raw-source archive, and Lean archive. Its Codex session can write throughout"
  echo "the shared data directory."
  echo
  echo "NL-Prover coordinates natural-language proof workflows. FL-Prover"
  echo "coordinates Lean 4 formalization and proof workflows. Their sessions receive"
  echo "write access only to data/workspace and data/inbox; other shared data remains"
  echo "read-only unless you approve a broader operation."
  echo
  echo "NL-Prover and FL-Prover both provide Codex and Claude Code harnesses over"
  echo "the same prompts, deterministic tools, and shared skills."
  echo
  echo "Arguments passed to ./start.sh are forwarded to the selected CLI."
  echo "Exit the active CLI, then run ./start.sh again to switch components."
  echo
}

launch_codex() {
  local agent_dir="$1"
  local access_scope="$2"
  shift 2

  require_command codex
  require_directory "$agent_dir"

  if [ "$access_scope" = "all-data" ]; then
    echo "Starting Codex in $agent_dir"
    exec codex -C "$agent_dir" --add-dir "$DATA_DIR" "$@"
  fi

  echo "Starting Codex in $agent_dir"
  exec codex -C "$agent_dir" \
    --add-dir "$DATA_DIR/workspace" \
    --add-dir "$DATA_DIR/inbox" \
    "$@"
}

launch_claude() {
  local agent_dir="$1"
  shift

  require_command claude
  require_directory "$agent_dir"

  # `--version` catches incomplete installations where a wrapper exists but
  # the platform-specific Claude Code binary is missing.
  claude --version >/dev/null 2>&1 ||
    die "Claude Code is present but is not runnable; repair its installation."

  cd "$agent_dir"
  echo "Starting Claude Code in $agent_dir"
  exec claude \
    --add-dir "$DATA_DIR/workspace" \
    --add-dir "$DATA_DIR/inbox" \
    "$@"
}

require_directory "$DATA_DIR"
require_directory "$DATA_DIR/workspace"
require_directory "$DATA_DIR/inbox"

while true; do
  print_menu
  read -r -p "Enter choice [1-6]: " choice

  case "$choice" in
    1)
      launch_codex "$ROOT_DIR/kb-manager" "all-data" "$@"
      ;;
    2)
      launch_codex "$ROOT_DIR/nl-prover" "workspace-only" "$@"
      ;;
    3)
      launch_codex "$ROOT_DIR/fl-prover" "workspace-only" "$@"
      ;;
    4)
      launch_claude "$ROOT_DIR/nl-prover" "$@"
      ;;
    5)
      launch_claude "$ROOT_DIR/fl-prover" "$@"
      ;;
    6)
      print_help
      read -r -p "Press Enter to return to the menu."
      ;;
    *)
      echo "Exiting without starting a session."
      exit 0
      ;;
  esac
done
