"""Deterministic synthetic HDF5 snapshot generator for tests.

Creates miniature snapshots whose structure exactly matches what
``nbody/scripts/plot_scripts/loaders.read_snapshot`` expects:

    Header/
        Time                        (float)
        DM_InteractionCrossSection  (float)
    PartType3/
        Coordinates   (n, 3)  float64
        Velocities    (n, 3)  float64
        Masses        (n,)    float64     [optional]
        NInteractions (n,)    uint64      [optional]

The default geometry is a UNIFORM sphere (radius ``R``, shifted center) so the
expected analytic answers are trivial:

- density profile flat          -> inner log-slope ~ 0
- known center                  -> shrink_center must recover it
- prescribed NInteractions      -> exact sums / fractions

All randomness goes through a fixed seed => byte-identical fixtures across runs
and machines (numpy>=1.17 PCG64).
"""

from __future__ import annotations

from pathlib import Path

import h5py
import numpy as np

# ─────────────────────────── canonical parameters ────────────────────────────
# Tests and make_golden.py MUST use these constants unchanged.

SEED = 42
N_PARTICLES = 2000
RADIUS = 10.0
CENTER = (10.0, 20.0, 30.0)
BULK_VELOCITY = (5.0, 0.0, 0.0)
PARTICLE_MASS = 1.0e-4
TIME = 0.5
SIGMA = 20.0
NI_COUNT = 100  # first NI_COUNT particles interact i+1 times (1..NI_COUNT)

MTOT = PARTICLE_MASS * N_PARTICLES  # 0.2
NI_TOTAL = NI_COUNT * (NI_COUNT + 1) // 2  # 5050


def generate_positions(n: int = N_PARTICLES, seed: int = SEED) -> np.ndarray:
    """Uniform-density ball of radius RADIUS around origin."""
    rng = np.random.default_rng(seed)
    dirs = rng.normal(size=(n, 3))
    dirs /= np.linalg.norm(dirs, axis=1, keepdims=True)
    radii = RADIUS * rng.random(n) ** (1.0 / 3.0)
    return dirs * radii[:, None]


def make_snapshot(path, *, n: int = N_PARTICLES, seed: int = SEED,
                  with_masses: bool = True, with_ni: bool = True,
                  time: float = TIME, sigma: float = SIGMA) -> Path:
    """Write one synthetic snapshot; returns the path."""
    pos = generate_positions(n=n, seed=seed) + np.asarray(CENTER)
    rng = np.random.default_rng(seed + 1)
    vel = rng.normal(size=(n, 3)) + np.asarray(BULK_VELOCITY)

    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with h5py.File(path, "w") as f:
        head = f.require_group("Header")
        head.attrs["Time"] = float(time)
        head.attrs["DM_InteractionCrossSection"] = float(sigma)
        g = f.require_group("PartType3")
        g.create_dataset("Coordinates", data=pos.astype(np.float64))
        g.create_dataset("Velocities", data=vel.astype(np.float64))
        if with_masses:
            g.create_dataset("Masses",
                             data=np.full(n, PARTICLE_MASS, dtype=np.float64))
        if with_ni:
            ni = np.zeros(n, dtype=np.uint64)
            k = min(NI_COUNT, n)
            ni[:k] = np.arange(1, k + 1, dtype=np.uint64)
            g.create_dataset("NInteractions", data=ni)
    return path


def make_snapshot_no_sigma_attr(path, **kwargs) -> Path:
    """Snapshot whose Header lacks DM_InteractionCrossSection.

    read_snapshot must fall back to sigma=0.0 via attrs.get(..., 0.0).
    """
    p = make_snapshot(path, **kwargs)
    with h5py.File(p, "r+") as f:
        del f["Header"].attrs["DM_InteractionCrossSection"]
    return p


def make_series(snapshot_dir, count: int = 11, n: int = N_PARTICLES,
                seed: int = SEED) -> Path:
    """A directory of numbered snapshots (snapshot_000 ... snapshot_{count-1})."""
    d = Path(snapshot_dir)
    for i in range(count):
        make_snapshot(d / f"snapshot_{i:03d}.hdf5",
                      n=n, seed=seed + i, time=float(i) * 0.1)
    return d
