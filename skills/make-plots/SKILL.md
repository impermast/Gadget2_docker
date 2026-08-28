---
name: make-plots
description: Create plots and animations from an existing simulation run using the project plotting infrastructure nbody/scripts/plot_scripts/ (NbodyPlotter registry, data contracts, loaders). Standard analysis plots (density, log_slope, sigma_v, interactions_radial) and animations (particles_2d, particles_3d). Use when the user asks to plot, visualize, animate, or analyze snapshots of a completed run. Not for launching simulations.
metadata:
  short-description: Plot and analyze finished simulation runs
---

# Visualization Pipeline (plot_scripts)

All standard plotting goes through `nbody/scripts/plot_scripts/`.
Read `nbody/scripts/plot_scripts/README.md` before extending it.

## Preamble (always do first)

Read `.clinerules/00-entrypoint.md`, then every file in `llm/rules/` and
`llm/memory-bank/`. Communicate with the user in Russian.

## Architecture in one paragraph

`PlotSettings` (global visual policy) + `RunPaths`/`SimulationInfo` (run data)
live in `settings.py`. `BasePlot` (`base.py`) is the single ABC: every concrete
plot has `name`, `description`, `data_contract` (runtime-validated),
`default_config`, `render()`. `NbodyPlotter` (`plotter.py`) only orchestrates:
registry, config deep-merge, validation, render. `loaders.py` prepares
plot-ready data from HDF5 snapshots (math copied verbatim from the legacy
analysis scripts). Plots never read HDF5 and never compute physics.

## Registry (standard plots)

| name | class | data source | output |
|------|-------|-------------|--------|
| `density` | DensityPlot | 1 snapshot, `PartType3/Coordinates+Masses`, shrinkage center | `01_density_profile.png` |
| `log_slope` | LogSlopePlot | same, slope window 0.25 dex | `02_log_slope.png` |
| `sigma_v` | SigmaVPlot | same, `PartType3/Velocities` | `03_sigma_v.png` |
| `interactions_radial` | InteractionsRadialPlot | same, `PartType3/NInteractions` | `04_ninteractions_radial.png` |
| `density_compare` | DensityComparePlot | несколько прогонов (series) | `density_compare.png` |
| `log_slope_compare` | LogSlopeComparePlot | несколько прогонов (series) | `log_slope_compare.png` |
| `sigma_v_compare` | SigmaVComparePlot | несколько прогонов (series) | `sigma_v_compare.png` |
| `log_rho_compare` | LogRhoComparePlot | несколько прогонов; верх + Δ(log ρ) vs CDM в нижнем сабплоте | `log_rho_compare.png` |
| `rot_curve_compare` | RotCurveComparePlot | v_circ(r) (M(<r)) несколько прогонов; верх + Δv vs CDM внизу | `rot_curve_compare.png` |
| `core_density_vs_sigma` | CoreDensityVsSigmaPlot | σ и ρ_core по прогонам | `core_density_vs_sigma.png` |
| `particles_2d` | Particles2DAnimation | snapshot series, hist2d xy | `evolution_2d.gif` |
| `particles_3d` | Particles3DAnimation | snapshot series, 3D scatter | `evolution_3d.gif` |

Collections: `ANALYSIS_PLOTS`, `ANIMATION_PLOTS`, `ALL_PLOTS` (in `plotter.py`).

## Protocol

1. Identify the run directory (default `nbody/runs/<run_name>/`).
2. List snapshot files by names/sizes only; never open binary contents yourself — loaders do it.
3. Run inside the container (`docker exec gadget-gizmo ...`).
4. Introspect first: `plotter.available_plots()` and `plotter.describe(name)`
   give the exact data contract and default config of each plot.
5. Prepare data:
   - analysis plots: `loaders.prepare_profile_data(snapshot, rcore=...)` — one dict feeds all four analysis plots;
   - animations: `loaders.prepare_series(run.output, nmax=..., max_frames=...)`.
6. Render and verify outputs (existence, non-zero size, GIF frame count).
7. Outputs go directly to `nbody/runs/<run_name>/plots/` (no nested folders);
   comparative analyses to `nbody/analyse/<topic>/`.
8. Update `llm/memory-bank/experimentLog.md` (Type: visualization).

## One-shot full pipeline (preferred default)

