# LLM — AI-agent operational memory

This directory contains AI-agent operational memory and rules for the Gadget2_docker project.

## Structure

- `rules/` — project, safety, and workflow rules for each simulation code (GIZMO, GADGET-2, GalIC)
- `memory-bank/` — persistent project context: brief, patterns, tech context, progress, experiment log
- `../skills/` — reusable agent skills (`gizmo-sim`, `make-plots`, `check-run`) holding all operational protocols; these replaced the former `prompts/` and `workflows/` folders. Skills are LOCAL to this repo (no global install; project copies were removed from `~/.codex/skills/` and `~/.agents/skills/` on 2026-10-09).
