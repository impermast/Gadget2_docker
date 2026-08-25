# Active Context

Current focus:

- Git policy + fast test infrastructure implemented (2026-08-25):
  - single long-lived branch `agent/dev` for all agent work; merge to master
    by documented procedure (llm/rules/02-workflow.md) which untracks llm/
    on master;
  - commit template `llm/gitmessage.txt` enabled via git config
    (fields RUN / TEST / RESULT linking commits with experimentLog.md);
  - `tests/` — yt-style answer testing: deterministic synthetic HDF5 fixture
    (`synth_snap.py`, uniform sphere seed=42 N=2000), unit tests of loaders
    math (`test_loaders_math.py`, 22 tests) and golden values
    (`test_golden.py` + `golden/values.json`, regenerate ONLY deliberately
    via `tests/make_golden.py`). Full suite runs in ~1 s; agent may run
    pytest freely.
  - pytest installed into .venv (9.1.1; direct PyPI unreachable, used
    tuna mirror).

Current decision:

- Most AI-agent files live under `llm/`.
- Root keeps only minimal Cline entrypoint files:
  - `.clineignore`
  - `.clinerules/00-entrypoint.md`
- Cline should start nontrivial tasks in Plan mode.
- Cline should read `.clinerules/00-entrypoint.md`, then `llm/rules/` and `llm/memory-bank/`.
- Operational protocols (simulation run, IC generation, debugging, onboarding summary, plotting) are captured in the repo skills `gizmo-sim` and `make-plots` under `skills/`. They are installed into the agent discovery roots (`~/.codex/skills/` and `~/.agents/skills/`) as real copies via `skills/install.sh` — run that script after any skill edit. The former `llm/prompts/` and `llm/workflows/` folders were removed.
- Cline should avoid large simulation outputs and binary data.
- Controlled simulations should be created under `nbody/runs/<run_name>/`.

Current expected workflow:

- For code edits: inspect relevant files, propose patch, edit only after approval.
- For simulation tasks: invoke the `gizmo-sim` skill (run/debug/generate-ic/summarize modes); for visualization invoke `make-plots`.

Next step:

- Verify actual repository file paths and update this memory file with concrete files used for GIZMO, GADGET, GalIC, and visualization.

Known issues (broken paths):

- `nbody/gadget_test/run_gadget.sh` uses `/workspace/Gadget-2.0.7/Gadget2` instead of `/opt/gadget-2.0.7`.
- `nbody/gadget_test/Makefile` uses `/workspace/gsl` and `/workspace/fftw` instead of `/opt/gsl` and `/opt/fftw`.
- `nbody/gadget_test/run_gadget.sh` expects `galaxy.Makefile` and `galaxy.param` by default — only `lcdm_gas.param` and `Makefile` exist in the repo.
- GIZMO `Config_cdm_sidm.sh` enables `DM_SIDM=8` (particle type 3).

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
