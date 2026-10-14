# ACTIVE — checkpoint

Checkpoint: `migration-1-commit`

PLAN revision: `migration-1-commit`

Updated: implementation checkpoint (live simulation status not checked)

## Current task

The user-requested `llm/` transition commit has been created. Migration `P-001` is complete; no simulations, Docker rebuilds, installs, or push were part of this task.

## Verified progress

- Architecture implemented; important-only records policy accepted.
- This Pi conversation explicitly loaded `AGENTS.md` and all four canonical memory files; use them as the working project memory in this ongoing session.
- Initial source audit found latest active science triplet in old `activeContext.md`/`progress.md`; see P-003.
- Conference RUN_STATE (2026-10-12) records three accepted matched k08 T=5 M5 rows; retry2 D0.50 T=5 has 52 points but is not integrated into package ledgers. Earlier D0.50 attempt is incomplete; package is `science_partial`, user rehearsal pending. Verify current package before resuming.
- Repo is dirty with user work in `nbody/`, `.agents/`, `.pi/`, and untracked IC/reports. Preserve all unrelated changes. Do not infer live runs/disk from historical notes.

## Unresolved / resume checks

- Confirm active campaign/rehearsal state from conference package and user’s current priority before altering its detailed work artifacts.
- Historical resources/process status is stale; check live only before simulation/run operations.
- `.pi/settings.json` retains package config and sets project sessionDir. Current environment overrides it with `/home/kds/progs/harness/agent/sessions`; do not move the live transcript blindly. Use explicit CLI/harness configuration for a new project-local session and verify runtime `PI_SESSION_FILE`.
- Skills and Cline adapter now reference the new memory architecture; `git diff --check` and final reference/status review remain.

## Next safe action

Verify the transition commit scope/hash, then ask whether P-002 conference package or a P-003 science line is current priority before substantive work. Keep non-llm migration support changes and all pre-existing user changes outside this commit untouched.