```bash
docker exec gadget-gizmo python3 /nbody/scripts/plot_scripts/run_full_test.py \
    --run-root /nbody/runs/<run_name> \
    [--frames 12] [--nmax 80000] [--outdir /nbody/runs/<run_name>/plots]
```

It runs introspection, negative validation smoke-tests, all 6 plots and
output verification. Use it as the standard post-run visualization step.

## Python usage examples

```python
import sys; sys.path.insert(0, "/nbody/scripts/plot_scripts")
from settings import PlotSettings, RunPaths, SimulationInfo
from plotter import create_plotter, ANALYSIS_PLOTS
from loaders import prepare_profile_data, prepare_series

run = RunPaths("/nbody/runs/<run_name>")
plotter = create_plotter(PlotSettings(), output_dir=run.plots)

print(plotter.available_plots())     # what plots exist
print(plotter.describe("density"))   # data contract + default config

info = SimulationInfo.from_snapshot(run.latest_snapshot())

# analysis batch: one prepared dict feeds all four plots
prof = prepare_profile_data(run.latest_snapshot(), rcore=2.0)
plotter.make_plots({n: {"data": prof} for n in ANALYSIS_PLOTS},
                   output_dir=run.plots)

# single plot with individual overrides (defaults are not mutated)
plotter.make_plot("density", prof,
                  config={"ylim": (1e-6, 1e-1), "filename": "density_zoom.png"})

# animations
series = prepare_series(run.output, nmax=80_000, max_frames=12)
plotter.make_plots({
    "particles_2d": {"data": series,
                     "config": {"sigma_label": info.cross_section}},
    "particles_3d": {"data": series,
                     "config": {"label": f"{info.model} sigma={info.cross_section:g}"}},
}, output_dir=run.plots)
```

## Adding a new plot

1. Create `MyPlot(BasePlot)` in `analysis_plots.py` (or `animation_plots.py`).
2. Fill `name`, `description` (data provenance for humans and AI),
   `data_contract` (FieldSpec shapes — enforced at runtime),
   `default_config` (including `filename`), implement `render()`.
3. Add the class to `ANALYSIS_PLOT_CLASSES` / `ANIMATION_PLOT_CLASSES`.
4. Check `plotter.describe("my_plot")`, test on real data; extend
   `run_full_test.py` if it becomes a standard plot.
Do not write standalone plotting scripts — extend the registry.

## Legacy / non-standard diagnostics

Все legacy analysis/plotting скрипты удалены и заменены `plot_scripts/`:
`analyze_final_snapshot.py` (сводка -> `loaders.write_summary()`, вызывается в
`run_full_test.py`), `analyze_halo.py` и `compare_all.py` (multi-run сравнение
-> `compare_runs.py` + compare-plots в registry), `png_to_gif.py`,
`make_run_evolution.py`, `make_3d_animation.py`, `example_snap*.py`, `ytvis.py`,
`field_maker.py`, `plot_config.py` (поглощён `settings.py`).
Остались только run-wrappers и IC-инструменты (`run_sim.sh`, `generate_ics.sh`,
`merge_ics.py`, `convert_to_pt3.py`, `check_snapshot.py`, `run_sidm_batch.sh`,
`run_sidm20.sh`) и `plot_scripts/`.

Multi-run comparison (замена compare_all.py):

```bash
docker exec gadget-gizmo python3 /nbody/scripts/plot_scripts/compare_runs.py \
    --outdir /nbody/analyse/cdm_sidm_all --rcore 50 \
    /nbody/runs/cdm_N1e6 /nbody/runs/sidm_sigma0.1_N1e6 \
    /nbody/runs/sidm_sigma1_N1e6 /nbody/runs/sidm_sigma2_N1e6 \
    /nbody/runs/sidm_sigma5_N1e6
```

Строит density_compare, log_slope_compare, sigma_v_compare и
core_density_vs_sigma (если >=2 SIDM-прогонов).

## Rules

- Prefer the registry; never duplicate plot code in standalone scripts.
- Never mutate `default_config` or the user config dict; overrides are merged by the plotter.
- Do not change physical methodology in loaders/plots (centering, binning,
  formulas) — that is a separate, explicit task.
- Do not overwrite existing plots unless explicitly requested.
- Errors must name the plot and the field; if a validation message is
  unclear, fix the message, not the test.

## Produce (in Russian)

1. plot names used;
2. input run directory;
3. output plot directory;
4. exact command(s);
5. generated files with sizes;
6. warnings or failures.

