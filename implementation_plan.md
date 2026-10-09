# Implementation Plan — унификация анализа и визуализации

> **Статус на 2026-10-09:** основной этап унификации CLI и перенос curated
> presentation assets завершён и закоммичен (`17de885`). Файл оставлен как
> backlog только для явно перечисленных ниже отложенных миграций/приёмки;
> эти пункты не блокируют завершённый этап.

## [Overview]

Цель: собрать весь визуал в один пакет `nbody/scripts/analysis/` с **реестром как
единственным источником истины для ИИ-агента**, а результаты анализа разложить по
блокам `nbody/analysis/{ic,prerun,core,campaigns,presentations}`; существующие
прогоны встроить в новую систему как «предыдущие раны» внутри кампаний.

Контекст, который определяет объём работ:

- Сейчас есть **два несовместимых подхода к рисованию**: реестр
  `nbody/scripts/plot_scripts/` (21 concrete plot, `BasePlot` + data contract +
  `NbodyPlotter`) и «рисующие сами себя» скрипты в `nbody/scripts/check_simulations/`
  (`check_ic_cusp.py`, `early_cdm_gate.py`, `analyze_series.py`,
  `compare_shape_series.py`) — они лепят matplotlib-фигуры вручную мимо реестра.
- Выходы анализа разбросаны: `nbody/analyse/` (5 легаси-папок, часть файлов
  трекается git), `nbody/runs/*/plots|partial_analysis|diagnostics|early_gate|**
  shape_compare|visual_compare`, `nbody/ics/*/ic_gate/`, `nbody/presentations/**`.
- `nbody/runs/**` и `nbody/ics/*/galic_*/` — git-ignored данные; изображения
  (`*.png|gif|pdf`) игнорируются глобально; трекаются только текстовые артефакты
  (`*.md`, `*.txt`, `*.csv`, `*.json`, параметры, скрипты).
- Прогон `runs/corecusp_cdm_N1e7_T5` остановлен **по замыслу**: сделан один «дешёвый» шаг до
  t=0.27 (`snapshot_000`, `snapshot_001`, restart на месте), pipeline завершился со статусом
  `WAITING_FOR_REVIEW`. Приоритет сейчас — verdict «всё ли ок в этой системе» на t=0.27
  (см. [Analysis Gate]), потому что цена полного прогона высока. Мелкий косметический нюанс:
  `run_sim.sh` при остановке по wall-time пишет в `experiment.md` «finished normally» — это можно
  поправить позже, на решения не влияет. Путь `nbody/scripts/run_sim.sh` в рефакторинге не
  меняем (на него ссылаются pipeline, skills, matrix-скрипты).

Подход: (1) механический перенос кода в новый пакет с сохранением математики
loaders дословно; (2) введение реестра с блоками и автогенерируемого
`nbody/analysis/REGISTRY.md`; (3) миграция «рисующих себя» скриптов в плагины
реестра; (4) раскладка результатов по блокам + интеграция старых прогонов в
кампании; (5) обновление skills/rules/memory-bank и тестов.

## [Types]

### 1. `PlotSpec` (new) — `nbody/scripts/analysis/registry.py`

```python
@dataclass(frozen=True)
class PlotSpec:
    name: str                 # уникальное имя plot'а, как в реестре ("density")
    block: str                # "ic" | "prerun" | "core" | "campaigns" | "presentations"
    cls: type[BasePlot]       # concrete plot class
    summary: str              # 1 строка: что показывает (для AI/человека)
    data_source: str          # какие данные ждёт: "prepare_profile_data", "series"
    runner: str               # канонический CLI для построения
    default_filename: str     # имя файла по умолчанию (из cls.default_config)
    inputs: tuple[str, ...]   # человекочитаемый вход: ("run",) | ("runs",) | ("ic",) | ("run+ic",)
    notes: str = ""           # подводные камни (напр. "requires NInteractions block")
```

`BLOCKS: dict[str, tuple[str, ...]]` — порядок и состав блоков:
`ic`, `prerun`, `core`, `campaigns`, `presentations`.
`REGISTRY: dict[str, PlotSpec]` — единый словарь всех plot'ов (заполняется при
импорте `plots/*`). `validate_registry()` падает, если: имя plot'а не совпадает с
`cls.name`, блок неизвестен, `summary` пуст, `default_filename` отсутствует,
`inputs` пуст, есть дубликат класса.

### 2. `AnalysisPaths` (new) — `nbody/scripts/analysis/paths.py`

```python
BLOCK_NAMES = ("ic", "prerun", "core", "campaigns", "presentations")

@dataclass
class AnalysisPaths:
    root: Path = Path("/nbody/analysis")

    def block(self, block: str) -> Path                      # root/<block>, mkdir, валидация блока
    def artifact_dir(self, block: str, name: str,
                     group: str | None = None) -> Path        # root/<block>[/<group>]/<name>
    def registry_md(self) -> Path                            # root/REGISTRY.md
```

Правило размещения: `run` → `core/<run>`; `ic` → `ic/<ic-name>`;
`prerun` → `prerun/<run>`; группа прогонов → `campaigns/<runs-group>/<run или group>`;
слайды → `presentations/<YYYY-MM-DD>[-name]`.

### 3. Существующие типы (переносятся без изменения семантики)

