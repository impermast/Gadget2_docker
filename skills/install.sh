#!/usr/bin/env bash
# Install repo skills into the agent discovery roots.
# Source of truth: this repository (skills/). Run this script after any skill edit.
set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DESTS=(
  "${CODEX_HOME:-$HOME/.codex}/skills"
  "$HOME/.agents/skills"
)

for dest in "${DESTS[@]}"; do
  mkdir -p "$dest"
  for skill_dir in "$REPO_DIR"/*/; do
    name="$(basename "$skill_dir")"
    target="$dest/$name"
    # Never install hidden/utility dirs that are not skills
    [ -f "$skill_dir/SKILL.md" ] || continue
    /bin/rm -rf "$target"
    cp -rL "$skill_dir" "$target"
    echo "installed: $target"
  done
done

echo "Done. Skills are available on the next agent turn."
