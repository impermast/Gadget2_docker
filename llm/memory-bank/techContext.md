# Tech Context

Host tools:

- VS Code
- Cline extension
- Docker
- Git

Container base:

- Ubuntu 20.04 or repository-defined base image

Scientific stack:

- OpenMPI
- GSL 1.16 (`/opt/gsl`)
- FFTW 2.1.5 (`/opt/fftw`, compiled with MPI, double and single precision)
- HDF5
- Python 3 with numpy, matplotlib, h5py, pandas
- GADGET-2 (source at `/opt/gadget-2.0.7`, compiled at runtime)
- GIZMO (source at `/opt/gizmo-public`, compiled at runtime)
- GalIC (pre-built at `/opt/GalIC`)
- glio (snapshot visualizer library at `/opt/glio`; user-side glio/yt scripts removed 2026-08-24)
- GIZMO built with SYSTYPE="kdsubuntu" (defined in `nbody/gizmo_test/Makefile.systype`)
- GADGET-2 Makefile uses `-DNOTYPEPREFIX_FFTW` (important for FFTW 2.1.5 compatibility)
- GIZMO config `Config_cdm_sidm.sh` enables `DM_SIDM=8` (particle type 3)
- GADGET-2 Makefile uses `-DPERIODIC -DUNEQUALSOFTENINGS -DPEANOHILBERT -DWALLCLOCK -DPMGRID=128 -DSYNCHRONIZATION`

Plot config — единый модуль стиля (`nbody/scripts/plot_scripts/settings.py`):
  Бывший `plot_config.py` УДАЛЁН (2026-08-24) и поглощён `settings.py`.
  Теперь один модуль содержит всё оформление: COLORS (palette/pastel/
  sequential/diverging/mono), SIZES, LINE_STYLES/MARKERS, STYLE, setup(),
  apply(ax, ...), save(fig, path) — плюс dataclass'ы RunPaths /
  SimulationInfo / PlotSettings.
  - Новая инфраструктура использует PlotSettings (фасад; применяется через
    NbodyPlotter, конкретные plots — settings.style_axis()/save_figure()).

Analysis output directory:
  `nbody/analyse/` — единая папка для всех результатов анализа.
  Каждый тест/сравнение — в своей подпапке:
    `nbody/analyse/sidm_sigma0.1/`     — одиночный прогон sigma0.1
    `nbody/analyse/cdm_sidm_comparison/` — сводные графики CDM vs все SIDM
  Все старые папки analysis/, analysis_all/ и т.д. удалены.
  Графики строятся скриптами, сохраняются напрямую или копируются в nbody/analyse/.

Important command classes:

- Docker image build
- container startup
- GADGET run scripts
- GIZMO run scripts
- GalIC IC generation
- PartType1→PartType3 conversion (`nbody/scripts/convert_to_pt3.py`)
- Multi-run comparison (`nbody/scripts/plot_scripts/compare_runs.py`)
- Standard plotting pipeline (`nbody/scripts/plot_scripts/`, см. ниже)
- Python visualization scripts

New plotting infrastructure (`nbody/scripts/plot_scripts/`, 2026-08-24):
- `settings.py` — ЕДИНЫЙ модуль стиля: COLORS/SIZES/STYLE/setup/apply/save (ex plot_config.py) + RunPaths / SimulationInfo / PlotSettings (глобальный стиль через rcParams);
- `base.py` — BasePlot ABC + data contract с runtime validation;
- `plotter.py` — NbodyPlotter (registry, describe, make_plot/make_plots), коллекции ANALYSIS_PLOTS / COMPARE_PLOTS / ANIMATION_PLOTS / ALL_PLOTS;
- `analysis_plots.py` — density, log_slope, sigma_v, interactions_radial + compare: density_compare, log_slope_compare, sigma_v_compare, core_density_vs_sigma;
- `animation_plots.py` — particles_2d, particles_3d (GIF, PIL);
- `loaders.py` — HDF5 → plot-ready данные + write_summary() (текстовая сводка);
- `run_full_test.py` — полный прогон всех plots одного run + validation-тесты + сводка;
- `compare_runs.py` — сравнение нескольких прогонов (замена compare_all.py / analyze_halo.py).

