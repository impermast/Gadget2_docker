# Golden values (answer testing)

`values.json` contains reference metrics of the analysis pipeline
(`nbody/scripts/plot_scripts/loaders.py`) computed on the deterministic
synthetic snapshot from `tests/synth_snap.py` (uniform sphere, seed=42,
N=2000). Pattern borrowed from the yt project's answer testing.

## Rules

- Golden values are regenerated ONLY deliberately:
      .venv/bin/python tests/make_golden.py
- Every regeneration MUST be documented here:

| Date       | Commit | Reason for regeneration                  |
|------------|--------|------------------------------------------|
| 2026-08-25 | (see values.json `_provenance`) initial generation |

## Why synthetic instead of real runs?

Real snapshots are huge (N=1e6, HDF5, gitignored) and slow to analyze.
The synthetic fixture has exact analytic answers (flat profile -> slope 0,
known center, prescribed NInteractions), so any divergence in loaders math
is caught in seconds without touching simulation data.
