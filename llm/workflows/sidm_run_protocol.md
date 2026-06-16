# GIZMO Run Protocol (CDM/SIDM)

## Canonical tool

**Use `bash /nbody/scripts/run_sim.sh`** — do NOT manually copy/param-patch/sed/mpirun.

## Protocol

1. Interpret user request (sim type, N, sigma, time, IC).
2. Verify IC file exists.
3. Construct the `run_sim.sh` command.
4. Show command to the user before execution.
5. For long runs (TimeMax > 1), ask explicit confirmation.
6. Execute the wrapper.
7. Review `run_dir/experiment.md` and `run_dir/snapshot_check.txt`.
8. Optionally run visualization (`analyze_halo.py`, `png_to_gif.py`, etc.).
9. Append `run_dir/experiment.md` to `llm/memory-bank/experimentLog.md`.

## Example

```bash
bash /nbody/scripts/run_sim.sh \
  --name 20260616_sidm_sigma10_N10000 \
  --type sidm \
  --time-max 5.0 \
  --sigma 10 \
  --ic-file /nbody/gizmo_test/halo_10000_sidm_ic
```

## What the wrapper does (for reference)

- Creates `nbody/runs/<name>/` with `configs/`, `output/`, `plots/` subdirs
- Copies template `.param` and `Config.sh` from `nbody/gizmo_test/`
- Patches only: `InitCondFile`, `OutputDir`, `TimeMax`, `TimeBetSnapshot`, `SigmaSIDM`
- Preflight check: IC exists, output dir free, binary ready, deps available
- Rebuilds GIZMO only if `Config.sh` changed (md5 check)
- Runs `mpirun` with `tee run.log`
- Validates last snapshot via `check_snapshot.py`
- Writes `experiment.md` with full config