Removed legacy analysis/graphics scripts (2026-08-24, заменены `plot_scripts/`):
- `png_to_gif.py` (imageio отсутствовал — был нерабочим);
- `make_run_evolution.py`, `make_3d_animation.py` (заменены particles_2d/particles_3d);
- `nbody/gadget_test/example_snap.py`, `example_snap3D.py` (glio);
- `nbody/gadget_test/ytvis.py`, `field_maker.py` (yt);
- `analyze_final_snapshot.py` (сводка → loaders.write_summary, графики → registry);
- `analyze_halo.py`, `compare_all.py` (multi-run → compare_runs.py + compare-plots).
Не перенесённые niche-графики (phase r-vr, surface density compare, projected grid,
contour overlay, circularity, core density evolution по времени) удалены вместе
со скриптами; при необходимости добавляются в registry как новые concrete plots.

Test infrastructure (2026-08-25):

- pytest 9.1.1 in `.venv` (direct PyPI unreachable from this host — install
  via mirror: `pip install -i https://pypi.tuna.tsinghua.edu.cn/simple <pkg>`).
- `pytest.ini` в корне (`testpaths = tests`, addopts `-q`).
- Запуск: `.venv/bin/python -m pytest tests/ -q` (~0.2–1 s, 23 теста).
  Агент может гонять свободно, без подтверждений.
- `tests/synth_snap.py` — детерминированный генератор синтетических HDF5
  снапшотов (однородный шар N=2000 seed=42, центр (10,20,30), NI=5050 сумм,
  σ=20; схема точно как читает `loaders.read_snapshot`).
- `tests/test_loaders_math.py` — юнит-тесты математики loaders на аналитических
  ответах (slope ровно −3/0 на идеальных данных, точные NI-статистики и т.д.).
- `tests/test_golden.py` + `tests/golden/values.json` — answer testing
  (паттерн yt): эталонные метрики от той же фикстуры; регенерация ТОЛЬКО
  осознанно через `python tests/make_golden.py` + запись причины в
  `tests/golden/README.md`.
- Уровень 3 (render smoke тесты графиков) — отложен.

Auto-run of tests:

- Локально: pre-commit hook `githooks/pre-commit` (гоняет pytest перед каждым
  коммитом; включается `git config core.hooksPath githooks`; обход —
  `--no-verify`; без `.venv` просто предупреждает).
- CI: GitHub Actions `.github/workflows/tests.yml` — на каждый push в
  master/agent/dev и PR: checkout@v5, setup-python@v6 (Node 24, без
  deprecation warning), `pytest -v -ra --junitxml`, затем
  `.github/scripts/test_summary.py` пишет markdown-таблицу статистики тестов
  в Step Summary и лог. Прогоны бесплатны (публичный репозиторий).

Git policy (2026-08-25):

- Ветки: `master` (стабильно, агент не пушит напрямую) + единственная
  долгоживущая `agent/dev`. Веток под каждую задачу не создаём.
- Push `agent/*` разрешён с уведомлением пользователя.
- Шаблон коммитов `llm/gitmessage.txt` (git config commit.template):
  `<type>(<scope>): ...` + поля RUN / TEST / RESULT, связывающие историю git
  с experimentLog.md.
- `llm/` трекается только в `agent/dev`; при мерже в master снимается с
  трекинга процедурой из `llm/rules/02-workflow.md`.

Telegram notifications:
- `run_sim.sh` шлёт START/FINISH/ERROR в Telegram автоматически (по умолчанию, при наличии `nbody/tg/telegram.conf`); отключение — `--no-tg`, прогресс-уведомления — `--tg-progress` / `--tg-interval <n>`.
- Отправка реализована в `nbody/tg/` (`tg_notify.py` — модуль, `tg_event.py` — события, `tgbot.py` — polling-бот с командами /status, /runs и фоновым мониторингом).

High-risk actions:

- Docker rebuilds
- Docker prune/remove
- package installs
- full simulation runs
- direct edits under `/opt`
- deleting output folders
- overwriting baseline parameter/config files