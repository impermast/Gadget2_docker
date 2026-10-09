---
name: make-plots
description: Create plots and animations for simulation runs through the single analysis layer nbody/scripts/analysis/ (registry as the source of truth, AnalysisPaths output tree, runners CLI, loaders). Blocks ic/prerun/core/campaigns/presentations; standard plots (density, log_slope, sigma_v, interactions_radial, disk_edgeon, particles_2d/3d) and group comparisons. Use when the user asks to plot, visualize, animate, or analyze snapshots of a run or a run group. Not for launching simulations.
metadata:
  short-description: Plot and analyze finished simulation runs
---

# Visualization pipeline (`nbody/scripts/analysis/`)

Единственный слой рисования: и код, и runners живут в
`nbody/scripts/analysis/`. Standalone-скрипты с matplotlib запрещены
(AST-guard: `tests/test_layout_guard.py`, маркер `guard`).

## Preamble (always do first)

Read `.clinerules/00-entrypoint.md`, then every file in `llm/rules/` and
`llm/memory-bank/`. Communicate with the user in Russian.

## Актуальный каталог графиков — из реестра, не из этого skill

При каждом запросе на анализ/визуализацию сначала открой
`nbody/analysis/REGISTRY.md` (в контейнере `/nbody/analysis/REGISTRY.md`). Это
сгенерированный актуальный каталог; не полагайся на имена графиков или CLI,
запомненные из этого skill, памяти или прежних запусков. Код plot'ов для обычного
выбора читать не нужно. Для каждого графика реестр даёт `summary`, `data_source`,
`inputs`, `runner`, `filename` и `config keys`.

Чтобы показать пользователю перечень, сгруппируй записи реестра по блокам и
перескажи имена + краткие `summary` + runner. Не переписывай каталог вручную в
skill: изменение реестра должно отражаться в следующем чтении REGISTRY.md.

Если файла нет или он явно не совпадает с нужным блоком, не угадывай список:
сгенерируй/выведи его из реестра через `registry_docs.py --print` (без
перезаписи каталога). В контейнере:

```bash
docker exec gadget-gizmo python3 /nbody/scripts/analysis/runners/registry_docs.py --print
```

Локально, когда контейнер недоступен, разрешён эквивалентный read-only вывод:

```bash
NBODY_ANALYSIS_ROOT=/tmp/nbody-analysis \
  python3 nbody/scripts/analysis/runners/registry_docs.py --print
```

`--check` проверяет сохранённый generated-файл, но не является командой для
показа каталога. Не запускай генератор без `--print`, если задача не просит
обновить REGISTRY.md: обычный запрос каталога должен быть read-only.

Актуализация/проверка каталога (сам файл руками не правим):

```bash
docker exec gadget-gizmo python3 /nbody/scripts/analysis/runners/registry_docs.py
docker exec gadget-gizmo python3 /nbody/scripts/analysis/runners/registry_docs.py --check
```

## Блоки и куда падают артефакты

Выход вычисляет ТОЛЬКО `AnalysisPaths` (`analysis/paths.py`); CLI-флага
`--outdir` нет — это guard-инвариант. Корень: `NBODY_ANALYSIS_ROOT`
(по умолчанию `/nbody/analysis`).

