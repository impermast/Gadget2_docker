# LLM — AI-agent operational memory

This directory contains AI-agent operational memory and rules for the Gadget2_docker project.

## Structure

- `rules/` — project, safety, and workflow rules for each simulation code (GIZMO, GADGET-2, GalIC)
- `memory-bank/` — persistent project context: brief, patterns, tech context, progress, experiment log
- `../skills/` — reusable agent skills (`gizmo-sim`, `make-plots`) holding all operational protocols; these replaced the former `prompts/` and `workflows/` folders. Source of truth lives in the repo `skills/`; symlinks in `~/.codex/skills/` make them invocable.
