# Active Context

## 2026-10-05 — prerun pipeline переведён на canonical runner

### Gitignore cleanup

- `.gitignore` теперь покрывает canonical IC-gate artifacts в
  `nbody/ics/*/ic_gate/`, legacy IC-gate files, которые писались прямо в
  `nbody/ics/<ic>/`, legacy generated output в `nbody/analyse/`, а также
  generated presentation exports (`pptx`, `gif/`, `images/`, HTML).
- Исходники `nbody/scripts/analysis/` и presentation source scripts/prompts
  намеренно не игнорируются. Уже tracked generated files не untrack'ились.

- Legacy IC/early gate CLI теперь содержит только аргументы, вызов loader-метрик
  и registry-based rendering; прямых импортов matplotlib/savefig в этих CLI нет.
- `nbody/scripts/run_matrix_dissipation_focused_T5.sh` переключён с
  `check_simulations/analyze_series.py` и `compare_shape_series.py` на
  `analysis/runners/make_prerun_plots.py` для series и shape режимов.
- `loaders.prerun.resolve_metrics_path()` поддерживает и новый путь
  `NBODY_ANALYSIS_ROOT/prerun/<run>/metrics_series.csv`, и старый
  `<run>/partial_analysis/metrics_series.csv`; это позволяет групповой shape
  анализу работать с уже существующими legacy runs.
- Проверено: `git diff --check`, `bash -n` pipeline, CLI `--help`, полный pytest
  (`50 passed`; остаётся только ожидаемое warning про пустой presentations block).

## 2026-10-09 — make-plots: актуальный каталог из реестра

- Skill уточнён как динамический путеводитель: на каждом запросе читать
  `nbody/analysis/REGISTRY.md`; для read-only вывода свежего каталога использовать
  `registry_docs.py --print`, не дублировать перечень в skill и не запускать
  запись каталога без отдельной необходимости.
- Фактический реестр: 26 графиков (`ic=1`, `prerun=4`, `core=7`, `campaigns=14`,
  `presentations=0`). Описание presentations runner в skill было преждевременным:
  runner отсутствует, блок пуст.
- Проверка перехода нашла незакрытый plotting debt: `analyze_series.py` и
  `compare_shape_series.py` всё ещё содержат matplotlib/savefig; legacy
  presentation source также остаётся вне analysis. IC/early gate wrappers уже
  используют общий layer, однако whitelist-комментарии раньше создавали
  впечатление, что весь этап миграции завершён. Уточнён статус whitelist.
- Проверки после правок: guard `7 passed`, полный suite `50 passed`;
  `git diff --check` чистый. Registry выведен через `--print` с временным
  `NBODY_ANALYSIS_ROOT`; `--check` на хосте с default `/nbody/analysis` не
  работает, т.к. `/nbody` недоступен вне контейнера.

## 2026-10-09 — продолжение унификации analysis

- Перенесены legacy series/shape CLI на `make_prerun_plots.py`; wrapper-сценарии
  оставляют прежние имена/основные флаги, но не рисуют напрямую. `--outdir` для
  произвольных каталогов намеренно не поддерживается (AnalysisPaths invariant).
- Presentation source/assets перенесены через writable bind mount контейнера в
  `nbody/analysis/presentations/`; отдельный plotting runner не нужен.
- Предварительное удаление `nbody_deepseek.pptx` не трогалось.
- Миграция `nbody/analyse/` и мусора остаётся отложенной; архивные результаты,
  в частности незавершённый corecusp, не перемещались.

Current focus:

- **corecusp: CDM↔SIDM σ/m=2 сравнение на первых снапшотах (2026-10-01)**:
  оба рана доведены до t=0.52 (snapshot_000/001/002), остановлены штатно
  (stop-file + свежие restart). Контроль: на t=0.02 раны идентичны
  (N_sidm/N_cdm median=0.9976) — разные только σ. **Ядро у SIDM сформировано**:
  slope 0.3–3 kpc CDM −1.279/−1.225/−1.273 (t=0.02/0.27/0.52) — касп держится;
  SIDM −1.186/−0.630/−0.445. ρ_SIDM/ρ_CDM = 0.19 (0.15 кпк), 0.46 (0.54 кпк),
  ~1 (1.5 кпк), 1.12 (2.6 кпк) — масса вынесена наружу. N(<0.5 кпк) упал в 3×
  (18269→6032), N(<1) −45%. σ_1D стала изотермальной (96–99 км/с), у CDM
  растёт 81→101. NI: 5.53M, 22.2% частиц (в ядре 99% r<0.3 кпк). Гейты:
  CDM PASS 7/7 все три точки; SIDM FAIL — интерпретировать как «ожидаемая
  физика» (no_immediate_core, central_density_stable, snap_matches_target,
  cdm_no_interactions — это CDM-семантика) + артефакт порога timesteps_sane
  (dtmin 7.45e-08 — 5 из 8563 точек, медиана стабильна 3.8e-5, темп растёт
  4.8→7.3e-5 Gyr/шаг). Энергия сохраняется: ΔE/|E| = 0.09% (SIDM), 0.004% (CDM);
  2T/|W| = 1.0059 / 1.0023. Графики: `/nbody/analysis/campaigns/corecusp/
  cdm_vs_sidm2_t052/` (5 из 6, montage упал по контракту — см. issues).
  Решение пользователя ждёт: продолжать ли оба до T=5.0.
