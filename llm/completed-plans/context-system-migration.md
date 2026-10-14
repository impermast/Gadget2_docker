# Completed plan — agent context and memory migration

Status: completed in this working tree; architecture is operational in `AGENTS.md`, `llm/PROJECT.md`, `PLAN.md`, `ACTIVE.md`, and `MEMORY.md`. The detailed architecture proposal and obsolete competing rulebook/state were removed after reconciliation. Historical approvals do not transfer.

- Added `llm/records/` with important scientific reports and IC/run manifests; added a mandatory default-no-record gate in AGENTS and PROJECT.
- Historical completed matched IC campaign retained at `rotating-ic-matched-campaign.md`, explicitly non-operative; unrelated run artifacts remain in `nbody/`.
- Updated Cline entrypoint, `.agents/skills/`, `.cline/skills/`, runner comment, Git ignore policy, and Pi session-dir setting.
- Pi project session storage is configured to `llm/sessions/`. The current `PI_CODING_AGENT_SESSION_DIR` override was verified as `/home/kds/progs/harness/agent/sessions`; this running session and its transcript were not moved. The chosen launcher must unset/override it for a new project-local session.
- Scientific runs, datasets, commits, pushes, and package installation were not part of this migration.