- `FieldSpec` / `BasePlot` / `PlotValidationError` (`base.py`) — без изменений
  кроме путей импорта; добавляется обязательный атрибут `block: str` у каждой
  concrete plot (проверяется `validate_registry()`).
- `PlotSettings`, `RunPaths`, `SimulationInfo` (`style.py`, ex `settings.py`) —
  сохраняются; добавляются функции `shade_unresolved()` и `resolve_xlim()`
  (уже реализованы 2026-09-29) и новый `AnalysisPaths`.
- `SeriesMetric` (`analyze_series.py`) переезжает в `loaders/series.py` как
  публичный тип конвейера метрик по снапшотам.


## [Files]

### Создание (новый пакет визуала)

```
nbody/scripts/analysis/               # ЕДИНЫЙ пакет визуала + анализа (реестр = источник истины)
  __init__.py
  registry.py        # PlotSpec + REGISTRY + BLOCKS + validate_registry() + to_markdown() + find(name)
  plotter.py         # NbodyPlotter (из plot_scripts/plotter.py, реестр-based)
  base.py            # BasePlot/FieldSpec/PlotValidationError (перенос из plot_scripts/base.py)
  style.py           # == переименованный settings.py: COLORS/SIZES/STYLE/setup/apply/save,
                     #   PlotSettings/RunPaths/SimulationInfo + shade_unresolved/resolve_xlim
  paths.py           # AnalysisPaths, BLOCK_NAMES (new)
  loaders/
    __init__.py      # re-export публичного API (обратно-совместимый интерфейс)
    snapshots.py     # read_snapshot, list_snapshots, softening/unresolved_radius (из loaders.py)
    profiles.py      # prepare_profile_data, write_summary, v_circ (из loaders.py, дословно)
    particles.py     # prepare_particle_snapshot, prepare_visual_snapshot, morphology, phase-space
    series.py        # SeriesMetric + build_series/metrics (из check_simulations/analyze_series.py)
    ic.py            # чтение GalIC-выходов/target-кривых, ic_gate-метрики (из check_ic_cusp.py)
  plots/
    __init__.py      # импортирует все модули блоков → триггерит регистрацию в REGISTRY
    core.py          # density, log_slope, sigma_v, interactions_radial, disk_edgeon (block="core")
    campaigns.py     # *_compare, core_density_vs_sigma, morphology montage/residuals/profiles,
                     #   phase_space, disk_dashboard, diag_* (block="campaigns")
    ic.py            # ic_gate_profile, ic_target_vs_particles (block="ic"; из check_ic_cusp.py)
    prerun.py        # early_cusp_compare, series_evolution, shape_panel, contact_sheet
                     #   (block="prerun"; из early_cdm_gate.py, analyze_series.py,
                     #    compare_shape_series.py)
    animations.py    # particles_2d, particles_3d (из animation_plots.py)
     presentations/ # исходники/готовые assets презентаций; отдельного runner/plot-класса нет
```

### Создание (runners — тонкие CLI поверх реестра)

```
  runners/
    make_run_plots.py            # все core-плоты одного run (ex run_full_test.py)
    make_ic_plots.py             # ic-plot'ы по каталогу GalIC-IC (ex plotting-часть check_ic_cusp.py)
    make_prerun_plots.py         # early gate + series evolution (ex early_cdm_gate.py + analyze_series.py)
    make_campaign_plots.py       # сравнения группы run'ов (ex compare_runs.py +
                                 #   compare_shape_series.py + compare_visual_morphology.py +
                                 #   make_campaign_diagnostics.py)
    registry_docs.py             # генерирует nbody/analysis/REGISTRY.md из REGISTRY.to_markdown()
  README.md          # короткий: «источник истины — nbody/analysis/REGISTRY.md» + карта модулей
```


### Создание (корень выходов)

```
nbody/analysis/
  REGISTRY.md        # АВТОГЕНЕРИРУЕМЫЙ каталог (из реестра, через registry_docs.py):
                     #   по блокам: name | summary | data_source | inputs | runner + пример
                     #   команды | default_filename | notes. ИИ читает ТОЛЬКО его.
  README.md          # карта блоков + правила размещения артефактов + ссылка на REGISTRY.md
  ic/<ic_name>/                 # ic_gate_profile.{png,csv,json}, ic_target_vs_particles.png, logs/
  prerun/<run_name>/            # early_gate.{png,csv,json}, series_evolution_*.png, shape_panel.png
  core/<run_name>/              # core-плоты одного production run + summary.txt
  campaigns/<campaign>/         # <run>/ (core-выходы участников) + compare/
  previous_runs/                # README.md: таблица «старый путь → новый путь»; артефакты
                                #   прежних прогонов, встроенные в кампании по логике
```

### Перенос/слияние (`git mv` + правка импортов)

- `plot_scripts/{plotter,base,settings}.py` → `analysis/{plotter,base,style}.py`
- `plot_scripts/loaders.py` → `analysis/loaders/{snapshots,profiles,particles}.py` (математика
  дословно, golden-тесты не меняются)
- `plot_scripts/analysis_plots.py` → `analysis/plots/{core,campaigns}.py` (разрез по блокам)
- `plot_scripts/animation_plots.py` → `analysis/plots/animations.py`
- `plot_scripts/{run_full_test,compare_runs,compare_visual_morphology,make_campaign_diagnostics}.py`
  → логика в `analysis/runners/make_*.py`
