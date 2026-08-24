# plot_scripts — новая plotting-инфраструктура

Компактный слой визуализации для R&D pipeline. Архитектура:

| Файл | Ответственность |
|------|-----------------|
| `settings.py` | ЕДИНЫЙ модуль стиля: COLORS/SIZES/STYLE/setup/apply/save (бывший plot_config.py) + `RunPaths` (пути run), `SimulationInfo` (метаданные симуляции), `PlotSettings` (глобальная визуальная политика, применяется через rcParams) |
| `base.py` | `BasePlot` (ABC), data contract (`FieldSpec`) + runtime validation |
| `plotter.py` | `NbodyPlotter` — оркестратор: registry, config-merge, validation, render; коллекции `ANALYSIS_PLOTS`, `ANIMATION_PLOTS`, `ALL_PLOTS` |
| `analysis_plots.py` | concrete plots: density, log_slope, sigma_v, interactions_radial |
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

Правила: plots не знают про HDF5/физику; данные готовят loaders;
output_dir передаётся интеграционным слоем; renderer сейчас только
"matplotlib", но API не зависит от backend.
