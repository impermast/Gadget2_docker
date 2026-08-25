# Active Context

Current focus:

- Pipeline hardening done (2026-08-25): git policy (`agent/dev`), fast test
  suite (`tests/`, 23 tests ~1 s), pre-commit auto-run, GitHub Actions CI
  (runs #1, #2 green). Memory bank synced with this state.

Current decision:

- Most AI-agent files live under `llm/` (tracked ONLY on `agent/dev`).
- Git model: single long-lived branch `agent/dev` for all agent work;
  no per-task branches; merge to master by documented procedure in
  `llm/rules/02-workflow.md` (untracks `llm/` on master).
- Commits follow template `llm/gitmessage.txt` (enabled via
  `git config commit.template`): fields RUN / TEST / RESULT.
- Cline should start nontrivial tasks in Plan mode.
- Operational protocols live in repo skills `gizmo-sim` and `make-plots`
  (`skills/`, installed into `~/.codex/skills/` and `~/.agents/skills/` via
  `skills/install.sh` — run that script after any skill edit).
- Cline avoids large simulation outputs and binary data.
- Controlled simulations go under `nbody/runs/<run_name>/`.
- Fast tests may be run by the agent freely: `.venv/bin/python -m pytest tests/ -q`.

Current expected workflow:

- For code edits: inspect relevant files, propose patch, edit only after
  approval, validate with `pytest tests/`, commit on `agent/dev` per template.
- For simulation tasks: invoke the `gizmo-sim` skill (run/debug/generate-ic/
  summarize modes); for visualization invoke `make-plots`.

Next step:

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
- Skills (operational protocols): `skills/gizmo-sim/SKILL.md` (run/debug/generate-ic/summarize), `skills/make-plots/SKILL.md` (visualization через plot_scripts); installed into `~/.codex/skills/` and `~/.agents/skills/` via `skills/install.sh`

Removed legacy graphics scripts (2026-08-24, заменены `plot_scripts/`):
`png_to_gif.py`, `make_run_evolution.py`, `make_3d_animation.py`,
`nbody/gadget_test/example_snap.py`, `example_snap3D.py`, `ytvis.py`, `field_maker.py`.
