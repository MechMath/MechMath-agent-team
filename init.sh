#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TIMESTAMP="$(date +%Y%m%d-%H%M%S)"
PROJECT_DIR_NAME="$(basename "$ROOT_DIR")"
INITIALIZATION_MARKER=".mmat-initialized"

die() {
  echo "ERROR: $*" >&2
  exit 1
}

command_exists() {
  command -v "$1" >/dev/null 2>&1
}

normalize_project_name() {
  local name="$1"

  printf '%s\n' "$name" |
    tr '[:upper:]' '[:lower:]' |
    sed -E 's/[^a-z0-9]+/-/g; s/^-+//; s/-+$//'
}

update_pyproject_name() {
  local normalized_name

  [ -f "$ROOT_DIR/pyproject.toml" ] || return 0

  normalized_name="$(normalize_project_name "$PROJECT_DIR_NAME")"
  [ -n "$normalized_name" ] || normalized_name="mmat-project"

  sed -i -E "s/^name = \".*\"/name = \"$normalized_name\"/" \
    "$ROOT_DIR/pyproject.toml"
}

rename_project_root() {
  local requested_name="$1"
  local parent_dir
  local current_name
  local target_name
  local target_dir

  if [ -z "$requested_name" ]; then
    PROJECT_DIR_NAME="$(basename "$ROOT_DIR")"
    return 0
  fi

  case "$requested_name" in
    */*|.|..)
      die "Project name must be a directory name, not a path: $requested_name"
      ;;
  esac

  parent_dir="$(dirname "$ROOT_DIR")"
  current_name="$(basename "$ROOT_DIR")"
  target_name="$requested_name"
  target_dir="$parent_dir/$target_name"

  if [ "$target_name" = "$current_name" ]; then
    PROJECT_DIR_NAME="$target_name"
    return 0
  fi

  if [ -e "$target_dir" ]; then
    target_name="$requested_name-$TIMESTAMP"
    target_dir="$parent_dir/$target_name"
    echo "A sibling named '$requested_name' already exists."
    echo "Using project name: $target_name"
  fi

  while [ -e "$target_dir" ]; do
    target_name="$requested_name-$TIMESTAMP-$RANDOM"
    target_dir="$parent_dir/$target_name"
  done

  mv "$ROOT_DIR" "$target_dir"
  ROOT_DIR="$(cd "$target_dir" && pwd)"
  PROJECT_DIR_NAME="$target_name"
  echo "Project directory renamed to: $ROOT_DIR"
}

initialize_data_layout() {
  mkdir -p \
    "$ROOT_DIR/data/inbox" \
    "$ROOT_DIR/data/lean" \
    "$ROOT_DIR/data/logs" \
    "$ROOT_DIR/data/raw_sources" \
    "$ROOT_DIR/data/wiki" \
    "$ROOT_DIR/data/workspace"

  touch \
    "$ROOT_DIR/data/download_queue.md" \
    "$ROOT_DIR/data/sources_manifest.md" \
    "$ROOT_DIR/data/wiki/index.md" \
    "$ROOT_DIR/data/wiki/log.md"
}

command_exists git || die "git is required."

cd "$ROOT_DIR"

[ ! -e "$ROOT_DIR/$INITIALIZATION_MARKER" ] ||
  die "This project has already been detached from the MMAT template."

echo "Initialize a new MMAT-based research project"
echo
echo "This permanently detaches the copied project from the template repository."
echo "It will:"
echo "  - optionally rename the project directory;"
echo "  - update the root pyproject.toml project name;"
echo "  - permanently remove the current root Git metadata and history;"
echo "  - initialize a new Git repository on branch main;"
echo "  - create the shared data directory layout;"
echo "  - stage the initial project files without committing them."
echo
echo "The fl-prover, nl-prover, and kb-manager directories are ordinary project"
echo "directories in this repository; no submodules are created or retained."
echo
echo "WARNING: the existing .git metadata will not be backed up."
echo "Type INIT to continue, or anything else to exit."
read -r -p "> " confirmation

if [ "$confirmation" != "INIT" ]; then
  echo "Canceled."
  exit 0
fi

echo
echo "Enter a project name, or press Enter to keep: $PROJECT_DIR_NAME"
echo "If that name already exists beside this directory, a timestamp is appended."
read -r -p "Project name: " project_name

rename_project_root "$project_name"
update_pyproject_name

# Removing only the exact metadata entry at the project root prevents an
# enclosing repository from being affected when this directory came from a ZIP
# archive or a plain filesystem copy.
if [ -e "$ROOT_DIR/.git" ]; then
  rm -rf -- "$ROOT_DIR/.git"
fi

if ! git -C "$ROOT_DIR" init -b main >/dev/null 2>&1; then
  git -C "$ROOT_DIR" init >/dev/null
  git -C "$ROOT_DIR" checkout -B main >/dev/null
fi

initialize_data_layout
printf '%s\n' \
  "This repository has been detached from the MMAT project template." \
  > "$ROOT_DIR/$INITIALIZATION_MARKER"
git -C "$ROOT_DIR" add --all

echo
echo "New project initialized at:"
echo "  $ROOT_DIR"
echo
echo "The template Git history has been permanently removed."
echo
echo "Next steps:"
if command_exists uv; then
  echo "  1. Install or refresh dependencies: uv sync --all-packages"
else
  echo "  1. Install uv, then run: uv sync --all-packages"
fi
echo "  2. Review staged files: git status"
echo "  3. Create the first commit: git commit -m \"Initial project\""
echo "  4. Add your repository: git remote add origin <your-repo-url>"
echo "  5. Push it: git push -u origin main"