- `check_simulations/{analyze_series,compare_shape_series}.py` → метрики в
  `loaders/prerun.py`, графики в `plots/prerun.py`, канонический CLI
  `runners/make_prerun_plots.py`; старые CLI оставлены тонкими compatibility wrappers
- plotting-часть `check_simulations/{check_ic_cusp,early_cdm_gate}.py` → `plots/{ic,prerun}.py`;
  в гейтах остаются только метрики + verdict + `*_report.{json,csv,txt}`
- `nbody/presentations/*` → `nbody/analysis/presentations/*` (код и assets;
  build outputs `*.pptx` остаются ignored);
  runtime-выходы runner'ов по-прежнему размещаются через `AnalysisPaths` в `nbody/analysis/`
- выходы `nbody/analyse/*` → `campaigns/…` / `previous_runs/…` (см. [Migration]); пустую
  `nbody/analyse/` удалить

### Удаление мусора (согласовано)

- `nbody/scripts/.test_write`; `nbody/runs/{corecusp_pipeline.nohup,corecusp_pipeline.log,
  corecusp_resume.log,*.launcher.log}`; `nbody/ics/corecusp_gen.log`
- `/nbody/scratch/*_copy*` (копии 17 ГБ/файл, дубли `runs/`) — вынести в план списком,
  удалить только после повторного подтверждения в момент выполнения

### Правка (docs / tests / infra)

- `.gitignore`: `!nbody/analyse/**` → `nbody/analysis/**` (+ `!*.py/md/json/csv/txt`), убрать
  `nbody/presentations/**`
- `tests/conftest.py` — путь импорта `plot_scripts` → `analysis`; новые `tests/test_registry.py`,
  `tests/test_paths.py`, `tests/test_render_smoke.py`; `pytest.ini` — маркер `render`
- `skills/{make-plots,check-run,gizmo-sim}/SKILL.md`; `llm/rules/{04-gadget,06-simulation-pipeline}.md`;
  `llm/memory-bank/{techContext,systemPatterns,activeContext,progress}.md`
- `nbody/scripts/run_*.sh`, `nbody/runs/corecusp/*.sh` — только пути к plot-runner'ам
  (команды прогонов не трогаем); `run_sim.sh` НЕ перемещаем (идёт прогон)


## [Migration]

### Кампании (старые раны = предыдущие раны новой системы, не «легаси»)

| Данные (`nbody/runs/…`, не трогаем) | Куда в `nbody/analysis/` |
|---|---|
| `corecusp/` (pipeline) + `corecusp_cdm_N1e7_T5/` | `core/corecusp_cdm_N1e7_T5/` + `prerun/corecusp_cdm_N1e7_T5/` + `ic/corecusp_N1e7/` |
| `sidm_dwarf_N1e6_T5/` (5 прогонов) | `campaigns/sidm_dwarf_N1e6_T5/{<run>/,compare/}` |
| `dissipation/` (3 блока) | `campaigns/dissipation/{<block>/,compare/}` |
| `dsidm_spin_k08_transition/` (5 прогонов) | `campaigns/dsidm_spin_k08_transition/{<run>/,compare/}` |
| `archive/legacy_cdm_sidm_N1e6/` | `campaigns/cdm_sidm_N1e6/{<run>/,compare/}` |
| `archive/test_sidm/` | `campaigns/archive_test_sidm/` |
| `archive/misc/` (одиночные) | `core/<run>/` |

Переносимые артефакты (физически `mv`, содержимое не правим):

