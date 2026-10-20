---
name: make-plots
description: Create, inspect, and extend scientific plots for GADGET/GIZMO runs through the canonical analysis layer in nbody/scripts/analysis/. Use whenever a user asks to visualize or compare simulation results, find available plots, interpret existing figures, change shared plot styling, or add a plot type. Never create one-off plotting scripts or duplicate visual outputs outside the registered workflow.
metadata:
  short-description: Canonical scientific visualization workflow
---

# make-plots — agent workflow router

## Project contract

- All simulation analysis and rendering go through `nbody/scripts/analysis/`: registry, loaders, plot classes, runners, and `AnalysisPaths`. Do not build parallel plotting paths or read HDF5/snapshot arrays directly.
- `nbody/analysis/REGISTRY.md` is the generated catalog of supported plots and their runner/input/config metadata. Read it when choosing a plot; never maintain a second list here.
- Shared visual policy belongs in `nbody/scripts/analysis/style.py` (`PlotSettings`, `STYLE`, `COLORS`, `SIZES`), not copied into individual plots. Plot-specific defaults are for semantics/layout that cannot reasonably be shared.
- Use only the workflow needed for the current task. Load that workflow before acting:

| Agent task | Read |
|---|---|
| List or verify available plots/registry | `workflows/registry.md` |
| Render registered plots | `workflows/build.md` |
| Inspect or interpret existing figures/results | `workflows/inspect.md` |
| Change project-wide appearance/theme | `workflows/style.md` |
| Add a new plot type | `workflows/add-plot.md` |

These are agent work routes, not a requirement to ask the user to select a mode. Infer the route from intent; if a request mixes routes, do the minimum needed and do not render as a side effect of catalog/design discussion.

## Always-on invariants

- Communicate in Russian. Follow repository bootstrap and safety rules in `AGENTS.md` and `llm/PROJECT.md`; preserve dirty user changes.
- Do not create ad-hoc Matplotlib scripts, alternate plot directories, timestamped copies, or duplicate plot implementations. Use canonical runners and deterministic `AnalysisPaths` destinations.
- Do not alter scientific calculations, data transformations, centering, units, binning, or interpretation as a visual-style task. Such changes require a separately scoped scientific-method task.
- Do not open large snapshots/HDF5 for orientation. Loaders own snapshot access.
- Existing files are not disposable: before rendering, inspect expected output paths. If the canonical outputs already exist, do not silently overwrite them or create a second directory to avoid the collision. Report the collision and ask whether to reuse/inspect or regenerate the canonical files.
- Never invent a plot or runner based on memory. Resolve current names, runners and configuration from `REGISTRY.md` and verify exact CLI against the runner when needed.

## Completion report

For actions taken, report in Russian: selected workflow, inputs, exact command or files changed, canonical output paths, overwritten/skipped files, warnings, and validation performed. For read-only catalog/inspection tasks, say explicitly that nothing was generated or changed.
