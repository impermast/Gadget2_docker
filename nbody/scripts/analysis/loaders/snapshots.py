#!/usr/bin/env python3
"""snapshots — переезд из plot_scripts/loaders.py (математика дословно, см. этап 1).
Чтение снапшотов, центр (shrinkage), unresolved-радиус.
"""
from __future__ import annotations

import glob
import os
import re
from pathlib import Path
from typing import Dict, Optional, Sequence, Tuple

import h5py
import numpy as np

GYR_PER_CODE = 0.9777923542981722

UNRESOLVED_FACTOR = 2.0   # r_unresolved = factor * <softening kernel radius>_inner
UNRESOLVED_INNER_R = 1.0  # [kpc] внутри какого радиуса усредняем софтенинг

def read_snapshot(path, ptype: int = 3) -> Dict[str, Optional[np.ndarray]]:
    """Прочитать поля частиц и заголовок одного snapshot."""
    path = Path(path)
    with h5py.File(path, "r") as f:
        g = f[f"PartType{ptype}"]
        return {
            "pos": g["Coordinates"][:].astype(np.float64),
            "vel": g["Velocities"][:].astype(np.float64),
            "mass": (g["Masses"][:].astype(np.float64)
                     if "Masses" in g else None),
            "ni": (g["NInteractions"][:].astype(np.uint64)
                   if "NInteractions" in g else None),
            "softening": (g["Softening_KernelRadius"][:].astype(np.float64)
                          if "Softening_KernelRadius" in g else None),
            "time": float(f["Header"].attrs.get("Time", 0.0)),
            "sigma": float(f["Header"].attrs.get("DM_InteractionCrossSection", 0.0)),
        }


# ─────────────── зона ниже разрешения (софтенинг + релаксация) ───────────────

UNRESOLVED_FACTOR = 2.0   # r_unresolved = factor * <softening kernel radius>_inner
UNRESOLVED_INNER_R = 1.0  # [kpc] внутри какого радиуса усредняем софтенинг

def unresolved_radius(r: np.ndarray, softening: Optional[np.ndarray],
                      factor: float = UNRESOLVED_FACTOR,
                      r_inner: float = UNRESOLVED_INNER_R) -> Optional[float]:
    """Оценка радиуса, ниже которого профиль не разрешён.

    Берём медианный Softening_KernelRadius частиц внутри r_inner и умножаем на
    factor: профиль ненадёжен там, где r сравним с длиной смягчения силы.
    Возвращает None, если блок софтенинга отсутствует.
    """
    if softening is None:
        return None
    inner = r < r_inner
    sample = softening[inner] if inner.sum() >= 50 else softening
    if sample.size == 0:
        return None
    med = float(np.median(sample))
    if not np.isfinite(med) or med <= 0:
        return None
    return float(factor * med)



# ─────────────────────────── центрирование halo ─────────────────────────────

def shrink_center(pos: np.ndarray, mass: np.ndarray, niter: int = 10) -> np.ndarray:
    """Итеративный shrinkage-центр (не зависит от далёких эскаперов).
    Дословно из analyze_final_snapshot.py."""
    c = np.average(pos, axis=0, weights=mass)
    for _ in range(niter):
        rr = np.linalg.norm(pos - c, axis=1)
        ncut = max(100, int(0.10 * len(rr)))
        rcut = np.partition(rr, ncut - 1)[ncut - 1]
        mm = rr <= rcut
        c = np.average(pos[mm], axis=0, weights=mass[mm])
    return c

def _snapshot_number(path: str) -> int:
    m = re.search(r"snapshot_?(\d+)\.hdf5$", os.path.basename(path))
    return int(m.group(1)) if m else -1

def list_snapshots(snapshot_dir) -> list:
    files = sorted(glob.glob(os.path.join(str(snapshot_dir), "snapshot*.hdf5")),
                   key=_snapshot_number)
    if not files:
        raise FileNotFoundError(f"No HDF5 snapshots found in {snapshot_dir}")
    return files


# ──────────────────── подготовка radial-профилей (1 snapshot) ───────────────
