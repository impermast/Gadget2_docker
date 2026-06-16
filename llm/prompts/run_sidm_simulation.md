# Prompt: run controlled GIZMO simulation (CDM/SIDM)

Read `.clinerules/00-entrypoint.md`, then read all required files from `llm/rules/` and `llm/memory-bank/`.

Task:

Create and run a controlled GIZMO simulation (CDM or SIDM) based on existing initial conditions using the unified run wrapper.

The canonical tool is `bash /nbody/scripts/run_sim.sh`. Do NOT manually copy/param-patch/compile — use the wrapper.

User parameters:

- particle number: `<N>` (default 10000 if IC exists for that N)
- simulation type: CDM or SIDM
- SIDM cross-section (if SIDM): `<sigma>` (default 10)
- initial condition source: `<IC_SOURCE>` (default `/nbody/gizmo_test/halo_10000_sidm_ic`)
- simulation length: `<TIME>` (use `--time-max <t>`)
- visualization: `<VIS_TYPE>`

Workflow:

1. Plan mode: confirm parameters with the user (interpreting their request).
2. Check that the IC file exists.
3. Run the simulation with the wrapper:
   ```bash
   bash /nbody/scripts/run_sim.sh \
     --name YYYYMMDD_descriptive_name \
     --type cdm|sidm \
     --time-max <T> \
     --sigma <SIGMA> \
     --ic-file <PATH>
   ```
4. After completion, check `run_dir/experiment.md` for the log and `run_dir/snapshot_check.txt` for validation.
5. Optionally run visualization (e.g. `analyze_halo.py` or `png_to_gif.py`).
6. Append `run_dir/experiment.md` to `llm/memory-bank/experimentLog.md`.

Rules:

- Work in Russian when explaining.
- Start in Plan mode.
- **Do NOT manually copy/edit param/config files** — let `run_sim.sh` handle that.
- Do not edit files under `/opt`.
- Do not open HDF5/snapshot/binary files unless explicitly needed.
- Show the exact `run_sim.sh` command before execution.
- For long runs (TimeMax > 1), ask explicit confirmation.
- After completion, show paths: run directory, log, snapshot check result.

Expected output:

1. interpreted parameters;
2. exact `run_sim.sh` command;
3. run status;
4. output paths (run dir, log, snapshots);
5. snapshot check summary;
6. memory-bank update summary.
