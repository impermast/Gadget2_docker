# Tech Context

> Older entries below are historical; current layout is the `analysis` package
> and canonical output root documented here.

> Historical notes below include old paths/layouts. Current source of truth for
> plotting and analysis is `nbody/scripts/analysis/`; canonical output root is
> `nbody/analysis/`. Legacy outputs from `nbody/analyse/` were migrated on
> 2026-10-09 (move trace: git rename history). Separate previous_runs/campaign
> README maps were dropped the same day as redundant.

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

Analysis/plotting package: `nbody/scripts/analysis/` — canonical реестр,
`AnalysisPaths`, `NbodyPlotter`, стиль, loaders, plots и CLI runners.
Presentation inputs/assets хранятся отдельно в `nbody/analysis/presentations/`;
этот registry block asset-only и отдельного runner не имеет.

Canonical analysis output root: `nbody/analysis/` (container: `/nbody/analysis/`),
with generated `REGISTRY.md` and `ic/`, `prerun/`, `core/`, `campaigns/`,
`previous_runs/` blocks. Runners derive output destinations through `AnalysisPaths`.
Migrated text artifacts (summaries, READMEs, params) are tracked via `.gitignore`
exceptions; generated PNG/GIF stay ignored. The old `nbody/analyse/` directory
was removed after the move (contents verified byte-identical via git rename
detection for the tracked texts); corecusp outputs under `nbody/runs/` were
deliberately left in place pending the run-status decision.

Important command classes:

- Docker image build
- container startup
- GADGET run scripts
- GIZMO run scripts
- GalIC IC generation
- PartType1→PartType3 conversion (`nbody/scripts/convert_to_pt3.py`)
- Multi-run comparison and standard plotting (`nbody/scripts/analysis/`)
- Python visualization scripts

Canonical analysis layout (migration completed 2026-10-09):
- `registry.py`, `paths.py`, `base.py`, `plotter.py`, `style.py`;
- `loaders/` converts IC/snapshot/series inputs into plot-ready data;
- `plots/` contains registered plot classes by block;
- `runners/` contains IC, prerun, run, campaign, and registry-doc CLIs.

Historical removals from the pre-registry plotting layer (2026-08-24):
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
- Запуск: `.venv/bin/python -m pytest tests/ -q` (suite grows as regression tests are added).
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
- Группы тестов через маркеры (pytest.ini): `math` (уровень 1) и `golden`
  (уровень 2); запуск группы — `pytest tests/ -m <group>`. В CI каждая группа
  — отдельная matrix-джоба (своя строка в Actions UI); новая группа =
  маркер в pytest.ini + элемент в strategy.matrix.group в tests.yml.

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

- Telegram notifications:
- `run_sim.sh` шлёт START/FINISH/ERROR в Telegram автоматически (по умолчанию, при наличии `nbody/tg/telegram.conf`); отключение — `--no-tg`, прогресс-уведомления — `--tg-progress` / `--tg-interval <n>`.
- Отправка реализована в `nbody/tg/` (`tg_notify.py` — модуль, `tg_event.py` — события, `tgbot.py` — polling-бот с командами /status, /runs и фоновым мониторингом).

Operational validation workflow:
- `nbody/scripts/check_simulations/` — reusable monitoring/diagnostic tools: `check_run.py` for one run, `check_block.py` for groups, and `analyze_series.py` for partial/pathological series diagnostics; parse `run.log`, `run.state`, run params, snapshot inventory/latest metadata, detect timestep pathology, estimate simple ETA, output `human`, `json`, or compact Telegram-safe `tg` reports, and quantify shape/thickness/rotation/core-density/NInteractions evolution over completed snapshots.
- `.cline/skills/check-run/SKILL.md` — thin orchestration skill that invokes these scripts instead of ad-hoc checks; plotting uses the canonical analysis runners when runs are complete enough.

High-risk actions:

- Docker rebuilds
- Docker prune/remove
- package installs
- full simulation runs
- direct edits under `/opt`
- deleting output folders
- overwriting baseline parameter/config files