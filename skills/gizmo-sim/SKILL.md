---
name: gizmo-sim
description: Run, debug, or plan controlled GIZMO CDM/SIDM simulations and generate GalIC initial conditions in this Dockerized repo via the run_sim.sh and generate_ics.sh wrappers. Use when the user asks to launch a CDM or SIDM run, create initial conditions, debug the GIZMO workflow, or summarize the project architecture. Not for standalone plotting.
metadata:
  short-description: GIZMO CDM/SIDM simulation lifecycle
---

# GIZMO Simulation Lifecycle (CDM/SIDM)

## Preamble (always do first)

1. Read `.clinerules/00-entrypoint.md`.
2. Read every file in `llm/rules/` and `llm/memory-bank/`.
3. Communicate with the user in Russian.

## Canonical tools

- `bash /nbody/scripts/run_sim.sh` — unified GIZMO run wrapper. NEVER manually copy/param-patch/sed/mpirun.
- `bash /nbody/scripts/generate_ics.sh --config <config.json>` — GalIC initial-condition generator.

## Mode selection

Determine intent from the user request:

| Request pattern | Mode |
|---|---|
| "summarize project", onboarding, orientation | summarize |
| "debug GIZMO", crashes, failures, broken workflow | debug |
| "generate ICs", new galaxy/halo model | generate-ic |
| "run simulation ..." (default) | run |

## Mode: summarize

Inspect only small tracked text files (`README.md`, `.gitignore`, `Dockerfile`, `run_docker_gui_linux.sh`, small `.sh`/`.param`/`.cfg`/`Makefile*`/`Config*`/`.py`/`.md` under `nbody/`). Never open HDF5, snapshots, binaries, plots, archives, or generated outputs.

Produce in Russian:

1. project architecture;
2. Docker/container workflow;
3. GADGET workflow;
4. GIZMO workflow;
5. GalIC workflow;
6. visualization workflow;
7. files to inspect first for debugging;
8. files/directories to avoid;
9. standard `nbody/runs/<run_name>/` layout.


## Mode: debug

Rules: start in Plan mode; do not edit files yet; no full simulations; no Docker rebuilds; no package installs; never open HDF5/snapshots/binaries/plots/archives/generated outputs.

Inspect only relevant small files, in this order:

1. `nbody/gizmo_test/run_gizmo.sh`;
2. parameter files: `nbody/gizmo_test/gizmo_cdm.param`, `nbody/gizmo_test/gizmo_sidm.param`, or a copied param;
3. runtime param if present: `.gizmo_run.param`;
4. build/config: `Config_cdm_sidm.sh`, `GizmoMakefile`, `Makefile.systype`;
5. IC generation scripts (`nbody/gizmo_test/generate_ics.sh`, `nbody/scripts/generate_ics.sh`);
6. relevant README files.

Deliver in Russian:

1. reconstruction of the current workflow;
2. likely failure points;
3. minimal diagnostic commands;
4. files that may need editing;
5. patch plan (do not apply yet).

Remember: `Config_cdm_sidm.sh` sets `DM_SIDM=8` (particle type 3). `nbody/gadget_test/run_gadget.sh` may reference stale `/workspace/...` paths — verify actual paths before running.

## Mode: generate-ic

Protocol:

1. Prepare or reuse a JSON config for `generate_ics.sh`.
2. Run: `bash /nbody/scripts/generate_ics.sh --config <path/to/config.json>`.
3. Verify output `nbody/ics/<run_name>/<run_name>.hdf5` exists (presence only, never open it).
4. Record the generated IC path in `llm/memory-bank/experimentLog.md`.
5. Optionally continue to Mode: run with `--ic-file` pointing at the new IC.

JSON config format:

```json
{
  "run_name": "my_cdm",
  "output_dir": "/nbody/ics/my_cdm",
  "galic_param": "nbody/GalIC/halo_nfw_ics.param",
  "components": [
    {"name": "dm", "n": 10000, "cc": 10, "v200": 200, "map_to": 3, "sigma": 0}
  ]
}
```

