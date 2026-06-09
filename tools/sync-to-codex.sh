#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Usage:
  tools/sync-to-codex.sh [--dry-run] [--codex-home PATH]

Sync the installable skill directory from this repository to the local Codex
skills directory.

Options:
  --dry-run          Show what would change without writing files.
  --codex-home PATH  Override CODEX_HOME. Defaults to $CODEX_HOME or ~/.codex.
EOF
}

dry_run=0
codex_home="${CODEX_HOME:-$HOME/.codex}"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --dry-run)
      dry_run=1
      shift
      ;;
    --codex-home)
      codex_home="$2"
      shift 2
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "Unknown argument: $1" >&2
      usage >&2
      exit 2
      ;;
  esac
done

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
repo_root="$(cd "$script_dir/.." && pwd)"
src="$repo_root/imagegen-pptx-pipeline/"
dst="$codex_home/skills/imagegen-pptx-pipeline/"

if [[ ! -f "$src/SKILL.md" ]]; then
  echo "Missing source SKILL.md: $src/SKILL.md" >&2
  exit 1
fi

mkdir -p "$(dirname "$dst")"

args=(
  -a
  --delete
  --exclude '__pycache__/'
  --exclude '*.pyc'
  --exclude '.DS_Store'
)

if [[ "$dry_run" -eq 1 ]]; then
  args+=(--dry-run --itemize-changes)
fi

rsync "${args[@]}" "$src" "$dst"

if [[ "$dry_run" -eq 1 ]]; then
  echo "Dry run complete. No files were changed."
else
  echo "Synced $src to $dst"
fi