| блок | что это | путь | runner |
|------|---------|------|--------|
| `ic` | начальные условия: target-профиль, гейт разрешения каспа | `analysis/ic/<ic_name>/` | `make_ic_plots.py` |
| `prerun` | ранние снапшоты: гейт первых шагов, серия | `analysis/prerun/<run>/` | `make_prerun_plots.py` |
| `core` | один production-прогон | `analysis/core/<run>/` | `make_run_plots.py` |
| `campaigns` | сравнение группы прогонов | `analysis/campaigns/<campaign>[/<member>]/` | см. ниже (3 runner'а) |
| `presentations` | архив презентационных исходников и готовых экспортов | `analysis/presentations/<label>/` | отдельный runner не используется |

Текущий реестр сообщает `presentations (0)`: это намеренно, так как презентация
собирается из уже существующих графиков и подготовленных assets, а не отдельным
runner'ом. Для новых графиков презентации используй зарегистрированные plots
соответствующих блоков и перенаправление не меняй.

## Runners (готовый CLI)

```bash
# core: профили, карты, анимации одного прогона
#  -> analysis/core/<run>/{01_density_profile.png,...}
docker exec gadget-gizmo python3 /nbody/scripts/analysis/runners/make_run_plots.py \\
    --run-root /nbody/runs/<run> [--plots density,log_slope] [--frames 12] [--nmax 80000]

# campaigns: сравнение профилей группы (density/log_slope/sigma_v/log_rho/rot_curve compare)
#  -> analysis/campaigns/<campaign>/<member>/
docker exec gadget-gizmo python3 /nbody/scripts/analysis/runners/make_campaign_plots.py \\
    /nbody/runs/<run-a> /nbody/runs/<run-b> \\
    --labels CDM SIDM_sigma2 --campaign <campaign> --member compare_2runs --rcore 2.0

# campaigns: морфология группы (montage, residuals, radial profiles, R-vphi, dashboard)
docker exec gadget-gizmo python3 \\
    /nbody/scripts/analysis/runners/make_campaign_morphology_plots.py \\
    --group-root /nbody/runs/<group> --campaign <campaign> [--runs a b] [--nmax 300000]

# campaigns: DIAG-панели (dE/E vs D, criteria-time, runaway timestep)
docker exec gadget-gizmo python3 \\
    /nbody/scripts/analysis/runners/make_campaign_diag_plots.py \\
    --group-root /nbody/runs/<group> --campaign <campaign> \\
    --eloss-runs a b --eloss-baseline <elastic-run> \\
    --criteria-runs a b --runaway-runs <run>
```

Позиционные run-каталоги указывать ДО `--labels` (`nargs='*'` съедает всё после).

## Protocol

1. Определи предмет: один прогон (`--run-root`) или группа (campaign + member).
2. Прочитай актуальный `nbody/analysis/REGISTRY.md`; выбери записи по смыслу и
   входу, затем используй runner и config keys именно из записи.
3. Запусти соответствующий runner в контейнере (`docker exec gadget-gizmo`).
   Никаких собственных скриптов и никакого `--outdir`.
4. Проверь результат: файлы в `analysis/<block>/...`, ненулевой размер, для GIF —
   число кадров > 1 (runner'ы печатают `[OK]`-проверки).
5. Отчитайся по-русски: графики, вход, каталог вывода, точная команда, файлы и
   размеры, warnings/skips.

Данные готовят только лоадеры (`analysis/loaders/`):
`prepare_profile_data`, `prepare_particle_snapshot`, `prepare_series`,
`prepare_visual_snapshot`, `projection_histograms`, `phase_space_histogram`,
`radial_morphology_profiles`, `load_metrics_series`, `interacted_kinetic_energy`.
Plots HDF5 не читают и физику не считают.

## Adding a new plot

1. Класс-наследник `BasePlot` в `analysis/plots/<block>.py` с декоратором
   `@register` и обязательными атрибутами: `name`, `block`, `summary`,
   `data_source`, `inputs`, непустой `default_config["filename"]`.
2. Данные — из лоадера; контракт (`data_contract`, `FieldSpec`) проверяется в
   рантайме и его ошибки обязаны называть plot и поле.
3. Если для plot'а нужен свой CLI — `analysis/runners/<name>.py` + атрибут
   `runner = "runners/<name>.py"` в классе (реестр проверяет существование файла).
4. Тесты: `tests/test_render_smoke.py` рисует доступные plots блоков core и
   campaigns на синтетической фикстуре; для нового plot добавь подходящие
   синтетические данные и покрой новый блок/режим.
5. Перегенерируй `REGISTRY.md`; прогони `pytest -q -m 'guard or math or render'`.

## Rules

- Только реестр и runners; дублирование plot-кода в скриптах запрещено.
- `default_config` и пользовательский config не мутируются — merge делает plotter.
- Физическую методику в `loaders/`/`plots/` (центрирование, биннинг, формулы)
  менять нельзя — это отдельная явная задача.
- Существующие графики не перезаписывать без явной просьбы пользователя.
- Не читать крупные HDF5/снапшоты/PNG самому — этим занимаются лоадеры.