Top-level fields: `run_name` (unique IC set name), `output_dir` (absolute path inside `/nbody/ics/`), `galic_param` (GalIC template relative to `/nbody`; canonical template `nbody/GalIC/halo_nfw_ics.param`), `components` (array).

Component fields: `name` (required), `n` (required, particle count), `cc` (required, halo concentration), `v200` (required, circular velocity km/s), `map_to` (required, target PartType, e.g. 1 or 3; conversion handled by `merge_ics.py`/`convert_to_pt3.py`), `sigma` (optional, SIDM cross-section, informational only).

Do not generate large ICs without explicit confirmation. Keep GalIC source/binary under `/opt/GalIC`; never edit it.

## Mode: run

Extract parameters from the request:

- type: CDM or SIDM;
- particle number N (default 10000 if an IC exists for that N);
- SIDM cross-section sigma (default 10);
- IC source (default `/nbody/gizmo_test/halo_10000_sidm_ic`);
- simulation length TimeMax;
- optional visualization type (delegate to the make-plots skill afterwards);
- quick test vs production run.

If a parameter is missing, choose a conservative default and state the assumption explicitly.

Steps:

1. Start in Plan mode: confirm interpreted parameters with the user.
2. Verify the IC file/directory exists.
3. Build and SHOW the exact command before execution:

   ```bash
   bash /nbody/scripts/run_sim.sh \
     --name YYYYMMDD_descriptive_name \
     --type cdm|sidm \
     --time-max <T> \
     --sigma <SIGMA> \
     --ic-file <PATH>
   ```

4. For long runs (TimeMax > 1) ask explicit confirmation before starting.
5. Execute the wrapper.
6. Validate: read `run_dir/experiment.md` (full config + log) and `run_dir/snapshot_check.txt`. Check exit status and that snapshot files exist (names/sizes only, never open contents).
7. Telegram notifications are AUTOMATIC: `run_sim.sh` sends START/FINISH/ERROR to Telegram by default when `/nbody/tg/telegram.conf` exists — the agent must not pass any TG flags or send messages itself (opt-out only via `--no-tg`; periodic progress via `--tg-progress` or `--tg-interval <n>`).
8. Optionally visualize (`plot_scripts/run_full_test.py` or the make-plots skill).
9. Append a concise `experiment.md` summary to `llm/memory-bank/experimentLog.md`.

What `run_sim.sh` does internally (for reference): creates `nbody/runs/<name>/` with `configs/`, `output/`, `plots/` subdirs; copies template `.param` and `Config.sh` from `nbody/gizmo_test/`; patches only `InitCondFile`, `OutputDir`, `TimeMax`, `TimeBetSnapshot`, `SigmaSIDM`; preflight checks (IC exists, output dir free, binary ready, deps available); rebuilds GIZMO only if `Config.sh` changed (md5 check); runs `mpirun` with `tee run.log`; validates the last snapshot via `check_snapshot.py`; writes `experiment.md`.

Report in Russian: interpreted parameters; exact command; run status; output paths (run dir, log, snapshots); snapshot check summary; memory-bank update status.

## Hard safety rules (all modes)

- Never overwrite baseline config/param files; use isolated run folders under `nbody/runs/` only.
- Never edit anything under `/opt` (`gadget-2.0.7`, `gizmo-public`, `GalIC`) unless explicitly requested.
- Never open `.dat`/HDF5/snapshot/binary/graph/generated outputs unless explicitly requested.
- No long simulations, Docker rebuilds, or package installs without explicit user approval.
- Preserve physical consistency: particle number, mass resolution, gravitational softening, time-step parameters, output cadence, IC paths, unit conventions, and SIDM cross-section must be checked together.
- If a physical parameter is ambiguous, state the assumed convention and ask for confirmation if the ambiguity can change the result.