| Старый путь | Новый путь |
|---|---|
| `nbody/analyse/cdm_sidm_all/{N100k,N1e6}` | `campaigns/cdm_sidm_N1e6/compare/` |
| `nbody/analyse/cdm_sidm_comparison/` | `previous_runs/cdm_sidm_comparison/` (исходные run'ы удалены — historical) |
| `nbody/analyse/dwarf_series/` | `campaigns/sidm_dwarf_N1e6_T5/compare/` |
| `nbody/analyse/sidm20_N1e6_T5/` | `previous_runs/sidm20_N1e6_T5/` |
| `nbody/analyse/sidm_sigma0.1/` | `previous_runs/sidm_sigma0.1/` (historical) |
| `nbody/analyse/test_dissipation_block/` | `campaigns/dissipation/compare/legacy_block/` |
| `nbody/presentations/2026-09-10/`, `nbody/presentations/figs_v2/` | `nbody/analysis/presentations/2026-09-10/`, `…/2026-09-10-figs_v2/` |

След миграции — git-история переименований (отдельные README-карты
previous_runs/кампаний вычеркнуты 2026-10-09 как излишние). Каталоги `runs/`, `ics/`
**не переименовываем** — это сломало бы логи/состояние прогонов.

### Обратная совместимость CLI

`run_full_test.py` и `compare_runs.py` не оставляем; старые имена
`analyze_series.py` и `compare_shape_series.py` сохранены как тонкие CLI-прокси
на canonical runner без прямого matplotlib. Слой `analysis/__init__.py` реэкспортирует
`NbodyPlotter, PlotSettings, RunPaths, REGISTRY, AnalysisPaths`, чтобы один импорт давал всё.

## [Functions]

### registry.py (new)

- `register(cls: type[BasePlot]) -> type[BasePlot]` — декоратор: читает `cls.name/block/summary/…`,
  кладёт `PlotSpec` в `REGISTRY`, дубль имени → `ValueError`.
- `find(name: str) -> PlotSpec` — с подсказкой ближайших имён (`difflib`), сообщения как в
  `NbodyPlotter._validate_plot_name`.
- `by_block(block: str) -> list[PlotSpec]`; `blocks() -> list[str]`.
- `describe(name: str | None = None, block: str | None = None) -> str` — человекочитаемый
  отчёт (для `--describe`); без аргументов — сводка по блокам.
- `to_markdown() -> str` — сгенерированный `REGISTRY.md` (заголовок «НЕ РЕДАКТИРОВАТЬ ВРУЧНУЮ»,
  секции по блокам, таблица + блок примеров команд для каждого runner).
- `validate_registry() -> None` — целостность (см. [Types]); вызывается из теста и из
  `registry_docs.py`.

### paths.py (new)

- `AnalysisPaths.block`, `.artifact_dir`, `.registry_md` — см. [Types]; неизвестный блок →
  `KeyError` со списком допустимых.
- `default_analysis_root() -> Path` — уважает `NBODY_ANALYSIS_ROOT` (нужно для render-тестов
  в tmp_path).

### plots/* (перенос + новые)

- существующие 21 plot-класс: имена, contract'ы, поведение **без изменений**; добавляется
  атрибут `block` и `summary`; импорт `settings` → `style`.
- новые (блок `ic`): `ICTargetVsParticlesPlot` (`ic_target_vs_particles`) — target-кривые
  GalIC vs измеренные ρ(r), β(r), v_c(r) из `loaders/ic.py` + `NbodyPlotter`-шейдинг
  `r_soft`; `ICGateComparePlot` (`ic_gate_compare`) — IC-метрики нескольких IC между собой.
- новые (блок `prerun`): `EarlyCuspComparePlot` (`early_cusp_compare`) — ρ(r) и dlnρ/dlnr
  ранних снапшотов CDM-референса и SIDM/DSIDM-кандидатов (замена 3-панельного рисунка
  `early_cdm_gate.py`); `SeriesEvolutionPlot` (`series_evolution`) — временные ряды метрик
  (замена `analyze_series.plot_lines`); `SeriesContactSheetPlot` (`series_contact_sheet`);
  `ShapePanelPlot` (`shape_panel`) — замена `compare_shape_series.plot_compare`;
  `SeriesTimestepPanel` (`series_timestep_panel`) — dt/dtmin по `run.log`+снапшотам (отличается
  от существующего campaigns-плота `runaway_timestep_panel`, который строится по diag-JSON).
- новые (блок `presentations`): `SlideDensityPanel` (`slide_density_panel`),
  `SlideSlopePanel` (`slide_slope_panel`), `SlideMorphologyGrid` (`slide_morphology_grid`) —
  композиционные figure под фиксированный slide-размер (используют те же loaders, что и
  core/campaign-плоты; ex ручные figure из `figs_v2`/`build_pptx.py`).

### runners/* (new, argparse + общий `_common.py`)

- `_common.resolve_runs(args) -> list[Path]`, `_common.build_plotter(...) -> NbodyPlotter`,
  `_common.emit(paths: AnalysisPaths, made: list[Path]) -> None` — общая логика вывода.
- `make_run_plots.run_all(run: Path, analysis: AnalysisPaths, plots: list[str],
  snapshots: list[int], with_anim: bool, overwrite: bool) -> list[Path]`.
- `make_ic_plots.run_all(ic_dir: Path, target: Path | None, analysis: AnalysisPaths, …)`.
- `make_prerun_plots.run_all(run: Path, ref: Path | None, analysis: AnalysisPaths, …)` —
  пишет те же `early_gate.{json,csv,txt}`, что и прежний гейт (поля сохранены: verdict,
  cusp_slope, r_core_frac).
- `make_campaign_plots.run_all(group: Path, runs: list[Path], ref: Path | None,
  analysis: AnalysisPaths, kinds: list[str]) -> list[Path]`.
- Presentation assets are curated files; no `make_presentation_figures` API/runner is planned.
- `registry_docs.main()` — `REGISTRY.md` (детерминированный вывод: сортировка по блоку/имени).

### check_simulations/ (сужение до мониторинга)

- `check_ic_cusp.py`, `early_cdm_gate.py`: удалить блоки рисования, вызвать
  `runners.make_ic_plots` / `runners.make_prerun_plots`; stdout-отчёт и exit-коды не меняются.
- `check_run.py`, `check_block.py`, `verdict.py`, `eta.py`, `params.py`, `processes.py`,
  `snapshots.py`, `gizmo_log.py`, `formatting.py` — без изменений.

## [Classes]

- **Перенос без изменения поведения:** `BasePlot`, `FieldSpec`, `PlotValidationError`
  (`base.py`); `PlotSettings`, `RunPaths`, `SimulationInfo` (`style.py`); `NbodyPlotter`
  (`plotter.py`); 19 классов из `analysis_plots.py` + 2 анимации.
- **Новые:** `PlotSpec`, `AnalysisPaths` (dataclass'ы) и 10 plot-классов (см. [Functions]):
  `ICTargetVsParticlesPlot`, `ICGateComparePlot`, `EarlyCuspComparePlot`, `SeriesEvolutionPlot`,
  `SeriesContactSheetPlot`, `ShapePanelPlot`, `TimestepRunawayPanel`, `SlideDensityPanel`,
  `SlideSlopePanel`, `SlideMorphologyGrid`.
- **Helper-иерархия сохраняется:** `_MultiSeriesPlot`, `_DeltaComparePlot` переезжают в
  `plots/campaigns.py`.
- **Инвариант реестра:** каждый класс объявляет `name`, `block`, `summary`, `data_source`,
  `inputs`, `default_config["filename"]`; `validate_registry()` проверяет это на импорте и в
  тесте — поэтому `REGISTRY.md` не может разойтись с кодом.

## [Dependencies]

- Новых pip-пакетов нет: matplotlib 3.7.5, numpy, h5py, Pillow (GIF) уже в образе.
- `python-pptx` нужен только опциональному `build_pptx.py`; наличие проверяем отдельно, при
  отсутствии pptx-сборка остаётся опциональной и не блокирует рефакторинг.
- Внутренние: импорт `nbody/scripts/generate_ics_lib.py` (IC-target) через общий helper
  `paths.repo_scripts_dir()` вместо дублируемых `sys.path.insert` в 4 файлах.
- `check_simulations` больше не импортирует matplotlib напрямую: обратная зависимость
  мониторинга от визуала убирается.

## [Testing]

1. `pytest tests/ -q`: после правки `conftest.py` все текущие 23 теста (маркеры `math`,
   `golden`) проходят; golden-значения **не регенерируем** — математика loaders переносится
   дословно, расхождение = ошибка переноса.
2. `tests/test_registry.py` (маркер `math`): `validate_registry()` проходит; блоки непустые и
   равны `BLOCK_NAMES`; имена уникальны и `PlotSpec.name == cls.name`; `default_filename`
   непустой; `describe()` и `to_markdown()` содержат каждое имя; `find("densit")` →
   `ValueError` с подсказкой `density`.
3. `tests/test_paths.py`: `artifact_dir("core","x") == root/"core"/"x"`; неизвестный блок →
   `KeyError` со списком допустимых; `NBODY_ANALYSIS_ROOT` переопределяет root (monkeypatch).
4. `tests/test_render_smoke.py` (маркер `render`, уровень 3 — ранее отложен, дёшев на фикстуре
   N=2000): каждый применимый plot рисует в `tmp_path`, файл существует и `size > 1000`;
   GIF — ≥2 кадра; compare/slide-плоты на паре фикстур (ref + candidate).
5. Регрессия CLI на реальных данных (в контейнере, логи в `analysis/…/logs/`):
   - `make_run_plots.py --run-root /nbody/runs/corecusp_cdm_N1e7_T5 --plots density,log_slope`
     → файл в `analysis/core/corecusp_cdm_N1e7_T5/`, значения совпадают с прежними `plots/`;
   - `make_prerun_plots.py --run …` → `early_gate.json` с теми же полями/значениями, что
     прежний `runs/…/early_gate/early_gate.json`;
   - `make_ic_plots.py --ic /nbody/ics/dwarf_N1e6` → метрики прежнего smoke-гейта воспроизведены;
   - `registry_docs.py` → `REGISTRY.md` содержит 31 plot (21 перенесённый + 10 новых).
6. Приёмка «ИИ-путеводителя»: по одному лишь `REGISTRY.md` (без чтения кода) собрать команды для
   «профиль плотности с заштрихованной unresolved-зоной» и для «IC-гейт»; обе обязаны запускаться.
7. `git status --short nbody/analysis` — в индекс попадают только `.md/.py/.json/.csv/.txt`.

## [Analysis Gate] — приоритет №1: вердикт «всё ли ок» по шагу t=0.27

Только read-only проверки (ничего не перезаписываем; артефакты — в `nbody/runs/corecusp_analysis/`).
Критерии GO/NO-GO к дорогому прогону T=5.0:

| # | Проверка (t=0 → t=0.27) | GO | WARN | NO-GO |
|---|---|---|---|---|
| 1 | наклон ρ(r) в 1–3 kpc | \|Δ\|<0.05 от IC (−1.00) | 0.05–0.15 | >0.15 (ранний core-collapse / ошибка IC) |
| 2 | M(<r) внутри 1, 3, 10 kpc | дрейф <0.5 % | 0.5–2 % | >2 % (утечка массы/границы/ошибка MNR) |
| 3 | профиль σ_∥(r) в 0.3–3 kpc | монотонный, без «горячего центра» | немонотонность <15 % | центральное Heating >30 % |
| 4 | v_c(r) внутри 1–3 kpc vs IC-target | \|Δ\|<3 % | 3–10 % | >10 % (недо-насыщение bbar, см. fix_ic_mass_deficit) |
| 5 | позиция centre_of_mass / смещение хало | <0.02 kpc | 0.02–0.1 kpc | >0.1 kpc (нет центратора, шум ядра) |
| 6 | выбросы: частицы с r>3×r vir и v>v_esc | <0.05 % | 0.05–0.5 % | >0.5 % (численный взрыв/некорректные dt) |
| 7 | численка: dtmin, NtreeForce, `MaxNumSizeInterp` | dtmin>1e-4, NtreeForce=0, warnings=0 | dtmin 1e-5…1e-4 | dtmin<1e-5 или NtreeForce>0 |
| 8 | сохранение энергии (T из снапшотов, ΔT/|T| за шаг) | <1 % | 1–5 % | >5 % |
| 9 | сетка/структура: ρ(r) гладкая, без «ступенек» на r_soft и r_trunc | визуально + р-профиль без разрывов | мелкая рябь | разрыв/провал на r_soft (недостаб. MNR) |

Порядок: (а) посчитать 1–9 по `snapshot_000` vs `snapshot_001` + логам; (б) сводная таблица в чат
и в `nbody/runs/corecusp_analysis/t027_review/verdict.md`; (в) вердикт GO / GO-with-fixes / NO-GO
со списком конкретных правок. Рефакторинг из остальной части плана выполняется **после** этого
вердикта (чтобы не смешивать научные правки с переездом кода), если пользователь не скажет иначе.

## [Skills] — жёстко прописанные скиллы (источник процедурной правды для ИИ)

Принцип «жёстко, но с манёвром»: каждый скилл = процедурный скрипт
(шаги, команды, запреты + развилки «если X — то Y»), а пространство для
манёвра — **строго внутри**: выбор config-ключей из `REGISTRY.md`,
пороги вердикта, решение «расширить реестр» (только процедурой §8.2).
Вне скилла разрешено: читать код `analysis/`, выбирать plot/config/порог,
предлагать правки плана. Вне скилла запрещено: pyplot/savefig вне `analysis/`,
свободные пути вывода, свои скрипты-анализаторы (всё это ловит guard-тест).

### 8.1 `make-plots` v2 — единственный путь к любому графику

Переписать `skills/make-plots/SKILL.md` полностью:

0. Преамбула: `.clinerules/00-entrypoint.md` + `llm/rules/` + memory-bank, русский.
1. Прочитать `nbody/analysis/REGISTRY.md` (НЕ код plot'ов). Найти plot по задаче
   (`find` по таблице/сводке; при неуверенности — `describe(name)`).
2. Развилка:
   - **plot есть** → взять блок/inputs/runner/пример команды из REGISTRY.md,
     собрать команду runner'а (только `--run/--runs/--ic`, `--plots`, config-ключи
     из spec; НИКАКИХ `--outdir`), выполнить в контейнере,
     доложить путь (он детерминирован: `artifact_dir(block, имя)`).
   - **plot нет** → процедура §8.2 (ни в коем случае не pyplot на месте).
3. Проверка: файл существует, размер > 1000 байт, для GIF — ≥2 кадров.
4. Отчёт (рус.): plot'ы, вход, выход, точные команды, файлы+размеры, warnings.
Запреты: никаких standalone-скриптов; не мутировать `default_config`;
не править формулы loaders/plots (это отдельная задача); не перезаписывать
существующие PNG без просьбы; выводы агентов — только по CSV/TXT/статика-PNG,
не по GIF (агент их не видит), как уже принято в check-run.

### 8.2 Процедура «нужного графика нет» (часть make-plots v2)

1. Подтвердить отсутствие: `find`/похожие имена (`difflib`-подсказка), соседние блоки.
2. Определить блок по типу входа (ic/prerun/core/campaigns/presentations);
   данные — только через существующие `loaders/*` (новый loader = тоже ревью).
3. Создать класс в `analysis/plots/<блок>.py`: `name/block/summary/data_source/inputs/runner/notes`,
   `data_contract` (FieldSpec), `default_config` с `filename`, `render()`.
4. Повесить `@register`, прогнать `pytest -q` (guard+registry+render обязаны зеленеть),
   `registry_docs.py` (REGISTRY.md обновляется автогенерацией).
5. Показать пользователю diff + свежую картинку; без аппрува новых plot-классов
   в `agent/dev` не коммитить.

### 8.3 `check-run` v2 — процедурные проверки прогонов

Переписать `skills/check-run/SKILL.md`:

- Маршрутизация по вопросу: прогресс/здоровье/ETA → `check_run.py --mode auto|monitor`;
  подозрение на патологию → `--mode diagnose`; итог → `--mode summary`;
  группа → `check_block.py`; динамика остановленного/патологического →
  `analyze_series.py` (метрики из CSV/TXT, PNG только для человека).
- **Gate-интерпретация σ-зависимая** (урок corecusp 2026-10-01): провал
  `no_immediate_core / central_density_stable / snap_matches_target /
  cdm_no_interactions` на SIDM-ране — ожидаемая физика ядра, НЕ патология;
  реальные красные флаги: `virial_sane`, `resolution_ok`, `dt`-runaway по медиане
  (не по 0.06% всплескам минимума), `NtreeForce>0`. Порог `dtmin>1e-7` интерпретировать
  через медиану/тренд темпа, а не мгновенный минимум.
- Запреты: не останавливать/не удалять прогоны; не запускать симуляции;
  не строить финальных выводов по незавершённому/патологическому рану;
  не открывать массивы снапшотов вручную (только `NInteractions`-сводка через чекер).
- Отчёт в чат — по фиксированному списку из 10 пунктов (уже есть, оставить);
  `--format tg` — только для Telegram, таблицы широкие нельзя.

### 8.4 `gizmo-sim` — точечные правки

Режим `run` п.8 и раздел «What run_sim.sh does internally»: заменить
`plot_scripts/run_full_test.py` → `make_run_plots.py`, `plots/` прогона →
выход `analysis/core/<run>/` (runner сам положит). Остальное без изменений;
skill-creator не трогаем (мета-скилл, покрыт `skills/install.sh`).

### 8.5 Распространение и приёмка скиллов

- После любой правки `skills/*/SKILL.md` — `bash skills/install.sh`
  (копии в `~/.codex/skills`, `~/.agents/skills`).
- Каждый скилл в шапке ссылается на `llm/rules/08-analysis-workflow.md` как
  на норматив, в теле — только процедуры.
- Тест «ИИ-путеводителя» (этап 7): агент, видя ТОЛЬКО `REGISTRY.md` + скилл,
  без чтения кода обязан собрать рабочие команды для
  (а) профиля плотности с unresolved-шейдингом,
  (б) IC-гейта,
  (в) новой проверки «вердикт по двум ранам одной командой» (сценарий corecusp);
  все три запускаются и кладут файлы в ожидаемые `artifact_dir`.

## [Implementation Order]

1. **Скелет дерева и реестра** (без риска для прогона): `nbody/scripts/analysis/{__init__,
   registry,paths}.py` + `plots/__init__.py`; `PlotSpec`, `validate_registry`, `to_markdown`;
   тесты 2–3.
2. **Механический перенос visual-кода** (`git mv`): `plot_scripts/*` →
   `analysis/{plotter,base,style}.py`, `analysis/loaders/{snapshots,profiles,particles}.py`,
   `analysis/plots/{core,campaigns,animations}.py`; правка импортов; `check_simulations` не
   трогаем; `pytest -q` — 23 теста зелёные.
3. **Блок-атрибуты + декоратор `@register`** у всех 21 класса; `NbodyPlotter` переведён на
   `REGISTRY` (API `make_plot/make_plots/describe` сохранён); тест 4 (`render`);
   `registry_docs.py` → `nbody/analysis/REGISTRY.md`.
4. **Миграция «рисующих себя» скриптов:** `loaders/{ic,series}.py`, `plots/{ic,prerun}.py`,
   `runners/{make_ic_plots,make_prerun_plots,make_campaign_plots}.py`; в гейтах остаются
   метрики/verdict; регрессия 5 (сверка старых и новых `*.json`).
5. **Presentations:** перенесены tracked source/assets из `nbody/presentations/*` в
   `nbody/analysis/presentations/*`. Отдельный presentation runner и plot-классы
   не нужны (решение пользователя); block `presentations` остаётся asset-only и пустым в реестре.
6. **Раскладка выходов и кампании:** `mv` по таблице [Migration], `analysis/README.md`,
  `.gitignore` (analyse→analysis, presentations), удаление пустого `nbody/analyse/`.
7. **Уборка мусора** по списку [Files]; отдельный запрос на `nbody/scratch/*_copy*`.
8. **Документы и навыки:** `skills/{make-plots,check-run,gizmo-sim}/SKILL.md`,
   `llm/rules/04-gadget.md`, `06-simulation-pipeline.md`, memory-bank
   (`techContext`, `systemPatterns`, `activeContext`, `progress`), пути plot-runner'ов в
   `nbody/scripts/run_*.sh` и `nbody/runs/corecusp/corecusp_pipeline.sh`; полный `pytest -q`,
   `git status`, запись в `experimentLog.md`/`progress.md`.
9. **(опционально, после подтверждения)** перегруппировка батч-скриптов: `run_matrix_*`,
   `run_series_dwarf`, `run_sidm_batch` → `nbody/scripts/runs/`; `generate_ics.sh`,
   `merge_ics.py`, `convert_to_pt3.py`, `add_halo_rotation.py` → `nbody/scripts/ic/`.

## [Status] — чеклист по состоянию на 2026-10-09

### Сделано

- [x] **Этапы 0–3:** `test_layout_guard.py` (маркер `guard`), `AnalysisPaths`
  с проверкой сегментов/containment, `registry.py` (+ проверка существования файла
  runner'а), `loaders/{snapshots,profiles,particles,ic,prerun}`, `plots/{core,campaigns,animations,ic,prerun}`
  (26 plot c `@register` и `block`), перевод `NbodyPlotter.register_defaults()` на
  глобальный реестр.
- [x] **Этап 4 (механический перенос):** legacy-каталог
  `nbody/scripts/plot_scripts/` удалён целиком; `analysis/README.md` — карта слоя;
- whitelist в guard-тесте уменьшен (остались 2 legacy gate CLI — этап 3).
  Зависимые места обновлены:
  `check_simulations/analyze_series.py` (импорт `analysis.loaders`),
  `tests/make_golden.py`, `run_*.sh` (runner'ы вместо legacy CLI), `.gitignore`
  (`nbody/analysis/**` + трекается только `REGISTRY.md`).
- [x] **Runners (этапы 3/4):** `make_run_plots.py` (core), `make_campaign_plots.py`
  (profile-compare), `make_campaign_morphology_plots.py`,
  `make_campaign_diag_plots.py`, `registry_docs.py` (+`--check`). Все проверены
  запуском в контейнере на реальных прогонах; `--outdir` нигде нет (guard-тест).
- [x] **Текущая валидация:** полный suite 51 passed; registry `--check`, shell syntax,
  legacy CLI `--help`, `git diff --check` и asset checksum validation прошли.
- [x] Актуализированы текущие source/output paths и статус migration в memory-bank;
  исторические experiment entries сохранены как история.
- **Историческая база тестов:** первоначально 50 зелёных, включая `test_registry.py`, `test_paths.py`,
  `test_render_smoke.py` (рендер ВСЕХ plots блоков core и campaigns на синтетической
  фикстуре), `test_plotter_contract.py` (негативные контракты, перенесены из
  удалённого `run_full_test.py`) и guard-тест `no_undefined_names_in_analysis`
  (ловит потерянные при переносе импорты/хелперы — реально нашёл 3 регрессии:
  `Mapping`/`validate_fields`/`LogNorm` в plots и `_snapshot_number` в loaders).
### Сделано в текущем продолжении

- [x] Перенос презентационных скриптов, prompt и существующих GIF/PNG, а также
  дополнительных curated PNG/HTML в `nbody/analysis/presentations/`; скрипты
  используют относительные пути и новый API loaders. Отдельный runner не создавался.
- [x] `analyze_series.py` и `compare_shape_series.py` стали совместимыми CLI-прокси
  на `make_prerun_plots.py`; прямой matplotlib из них удалён.
- [x] Убран ложный `make_presentation_figures.py` из реестра; для asset-only блока
  пустой runner допустим, а каждый зарегистрированный plot по-прежнему обязан иметь runner.
- [x] Matrix script и `check-run` skill используют canonical prerun runner.

### Осталось / отложено

- [x] Перенос tracked/generated outputs `nbody/analyse/` в `previous_runs/` и кампании
  (выполнено 2026-10-09: `mv` по таблице [Migration] через writable bind mount
  контейнера; tracked тексты зафиксированы как git renames, PNG/GIF остались
  ignored; пустой `nbody/analyse/` удалён).
- [x] ~~Создать `previous_runs/README.md` и README кампаний с картой перемещённых результатов~~ —
  вычеркнуто 2026-10-09 как излишнее (решение пользователя): след миграции —
  git-история переименований, карта блоков — `nbody/analysis/README.md`.
- [x] Удаление перечисленного мусора (выполнено 2026-10-09 с подтверждения
  пользователя: `nbody/scripts/.test_write`, `nbody/runs/corecusp_pipeline.*`,
  `corecusp_resume.log`, оба `*.launcher.log`, `nbody/ics/corecusp_gen.log`;
  `nbody/scratch/*_copy*` отсутствует в дереве; удаление PPTX подтверждено и
  включено в этот же коммит).
- [x] Завершить актуализацию `skills/{check-run,gizmo-sim}`, `llm/rules/04-gadget.md`,
  `06-simulation-pipeline.md`, `techContext.md`, `systemPatterns.md` и ссылок во всех shell scripts.
  (выполнено 2026-10-09: `06-simulation-pipeline.md` и оба skill указывают на
  canonical `nbody/analysis/`; `run_matrix_dissipation.sh` и `run_series_dwarf.sh`
  читают `analysis/core/<run>/`; `04-gadget.md` не содержал устаревших путей;
  techContext/systemPatterns отражают миграцию. Остаточные упоминания
  `run_full_test`/`plot_scripts` — только исторические комментарии о происхождении
  кода и записи experimentLog.)
- [ ] Приёмка «ИИ-путеводителя» §8.5.
- [ ] Проверить с пользователем оставшийся старый legacy gate CLI whitelist
  (`check_ic_cusp.py`, `early_cdm_gate.py`) и убрать его после проверки потребителей.

## [Risks / Constraints]

- **Отдельная, более приоритетная проблема (вне рамок этого плана):**
  production-прогон `corecusp_cdm_N1e7_T5` приостановлен решением пользователя
  2026-10-09 (cusp-решение уже видно, дальнейший ран не требуется); его IC-gate
  тексты и early-gate скопированы в `analysis/ic/corecusp_N1e7/` и
  `analysis/prerun/corecusp_cdm_N1e7_T5/`, summary — в
  `analysis/core/corecusp_cdm_N1e7_T5/`. Сами каталоги `nbody/runs/` и `nbody/ics/`
  не переименовывались.
- Если вы перезапустите прогон: шаги 1–8 не пишут в `output/`, `restartfiles/`, `run.log*`
  выбранного рана и не удаляют его артефакты (только копируем; оригиналы убираем на шаге 6).
- Все перемещения — `mv`/`git mv`, ничего не удаляется кроме явного списка мусора;
  след миграции — git-история переименований (отдельные README-карты
  previous_runs/кампаний вычеркнуты 2026-10-09 как излишние).
- Каталоги `nbody/runs/**` и `nbody/ics/**` не переименовываем (иначе порвём логи/состояние
  прогонов и ссылки в experimentLog).
- Реестр — единственный источник описаний: `REGISTRY.md` генерируется, ручная правка запрещена
  заголовком-предупреждением в самом файле.
- Критерий корректности: в diff нет изменений формул/метрик (только пути, импорты, блоки,
  новые plot'ы), golden-тесты проходят без регенерации.
