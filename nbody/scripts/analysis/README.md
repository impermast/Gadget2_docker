# analysis — единственный слой визуализации и анализа

Всё, что рисует графики (matplotlib/PIL) и вычисляет метрики для них, живёт ТОЛЬКО
здесь. Ad-hoc скрипты с `plt.savefig` в других каталогах запрещены — это
проверяется AST-guard-тестами (`tests/test_layout_guard.py`, маркер `guard`).

## Раскладка

| Модуль | Ответственность |
|--------|-----------------|
| `registry.py` | ЕДИНЫЙ реестр графиков: `@register`, `PlotSpec`, `validate_registry()`, `to_markdown()` → `nbody/analysis/REGISTRY.md` |
| `paths.py` | `AnalysisPaths` — правила размещения артефактов по блокам (ic/prerun/core/campaigns/presentations) + guard на сегменты пути |
| `plotter.py` | `NbodyPlotter` — оркестратор: config-merge, валидация данных, render; `UnknownPlotError`/`DuplicatePlotError` |
| `base.py` | `BasePlot` (ABC), data contract (`FieldSpec`/`F`, `validate_fields`), `PlotValidationError` |
| `style.py` | ЕДИНЫЙ стиль (`PlotSettings`, палитры, rcParams), `RunPaths` (пути прогона), `SimulationInfo`; узкая горловина `save_figure`/`savefig` |
| `loaders/` | HDF5 → plot-ready данные: `snapshots.py`, `profiles.py`, `particles.py` (математика перенесена дословно, golden-тесты) |
| `plots/` | concrete plots по блокам: `core.py`, `campaigns.py`, `animations.py` (+ `ic.py`, `prerun.py` — этап 3) |
| `runners/` | CLI: `make_run_plots.py`, `make_campaign_plots.py`, `make_campaign_morphology_plots.py`, `make_campaign_diag_plots.py`, `registry_docs.py` (+ `make_ic_plots.py`, `make_prerun_plots.py` — этап 3) |

## Главный вход для ИИ-агента — REGISTRY.md

Код читать не нужно: каталог графиков генерируется из реестра и лежит в
`nbody/analysis/REGISTRY.md` (в контейнере путь тот же). Для каждого plot там
есть `summary`, `data_source`, `inputs`, `runner`, `filename`, `config keys`.

```bash
# сгенерировать/обновить каталог:
docker exec gadget-gizmo python3 /nbody/scripts/analysis/runners/registry_docs.py
# проверить актуальность (CI/pre-commit):
docker exec gadget-gizmo python3 /nbody/scripts/analysis/runners/registry_docs.py --check
```

Инварианты реестра (падают тестом `tests/test_registry.py`):

- у каждого plot есть `name`, `block`, `summary`, `data_source`, `inputs`,
  непустой `default_config["filename"]`;
- имена уникальны, блок известен, файл `runner` существует;
- `REGISTRY.md` покрывает 100% имён.

## Куда попадают артефакты

Выход runner'ов определяется ТОЛЬКО `AnalysisPaths` (флага `--outdir` нет —
это guard-инвариант). Корень задаётся `NBODY_ANALYSIS_ROOT` (по умолчанию
`/nbody/analysis`):

```
nbody/analysis/
  REGISTRY.md                      # сгенерированный каталог графиков
  ic/<ic_name>/                    # блок ic:     target-профили, гейт разрешения каспа
  prerun/<run_name>/               # блок prerun: ранние снапшоты, гейт первых шагов
  core/<run_name>/                 # блок core:   один production-прогон
  campaigns/<campaign>[/<member>]/ # блок campaigns: сравнение группы
  presentations/<label>/           # блок presentations: фигуры под слайды
  previous_runs/                   # артефакты прежних прогонов (только чтение)
```

Примеры:

```bash
docker exec gadget-gizmo python3 /nbody/scripts/analysis/runners/make_run_plots.py \
    --run-root /nbody/runs/corecusp_cdm_N1e7_T5 --plots density,log_slope

docker exec gadget-gizmo python3 /nbody/scripts/analysis/runners/make_campaign_plots.py \
    /nbody/runs/corecusp_cdm_N1e7_T5 /nbody/runs/corecusp_sidm2_N1e7_T5 \
    --labels CDM SIDM_sigma2 --campaign corecusp --member compare_cdm_sidm2 --rcore 1.0
```

## Как добавить новый график

1. Класс-наследник `BasePlot` в `plots/<block>.py` c обязательными атрибутами
   `name`, `block`, `summary`, `data_source`, `inputs`, `default_config`
   (в нём — `filename`) и декоратором `@register`.
2. Данные для него готовит лоадер из `loaders/` (plots HDF5 не читают).
3. Тест: `tests/test_render_smoke.py` рисует каждый plot блока на синтетической
   фикстуре; для нового блока/plot'а добавьте данные в `_campaign_jobs`-подобный
   builder.
4. Перегенерируйте `REGISTRY.md`. Процедура этапов — `implementation_plan.md` §8.2.

## Тесты

```bash
.venv/bin/python -m pytest tests/ -q                     # всё
.venv/bin/python -m pytest tests/ -q -m 'guard or math'  # быстрый контур (pre-commit)
```