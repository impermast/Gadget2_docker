# Active Context

Current focus:

- **corecusp campaign (2026-09-21, N=1e7; перестроена 2026-09-28 под ранний
  gate)**: `/nbody/runs/corecusp_status.txt` — единственная точка статуса.
  Схема: GalIC NFW c=20 v200=100 N=1e7 (MPI np=12, см. `galic_nprocs`) →
  IC-gate (`check_ic_cusp.py`, target из `galic_dm/rotcurve.txt`) → ранний
  production CDM `corecusp_cdm_N1e7_T5` (TimeMax не меняется, `TimeOfFirstSnapshot
  =0.02`, пауза через GIZMO stop-file, restart в `output/restartfiles/`) →
  `early_cdm_gate.py` → **WAITING_FOR_REVIEW** (продолжение и SIDM только по
  решению пользователя; команда продолжения — `run_sim.sh --resume`, см.
  `nbody/runs/corecusp/README.md`). Лог пайплайна:
  `/nbody/runs/corecusp_pipeline.log`. Причина задачи: в dwarf_N1e6 (v200=30,
  c=15, N=1e6) касп разрешён лишь вне ~0.3 kpc (N(<0.3 kpc)=4212), «core-cusp»
  эффект был замаскирован; SIDM20 тем не менее давал ядро (наклон →0,
  ρ(r<2 kpc) +20% к CDM). Литература: Power et al. 2003 (≳3000 частиц +
  t_relax>t_age), Elbert et al. 2015 (σ/m 0.5–50, ядра 300–1000 pc для
  Vmax≈40 km/s).
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
