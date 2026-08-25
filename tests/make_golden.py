#!/usr/bin/env python3
"""Regenerate tests/golden/values.json (answer-testing pattern, cf. yt).

Run deliberately ONLY when loaders.py math changed on purpose:

    .venv/bin/python tests/make_golden.py

Then record the reason for regeneration in tests/golden/README.md.
The fixture is the deterministic synthetic snapshot from synth_snap.py,
so golden values are cheap to recompute (<1 s) and machine-independent.
"""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path

TESTS_DIR = Path(__file__).resolve().parent
REPO_ROOT = TESTS_DIR.parent
PLOT_SCRIPTS_DIR = REPO_ROOT / "nbody" / "scripts" / "plot_scripts"
for p in (str(PLOT_SCRIPTS_DIR), str(TESTS_DIR)):
    if p not in sys.path:
        sys.path.insert(0, p)

import loaders  # noqa: E402
import numpy as np  # noqa: E402

import synth_snap  # noqa: E402

GOLDEN_PATH = TESTS_DIR / "golden" / "values.json"


def compute_metrics(snapshot_path) -> dict:
    """All quantities tracked by test_golden.py. Keep in sync with it."""
    d = loaders.read_snapshot(snapshot_path)
    center = loaders.shrink_center(d["pos"], d["mass"])
    prof = loaders.prepare_profile_data(snapshot_path)
    inner = loaders.inner_log_slope(prof["slope"], prof["rho"], prof["r"])

    ni = d["ni"]
    nn = ni[ni > 0].astype(float)

    return {
        "shrink_center": [float(v) for v in center],
        "mtot": float(d["mass"].sum()),
        "time": float(d["time"]),
        "sigma": float(d["sigma"]),
        "rho_core_r2": float(prof["rho_core"]),
        "inner_log_slope": float(inner),
        "ni_total": int(ni.sum()),
        "ni_nonzero": int((ni > 0).sum()),
        "ni_nonzero_pct": float(100.0 * (ni > 0).sum() / len(ni)),
        "ni_mean_interacted": float(nn.mean()),
        "ni_median_interacted": float(np.median(nn)),
        "ni_p90_interacted": float(np.percentile(nn, 90)),
        "ni_max_interacted": int(nn.max()),
    }


def main() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        snap = synth_snap.make_snapshot(Path(tmp) / "snapshot_final.hdf5")
        metrics = compute_metrics(snap)

    commit = subprocess.run(["git", "rev-parse", "HEAD"], cwd=REPO_ROOT,
                            capture_output=True, text=True).stdout.strip()
    payload = {
        "_provenance": {
            "generator_module": "tests/synth_snap.py",
            "seed": synth_snap.SEED,
            "n_particles": synth_snap.N_PARTICLES,
            "git_commit_at_generation": commit,
            "note": "regenerate only when loaders math changes deliberately",
        },
        **metrics,
    }
    GOLDEN_PATH.write_text(json.dumps(payload, indent=2) + "\n")
    print(f"golden values written: {GOLDEN_PATH}")
    print(json.dumps(metrics, indent=2))


if __name__ == "__main__":
    main()