- Pipeline hardening done (2026-08-25): git policy (`agent/dev`), fast test
  suite (`tests/`, 23 tests ~1 s), pre-commit auto-run, GitHub Actions CI
  (runs #1, #2 green). Memory bank synced with this state.
- Active simulation follow-up (2026-08-28): soft dSIDM run
  `/nbody/runs/test_dissipation/dsidm5_f005_k0_N1e5_T2_np4/` completed and
  passed final analysis after the harder `dsidm10_f05_k15_N1e5_T2` showed
  timestep-collapse before disk formation. Key result: completed/ok, 21/21
  snapshots, no pathology flags, final NI=5194 (4.21% particles), core density
  r<2=`6.5441e-04`, inner slope≈-0.614. Plots are in the run `plots/` folder.
- `/nbody/scripts/run_matrix_dissipation.sh` is now revised to an 11-run
  smoke-calibrated grid: CDM; SIDM σ=1/5/10; dSIDM σ=1,f=0.05/0.1/0.2,k=0;
  dSIDM σ=5,f=0.05,k=0; dSIDM σ=10,f=0.05/0.1/0.2,k=0. It no longer
  auto-deletes run folders. Default matrix launch now uses PROCS=8 and supports
  env override `GROUP=...`.
- Revised grid `/nbody/runs/test_dissipation_grid_sigma1/` completed. Pathological `dsidm10_f02_k0_N1e5_T2` was removed; 10 stable runs passed `run_full_test.py`. Shape/thickness comparison (`shape_compare/`) shows no T=2 dark-disk signature (`c/a(r<5)≈0.94`, `z/R≈0.67`, `|vrot|/sigma≈0.07`).
- Added presentation visual morphology package in `nbody/scripts/plot_scripts/compare_visual_morphology.py` plus registry plots. First T=5 partial render exists at `/nbody/runs/test_dissipation_focused_T5/visual_compare/` using current available snapshots: CDM t=5.0 and SIDM10 t=0.9; other focused runs will be included automatically when snapshots appear.
- Old N1e6 dwarf production runs are grouped under `/nbody/runs/sidm_dwarf_N1e6_T5/`.
  Oversized old `/nbody/runs/cdm_N1e6/` was deleted by user request.
- Legacy runs are archived under `/nbody/runs/archive/`: `legacy_cdm_sidm_N1e6/`,
  `test_sidm/`, and `logs/`. Top-level runs are now mostly grouped.

Current decision:

- Most AI-agent files live under `llm/` (tracked ONLY on `agent/dev`).
- Git model: single long-lived branch `agent/dev` for all agent work;
  no per-task branches; merge to master by documented procedure in
  `llm/rules/02-workflow.md` (untracks `llm/` on master).
- Commits follow template `llm/gitmessage.txt` (enabled via
  `git config commit.template`): fields RUN / TEST / RESULT.
- Cline should start nontrivial tasks in Plan mode.
- Operational protocols live in repo skills `gizmo-sim`, `make-plots`, and
  `check-run` (`skills/`, installed into `~/.codex/skills/` and
  `~/.agents/skills/` via `skills/install.sh` — run that script after any
  skill edit).
- Cline avoids large simulation outputs and binary data.
- Controlled simulations go under `nbody/runs/<run_name>/`.
- Fast tests may be run by the agent freely: `.venv/bin/python -m pytest tests/ -q`.

Current expected workflow:

- For code edits: inspect relevant files, propose patch, edit only after
  approval, validate with `pytest tests/`, commit on `agent/dev` per template.
- For simulation tasks: invoke the `gizmo-sim` skill (run/debug/generate-ic/
  summarize modes); for visualization invoke `make-plots`; for monitoring,
  ETA, timestep diagnosis, integrity checks, and completed-run summaries invoke
  `check-run`, backed by `nbody/scripts/check_simulations/`.

Next step:

- Campaign `/nbody/runs/dsidm_spin_k08_transition/` (k=0.8, sigma=2.5, T=2) fully computed: CDM+SIDM controls and dSIDM D=0.10/0.25/0.50/0.75. D=0.75 pathological (sync-point runaway, NI blow-up, `no-disk-before-pathology`); D<=0.50 stable but c/a stays ~0.81, no disk transition. Controls reuse policy active; matching controls present for this IC+settings.
- Merge accumulated `agent/dev` work into `master` (user decides when);
- deferred: level-3 plot tests (render smoke / contracts), CI annotations
  via third-party action if needed.

Known issues (broken paths):

- `nbody/gadget_test/run_gadget.sh` uses `/workspace/Gadget-2.0.7/Gadget2` instead of `/opt/gadget-2.0.7`.
- `nbody/gadget_test/Makefile` uses `/workspace/gsl` and `/workspace/fftw` instead of `/opt/gsl` and `/opt/fftw`.
- `nbody/gadget_test/run_gadget.sh` expects `galaxy.Makefile` and `galaxy.param` by default — only `lcdm_gas.param` and `Makefile` exist in the repo.
- GIZMO `Config_cdm_sidm.sh` enables `DM_SIDM=8` (particle type 3).

Known issues (tests/analysis, found while writing tests):

- `compare_runs.py` падает на последнем шаге с `visual_morphology_montage`:
  data contract требует поля `labels`, `faceon`, `edgeon` (dtype S), которые
  compare-путь не формирует. Пять остальных compare-графиков строятся до падения,
  поэтому фикс отложен (2026-10-01, `nbody/analysis/campaigns/corecusp/cdm_vs_sidm2_t052/`
  содержит 5 PNG + сводку).
- `loaders.write_summary()` CRASHES on snapshots without the `Masses` dataset
  (`d["mass"][:, None]`) — documented by tests; fix loaders if needed later.
- `shrink_center` is statistical: at N=2000 the 10% cut gives ~1–2.5 kpc
  center scatter (measured over seeds); exact reproduction covered by golden
  values instead.

Known file paths:

- GIZMO run script: `nbody/gizmo_test/run_gizmo.sh`
- GIZMO CDM params: `nbody/gizmo_test/gizmo_cdm.param`
- GIZMO SIDM params: `nbody/gizmo_test/gizmo_sidm.param`
- GIZMO config: `nbody/gizmo_test/Config_cdm_sidm.sh`
- GIZMO Makefile: `nbody/gizmo_test/GizmoMakefile`
- GIZMO systype: `nbody/gizmo_test/Makefile.systype`
- IC generation (old): `nbody/gizmo_test/generate_ics.sh`
- IC generation (new): `nbody/scripts/generate_ics.sh` — CLI-wrapper для GalIC, принимает JSON-конфиг
- IC merge/convert: `nbody/scripts/merge_ics.py` — универсальный конвертер PartType и мерджер HDF5
- GalIC params: `nbody/GalIC/halo_nfw_ics.param`
- Example IC config: `nbody/ics/example_cdm.json`
- IC output: `nbody/ics/<run_name>/`
- GADGET run script: `nbody/gadget_test/run_gadget.sh`
- GADGET params: `nbody/gadget_test/lcdm_gas.param`
- GADGET Makefile: `nbody/gadget_test/Makefile`
- Visualization: `nbody/scripts/plot_scripts/` (единственная plotting-инфраструктура: NbodyPlotter + registry + compare_runs), `nbody/scripts/convert_to_pt3.py`, `nbody/scripts/check_snapshot.py`
- Run wrappers: `nbody/scripts/run_sim.sh` (GIZMO CDM/SIDM), `nbody/scripts/generate_ics.sh` (GalIC IC generation)
- IC tools: `nbody/scripts/merge_ics.py` (universal HDF5 PartType converter/merger)
- Skills (operational protocols): `skills/gizmo-sim/SKILL.md` (run/debug/generate-ic/summarize), `skills/make-plots/SKILL.md` (visualization через plot_scripts), `skills/check-run/SKILL.md` (monitor/diagnose/summary existing runs via reusable `nbody/scripts/check_simulations/`, with human/json/tg output); installed into `~/.codex/skills/` and `~/.agents/skills/` via `skills/install.sh`

Removed legacy graphics scripts (2026-08-24, заменены `plot_scripts/`):
`png_to_gif.py`, `make_run_evolution.py`, `make_3d_animation.py`,
`nbody/gadget_test/example_snap.py`, `example_snap3D.py`, `ytvis.py`, `field_maker.py`.
