# Progress

What works:

- Repository has Docker-based scientific workflow.
- SIDM σ=20 dwarf run (`sidm20_dwarf_N100k`) verified 2026-08-21: reached TimeMax=2, module active (DM_SIDM=8, AGS 82% CPU).
- SIDM модуль количественно верифицирован (2026-08-23, `nbody/analyse/cdm_sidm_all/`): тренд «больше σ → мягче ядро» на N1e6 подтверждён, N100k σ=20 эффект слаб из-за малого времени (Time=2). `compare_all.py` научился читать σ из заголовка снапшота.
- Добавлен вывод NInteractions в снапшоты GIZMO (прототип, патчи в `nbody/patches/`), проверен smoke-тестом: t=0 → 0, t=0.05 → 7826 сум, 5.6% частиц.
- Полный прогон σ=20 N=1e6 T=5 завершён 2026-08-24 (`sidm20_dwarf_N1e6_T5`): 8.15M рассеяний, 51.4% частиц затронуто, радиальный профиль NI корректен. Авто-цепочка IC→GIZMO→анализ отработала без вмешательства.
- Repository separates stable container software and mounted user workspace.
- Agent infrastructure is being moved into `llm/`.
- Cline root entrypoint is kept minimal.
- Operational protocols migrated from `llm/prompts/` and `llm/workflows/` into agent skills `gizmo-sim` and `make-plots` (source in repo `skills/`, installed into `~/.codex/skills/` and `~/.agents/skills/` via `skills/install.sh`).

Known risks:

- Large simulation outputs can waste tokens.
- HDF5/snapshot/binary files should not be opened by Cline.
- Docker rebuilds and full simulation runs are expensive and should require explicit confirmation.
- Direct edits to `/opt` source trees are risky and should be avoided unless intentional.
- Baseline parameter/config files should not be overwritten for individual experiments.
- `run_gadget.sh` uses `/workspace/Gadget-2.0.7/Gadget2` which may need updating to `/opt/gadget-2.0.7`.
- `nbody/gadget_test/Makefile` uses `/workspace/gsl` and `/workspace/fftw` instead of `/opt/gsl` and `/opt/fftw` (also broken).
- `run_gadget.sh` expects `galaxy.Makefile` and `galaxy.param` by default — only `lcdm_gas.param` and `Makefile` exist.
- GIZMO `Config_cdm_sidm.sh` enables `DM_SIDM=8` (particle type 3).

TODO:

- [x] Verify actual GIZMO/GADGET/GalIC file paths.
- [x] Identify canonical parameter templates.
- [x] Identify canonical visualization scripts.
- [x] Test one minimal controlled simulation workflow (test_sidm_quick, 10k particles, t=0.1).
- [x] Create unified run wrapper `nbody/scripts/run_sim.sh` with CLI args, preflight, auto-build, logging.
- [x] Test automated run via `run_sim.sh` (test_sidm_auto, identical to manual test).
- [x] Create `nbody/scripts/generate_ics.sh` — GalIC wrapper with JSON config, auto-component generation.
- [x] Create `nbody/scripts/merge_ics.py` — universal HDF5 PartType converter/merger.
- [x] Test full pipeline: GalIC → merge_ics → IC generated (example_cdm, 10k particles).
- [x] Refactor plotting layer: `nbody/scripts/plot_scripts/` (NbodyPlotter, registry, data contracts, 2D/3D animations), удалить png_to_gif/make_run_evolution/make_3d_animation после успешного теста.
- [x] Переписать skill `make-plots` под plot_scripts (registry, describe, примеры), переустановить skills.
- [x] Удалить старые графические скрипты (glio/yt: example_snap*.py, ytvis.py, field_maker.py), адаптировать memory-bank.
- [x] Слить plot_config.py с PlotSettings (единый settings.py).
- [x] Multi-run comparison в registry + compare_runs.py; сводка -> loaders.write_summary; удалить analyze_final_snapshot.py, analyze_halo.py, compare_all.py; переключить run_sidm_batch.sh.
- [ ] Fix broken `/workspace/` paths in GADGET files (`run_gadget.sh`, `Makefile`).
- [ ] Test GADGET-2 workflow (requires path fixes first).
- [ ] Add CDM vs SIDM comparison run with `compare_runs.py` (на свежих данных).
- [ ] Test mixed IC generation (CDM + SIDM via multi-component JSON config).
- [ ] Add mixed CDM+SIDM example to the `gizmo-sim` skill (generate-ic mode JSON config).
- [x] Git policy: agent/dev branch, push rules relaxed for agent/*, commit template (2026-08-25).
- [x] Fast test suite: synthetic fixtures + loaders math tests + golden answer tests (`tests/`, 23 tests, ~1 s).
