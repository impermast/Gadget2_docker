# LLM — AI-agent operational memory

This directory contains AI-agent operational memory and rules for the Gadget2_docker project.

## Structure

- `rules/` — project, safety, and workflow rules for each simulation code (GIZMO, GADGET-2, GalIC)
- `memory-bank/` — persistent project context: brief, patterns, tech context, progress, experiment log
- `../.cline/skills/` — reusable agent skills (`gizmo-sim`, `make-plots`, `check-run`) holding all operational protocols; these replaced the former `prompts/` and `workflows/` folders. Tracked directly in `.cline/skills/` (migrated from top-level `skills/` on 2026-10-09; Cline scans only workspace dirs `.cline/skills`, `.agents/skills`, `.claude/skills`, `.clinerules/skills`; no global install).
