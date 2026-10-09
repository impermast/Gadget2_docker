#!/usr/bin/env bash
# Local skills sync for Cline: repo skills/ is the source of truth.
# Cline discovers project skills ONLY in workspace dirs:
#   .cline/skills/  .agents/skills/  .claude/skills/  .clinerules/skills/
# Plain top-level skills/ is NOT scanned. This script syncs each skill
# (skills/<name>/SKILL.md) into .cline/skills/<name>/ as a copy.
# Global dirs (~/.agents/skills, ~/.codex/skills) are NOT used anymore
# (project skills removed from them on 2026-10-09 — do not reinstall there).
set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SRC="$REPO_DIR/skills"
DEST="$REPO_DIR/.cline/skills"

mkdir -p "$DEST"
for skill_dir in "$SRC"/*/; do
  name="$(basename "$skill_dir")"
  [ -f "$skill_dir/SKILL.md" ] || continue
  /bin/rm -rf "$DEST/$name"
  cp -rL "$skill_dir" "$DEST/$name"
  echo "synced: $DEST/$name"
done

echo "Done. Cline discovers these skills in .cline/skills/ (reload Cline session to pick up changes)."
