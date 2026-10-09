#!/usr/bin/env bash
# Local skill check: repo skills/ is the source of truth.
# Skills are LOCAL to this repository (skills/<name>/SKILL.md).
# This script only verifies structure; it does NOT copy anything to global
# directories. Project skills were removed from ~/.agents/skills and
# ~/.codex/skills on 2026-10-09 — do not reinstall them there.
set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

fail=0
for skill_dir in "$REPO_DIR"/*/; do
  name="$(basename "$skill_dir")"
  if [ -f "$skill_dir/SKILL.md" ]; then
    echo "ok: $name ($skill_dir/SKILL.md)"
  fi
done

echo "Done. Skills are local to this repo; no global install performed."
