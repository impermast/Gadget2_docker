---
name: check-run
description: Monitor, diagnose, summarize, and optionally Telegram-report existing GIZMO simulation runs using the reusable scripts in nbody/scripts/check_simulations/. Use when the user asks to check progress, health, ETA, timestep collapse, run integrity, completed-run summary, or a group/block of runs. Not for launching new simulations.
metadata:
  short-description: Reusable simulation monitoring/diagnostics
---

# Reusable Run Monitoring / Diagnostics Skill

## Preamble

1. Read `.clinerules/00-entrypoint.md` if present.
2. Read `llm/rules/` and `llm/memory-bank/` for current project state.
3. Communicate with the user in Russian.

## Purpose

`check-run` is a thin orchestration skill. It must not recreate ad-hoc grep/awk
checks every time. The canonical implementation lives in:

```text
/nbody/scripts/check_simulations/
```

Use these scripts to answer:

- симуляция ещё идёт: progress, health, simple ETA;
- непонятно, нормально ли всё: timestep/pathology/log/parameter diagnosis;
- симуляция завершена: integrity and concise summary;
- partial/pathological run: series diagnostics over all completed snapshots;
- группа прогонов: status table and compare-readiness.

## Canonical commands

Single run:

```bash
docker exec gadget-gizmo python3 /nbody/scripts/check_simulations/check_run.py \
  --run-root /nbody/runs/<run-or-group/run> \
  --mode auto \
  --format human
```

Group/block:

```bash
docker exec gadget-gizmo python3 /nbody/scripts/check_simulations/check_block.py \
  --group-root /nbody/runs/<group> \
  --format human
```

Telegram report plus console output:

```bash
docker exec gadget-gizmo python3 /nbody/scripts/check_simulations/check_run.py \
  --run-root /nbody/runs/<run> \
  --mode auto \
  --format tg
```

or:

```bash
docker exec gadget-gizmo python3 /nbody/scripts/check_simulations/check_block.py \
  --group-root /nbody/runs/<group> \
  --format tg
```

`--format tg` prints a compact Telegram-safe report to console and also sends
it through `/nbody/tg/tg_notify.py`. It must avoid wide tables because Telegram
wraps them poorly. Telegram failures are warnings, not fatal errors.

Machine-readable output is available for tooling:

```bash
--format json
```

Partial-series diagnostics for stopped/incomplete/pathological runs:

```bash
docker exec gadget-gizmo python3 /nbody/scripts/check_simulations/analyze_series.py \
  --run-root /nbody/runs/<run-or-group/run> \
  --outdir /nbody/runs/<run-or-group/run>/partial_analysis
```

This writes `metrics_series.csv`, `summary_partial_series.txt`, and static PNG
diagnostics. GIF/animation viewing must not be used as the agent's evidence;
agent verdicts must come from CSV/TXT metrics and static PNG file existence.

## Mode selection

`check_run.py` supports:

- `--mode auto` — default; infer running/diagnose/summary from process/log/state;
- `--mode monitor` — live progress and simple ETA;
- `--mode diagnose` — timestep/pathology/parameters/snapshot metadata;
- `--mode summary` — completed/incomplete summary and analysis readiness.

Prefer `auto` unless the user explicitly asks for one mode.

## What the reusable scripts check

The scripts collect only cheap/safe information:

1. run directory existence;
2. active `run_sim.sh` / `mpirun` / `GIZMO` processes;
3. `run.log` latest `Sync-Point`, `Time`, `Systemstep`;
4. latest occupied timebins and very small `dt` bins;
5. `run.state`, if available;
6. `.gizmo_run.param` and `output/parameters-usedvalues` selected parameters:
   - `TimeMax`, `TimeBetSnapshot`;
   - `DM_InteractionCrossSection`;
   - `DM_DissipationFactor`;
   - `DM_KickPerCollision`;
   - `DM_InteractionVelocityScale`;
7. snapshot count and expected count;
8. latest snapshot metadata and `NInteractions` summary only through the checker.
9. for partial series: shape/thickness/rotation/core-density/NInteractions/time-step
   evolution across all completed snapshots via `analyze_series.py`.

Do not manually open large snapshot arrays. The checker may read the small
`NInteractions` dataset of the latest snapshot for diagnostics; heavy profile
analysis remains in `plot_scripts/run_full_test.py`.

## Verdict semantics

The checker reports:

- `status`: `running`, `completed`, `failed`, `incomplete`, or `unknown`;
- `health`: `ok`, `degraded`, `pathological`, or `unknown`;
- `confidence`: `final` or `preliminary`;
- `flags`, e.g.:
  - `timestep-collapse`;
  - `small-systemstep`;
  - `syncpoint-runaway`;
  - `low-dt-timebins`;
  - `stalled-time-progress`.

Simple ETA is estimated from `run.state` elapsed minutes and `Time/TimeMax`.
If pathology is detected, ETA must be treated as unreliable.

## Reporting format to user

Answer in Russian and include:

1. exact command used;
2. checked path;
3. run status;
4. numerical health;
5. progress and ETA if available;
6. snapshot count / expected count;
7. key SIDM/dSIDM parameters;
8. `NInteractions` if available;
9. whether final analysis/compare plots are appropriate;
10. concise next action.

## Interaction with plotting

For incomplete/pathological runs where the user asks what happened dynamically,
prefer `analyze_series.py` before any final-only plotting. Its output directory
is normally:

```text
/nbody/runs/<run>/partial_analysis/
```

Use its `summary_partial_series.txt` and `metrics_series.csv` for scientific
judgement. Static contact-sheet PNGs are for qualitative human inspection;
do not claim conclusions from GIFs because the AI agent cannot inspect them.

If `check-run` says a run is complete and the user asks for plots/analysis, use
`make-plots` / `run_full_test.py`:

```bash
docker exec gadget-gizmo python3 /nbody/scripts/plot_scripts/run_full_test.py \
  --run-root /nbody/runs/<run>
```

For comparisons, only run `compare_runs.py` when all compared runs are complete
and non-pathological. Otherwise label any result as preliminary or skip compare.

## Safety

- Never stop or kill a simulation unless the user explicitly asks.
- Never delete run directories.
- Never launch new simulations from this skill.
- Never claim final physics from a running/incomplete/pathological run.
- Do not run heavy plotting/analysis automatically for incomplete runs.
