# plot_scripts — новая plotting-инфраструктура

Компактный слой визуализации для R&D pipeline. Архитектура:

| Файл | Ответственность |
|------|-----------------|
| `settings.py` | ЕДИНЫЙ модуль стиля: COLORS/SIZES/STYLE/setup/apply/save (бывший plot_config.py) + `RunPaths` (пути run), `SimulationInfo` (метаданные симуляции), `PlotSettings` (глобальная визуальная политика, применяется через rcParams) |
| `base.py` | `BasePlot` (ABC), data contract (`FieldSpec`) + runtime validation |
| `plotter.py` | `NbodyPlotter` — оркестратор: registry, config-merge, validation, render; коллекции `ANALYSIS_PLOTS`, `ANIMATION_PLOTS`, `ALL_PLOTS` |
| `analysis_plots.py` | concrete plots: density, log_slope, sigma_v, interactions_radial, disk_edgeon; compare/presentation plots для групповых diagnostics |
| `animation_plots.py` | concrete plots: particles_2d, particles_3d (GIF через PIL) |
| `loaders.py` | HDF5 -> plot-ready данные (математика перенесена дословно из старых скриптов) |
| `run_full_test.py` | integration/test runner |

## Быстрый старт

```python
import sys; sys.path.insert(0, "/nbody/scripts/plot_scripts")
from plotter import create_plotter, ANALYSIS_PLOTS
from settings import PlotSettings, RunPaths
from loaders import prepare_profile_data

run = RunPaths("/nbody/runs/sidm20_dwarf_N1e6_T5")
plotter = create_plotter(PlotSettings(), output_dir=run.plots)
print(plotter.available_plots())          # какие графики существуют
print(plotter.describe("density"))        # какие данные нужны каждому
data = prepare_profile_data(run.latest_snapshot())
plotter.make_plot("density", data)
```

Полный прогон всех plots + validation-тесты:

```bash
docker exec gadget-gizmo python3 /nbody/scripts/plot_scripts/run_full_test.py \
    --run-root /nbody/runs/sidm20_dwarf_N1e6_T5
```

## Презентационный visual morphology пакет

Для CDM/SIDM/dSIDM групп есть отдельный тонкий runner поверх registry:

```bash
docker exec gadget-gizmo python3 /nbody/scripts/plot_scripts/compare_visual_morphology.py \
    --group-root /nbody/runs/test_dissipation_focused_T5 \
    --outdir /nbody/runs/test_dissipation_focused_T5/visual_compare \
    --lim 12 --bins 220 --phase-bins 180
```

Он читает только доступные snapshot'ы через `loaders.py` и graceful-skip'ает
недоступные/ещё не стартовавшие runs, поэтому пригоден для запуска во время
расчёта. Outputs:

- `01_surface_density_montage_final.png` — face-on/edge-on montage;
- `02_surface_density_residual_vs_cdm_final.png` — residual maps vs baseline;
- `03_shape_radial_profiles_final.png` — b/a, c/a, thickness, rotation support;
- `04_phase_space_R_vphi_final.png` — R-vphi phase-space panels;
- `05_disk_dashboard.png` — compact disk-candidate dashboard;
- `06_log_rho_compare_final.png`, `07_rot_curve_compare_final.png` — стандартные delta-compare plots;
- `visual_summary.txt` — краткая сводка и warnings.

## Диагностические (presentation) DIAG-графики

Дополнительные диагностические графики регистрируются в коллекции `DIAG_PLOTS`
и рендерятся тонким runner'ом `make_campaign_diagnostics.py`:

```bash
docker exec gadget-gizmo python3 /nbody/scripts/plot_scripts/make_campaign_diagnostics.py \
    --group-root /nbody/runs/dsidm_spin_k08_transition \
    --eloss-runs dsidm_s2p5_D0p10_N1e5_T2 dsidm_s2p5_D0p25_N1e5_T2 dsidm_s2p5_D0p50_N1e5_T2 \
    --eloss-baseline sidm_s2p5_N1e5_T2 \
    --criteria-runs dsidm_s2p5_D0p10_N1e5_T2 dsidm_s2p5_D0p25_N1e5_T2 dsidm_s2p5_D0p50_N1e5_T2 \
    --runaway-runs dsidm_s2p5_D0p75_N1e5_T2
```

Три новых графика:

- `diag_eloss_vs_f` — по X заданная диссипация `f` (`DM_DissipationFactor`), по Y
  измеренная относительная потеря кинетической энергии рассеявшихся частиц
  `ΔE/E`; points + линия y=x; пунктиром теоретическая кривая `ΔE/E = 2D - D^2`.
  Данные: `interacted_kinetic_energy()` (kinetic energy подмножества частиц с
  `NInteractions > 0`), baseline — elastic SIDM run (`D=0`) той же sigma.
- `criteria_time_panel` — эволюция `c/a`, `z_rms/R_rms`, `|Vrot|/sigma` по времени
  для набора кандидатов, с порогами `0.75 / 0.55 / 0.15`. Данные: metrics-series
  CSV от `check_simulations/analyze_series.py`.
- `runaway_timestep_panel` — двух-осевой график `N_interactions(t)` (лев. ось) и
  `min dt(t)` (прав. ось, лог) — связь runaway с коллапсом шага времени.

Правила: plots не знают про HDF5/физику; данные готовят loaders;
output_dir передаётся интеграционным слоем; renderer сейчас только
"matplotlib", но API не зависит от backend.
