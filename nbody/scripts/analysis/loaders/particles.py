#!/usr/bin/env python3
"""particles — переезд из plot_scripts/loaders.py (математика дословно, см. этап 1).
Частицы/серии/морфология/фазовое пространство для карт и анимаций.
"""
from __future__ import annotations

import glob
import os
import re
from pathlib import Path
from typing import Dict, Optional, Sequence, Tuple

import h5py
import numpy as np

from .snapshots import (  # были одним модулем
    _snapshot_number,
    list_snapshots,
    read_snapshot,
    shrink_center,
)

GYR_PER_CODE = 0.9777923542981722

def prepare_series(snapshot_dir, ptype: int = 3, nmax: int = 100_000,
                   max_frames: Optional[int] = None, seed: int = 42):
    """
    Загрузить серию snapshot'ов для анимаций.

    Возвращает dict с plot-ready данными:
      positions (T, N, 3) float32 — уже shrinkage-центрированы по каждому кадру;
      masses    (T, N,)   float32 | None;
      times     (T,)      кодовое время;
      snapshot_numbers (T,)
    Кадры равномерно прореживаются до max_frames; частицы случайно
    сэмплуются до nmax на кадр (как в старых скриптах).
    """
    rng = np.random.default_rng(seed)
    files = list_snapshots(snapshot_dir)
    if max_frames and len(files) > max_frames:
        idx = np.round(np.linspace(0, len(files) - 1, max_frames)).astype(int)
        files = [files[i] for i in idx]

    pos_list, mass_list, times, numbers = [], [], [], []
    for fp in files:
        with h5py.File(fp, "r") as f:
            g = f[f"PartType{ptype}"]
            pos = g["Coordinates"][:].astype(np.float64)
            mass = (g["Masses"][:].astype(np.float64)
                    if "Masses" in g else None)
            t = float(f["Header"].attrs.get("Time", 0.0))
        w = mass if mass is not None else np.ones(len(pos))
        c = shrink_center(pos, w, niter=6)  # как в make_run_evolution.py
        pos -= c
        if nmax and len(pos) > nmax:
            sel = rng.choice(len(pos), nmax, replace=False)
            pos = pos[sel]
            mass = mass[sel] if mass is not None else None
        pos_list.append(pos.astype(np.float32))
        mass_list.append(mass.astype(np.float32) if mass is not None else None)
        times.append(t)
        numbers.append(_snapshot_number(fp))

    masses = (np.stack(mass_list) if all(m is not None for m in mass_list)
              else None)
    return {
        "positions": np.stack(pos_list),
        "masses": masses,
        "times": np.asarray(times, dtype=float),
        "snapshot_numbers": np.asarray(numbers, dtype=int),
    }


# ─────────────────────── текстовая сводка прогона ───────────────────────────

def prepare_particle_snapshot(snapshot_path, ptype: int = 3, nmax: int = None,
                              seed: int = 42) -> Dict[str, object]:
    """
    Plot-ready частицы финального снапшота (для карт disk_edgeon и т.п.):
    positions (N, 3) — shrinkage-центрированы, masses (N,), time, cross_section.
    """
    d = read_snapshot(snapshot_path, ptype=ptype)
    pos = d["pos"]
    mass = d["mass"] if d["mass"] is not None else np.full(len(pos), 1.0)
    center = shrink_center(pos, mass, niter=6)
    pos = pos - center
    if nmax and len(pos) > nmax:
        sel = np.random.default_rng(seed).choice(len(pos), nmax, replace=False)
        pos, mass = pos[sel], mass[sel]
    return {
        "positions": pos.astype(np.float32),
        "masses": mass.astype(np.float32),
        "time": float(d["time"]),
        "cross_section": float(d["sigma"]),
    }


# ──────────────── Hopkins/FIRE-style visual morphology helpers ───────────────

def prepare_visual_snapshot(snapshot_path, ptype: int = 3,
                            nmax: int = None, seed: int = 42) -> Dict[str, object]:
    """Plot-ready centered particles plus velocities for morphology packages.

    Это расширение использует тот же shrinkage-center, что и стандартные plots.
    Возвращает позиции/скорости/массы/NInteractions; сами concrete plots HDF5 не
    читают. Velocities центрируются вычитанием среднего, как в profile-loader.
    """
    d = read_snapshot(snapshot_path, ptype=ptype)
    pos0 = d["pos"]
    vel0 = d["vel"]
    mass = d["mass"] if d["mass"] is not None else np.full(len(pos0), 1.0)
    center = shrink_center(pos0, mass, niter=6)
    pos = pos0 - center
    vel = vel0 - np.mean(vel0, axis=0)
    ni = d["ni"]
    if nmax and len(pos) > nmax:
        sel = np.random.default_rng(seed).choice(len(pos), nmax, replace=False)
        pos, vel, mass = pos[sel], vel[sel], mass[sel]
        ni = ni[sel] if ni is not None else None
    return {
        "positions": pos.astype(np.float32),
        "velocities": vel.astype(np.float32),
        "masses": mass.astype(np.float32),
        "ninteractions": ni.astype(np.float64) if ni is not None else None,
        "time": float(d["time"]),
        "cross_section": float(d["sigma"]),
        "snapshot": str(snapshot_path),
    }

def projection_histograms(snapshot: Dict[str, object], bins: int = 220,
                          lim: float = 12.0) -> Tuple[np.ndarray, np.ndarray]:
    """Mass-weighted surface-density histograms in face-on xy and edge-on xz."""
    pos = np.asarray(snapshot["positions"], dtype=float)
    mass = np.asarray(snapshot["masses"], dtype=float)
    rng = [[-lim, lim], [-lim, lim]]
    hxy, _, _ = np.histogram2d(pos[:, 0], pos[:, 1], bins=bins, range=rng,
                               weights=mass)
    hxz, _, _ = np.histogram2d(pos[:, 0], pos[:, 2], bins=bins, range=rng,
                               weights=mass)
    return hxy.T.astype(np.float32), hxz.T.astype(np.float32)

def phase_space_histogram(snapshot: Dict[str, object], rlim: float = 12.0,
                          vlim: Optional[float] = None,
                          bins_r: int = 180, bins_v: int = 180) -> Tuple[np.ndarray, Tuple[float, float, float, float]]:
    """Mass-weighted cylindrical phase-space histogram: R vs v_phi."""
    pos = np.asarray(snapshot["positions"], dtype=float)
    vel = np.asarray(snapshot["velocities"], dtype=float)
    mass = np.asarray(snapshot["masses"], dtype=float)
    R = np.linalg.norm(pos[:, :2], axis=1)
    ok = R > 1e-8
    vphi = np.zeros(len(pos), dtype=float)
    vphi[ok] = (-pos[ok, 1] * vel[ok, 0] + pos[ok, 0] * vel[ok, 1]) / R[ok]
    if vlim is None:
        finite = np.isfinite(vphi)
        vlim = max(20.0, float(np.percentile(np.abs(vphi[finite]), 99.0))) if np.any(finite) else 50.0
    rng = [[0.0, rlim], [-vlim, vlim]]
    hist, _, _ = np.histogram2d(R, vphi, bins=[bins_r, bins_v], range=rng,
                                weights=mass)
    return hist.T.astype(np.float32), (0.0, rlim, -float(vlim), float(vlim))

def radial_morphology_profiles(snapshot: Dict[str, object],
                               radii: Sequence[float]) -> Dict[str, np.ndarray]:
    """Cumulative morphology/kinematic profiles on fixed radii.

    Возвращает b/a, c/a, z_rms/R_rms, <v_phi>, sigma components and
    |v_phi|/sigma_3d. Это тот же смысл метрик, что в check_simulations, но как
    финальный radial profile для презентационных сравнений.
    """
    pos = np.asarray(snapshot["positions"], dtype=float)
    vel = np.asarray(snapshot["velocities"], dtype=float)
    mass = np.asarray(snapshot["masses"], dtype=float)
    r3 = np.linalg.norm(pos, axis=1)
    R = np.linalg.norm(pos[:, :2], axis=1)
    out = {k: np.full(len(radii), np.nan, dtype=float) for k in [
        "ba", "ca", "thickness", "mean_vphi", "sigma_R", "sigma_phi",
        "sigma_z", "vrot_over_sigma", "interacted_fraction"]}
    ni = snapshot.get("ninteractions")
    for i, radius in enumerate(radii):
        m = r3 < radius
        if int(m.sum()) < 20:
            continue
        x = pos[m]
        w = mass[m]
        cov = (x * w[:, None]).T @ x / np.sum(w)
        vals = np.sort(np.clip(np.linalg.eigvalsh(cov), 0.0, None))[::-1]
        if vals[0] > 0:
            axes = np.sqrt(vals)
            out["ba"][i] = axes[1] / axes[0]
            out["ca"][i] = axes[2] / axes[0]
        z_rms = np.sqrt(np.average(pos[m, 2] ** 2, weights=w))
        R_rms = np.sqrt(np.average(R[m] ** 2, weights=w))
        out["thickness"][i] = z_rms / R_rms if R_rms > 0 else np.nan
        km = m & (R > 1e-8)
        if int(km.sum()) >= 20:
            xk, yk = pos[km, 0], pos[km, 1]
            vx, vy, vz = vel[km, 0], vel[km, 1], vel[km, 2]
            Rk = R[km]
            vphi = (-yk * vx + xk * vy) / Rk
            vR = (xk * vx + yk * vy) / Rk
            out["mean_vphi"][i] = np.mean(vphi)
            out["sigma_R"][i] = np.std(vR)
            out["sigma_phi"][i] = np.std(vphi)
            out["sigma_z"][i] = np.std(vz)
            sigma_3d = np.sqrt(np.var(vR) + np.var(vphi) + np.var(vz))
            out["vrot_over_sigma"][i] = abs(np.mean(vphi)) / sigma_3d if sigma_3d > 0 else np.nan
        if ni is not None:
            out["interacted_fraction"][i] = np.count_nonzero(np.asarray(ni)[m] > 0) / int(m.sum())
    out["radii"] = np.asarray(radii, dtype=float)
    return out


# ─────────────────── time-series метрики (для DIAG-панелей) ────────────────

def load_metrics_series(csv_path) -> Dict[str, np.ndarray]:
    """
    Прочитать metrics_series.csv, созданный check_simulations/analyze_series.py,
    в dict numpy-массивов (ключи = имена колонок CSV).

    Контракт полей (см. analyze_series.SeriesMetric):
      time, c/a, z_rms/R_rms, vrot/sigma, ninteractions_total,
      nearest_systemstep и т.д. — все как float64 numpy массивы.
    """
    import csv

    csv_path = Path(csv_path)
    with csv_path.open("r", newline="") as fh:
        reader = csv.DictReader(fh)
        rows = list(reader)
    if not rows:
        return {}
    columns = {key: [] for key in rows[0].keys()}
    for row in rows:
        for key in columns:
            columns[key].append(row.get(key, ""))
    out: Dict[str, np.ndarray] = {}
    for key, vals in columns.items():
        arr = np.asarray(vals, dtype=object)
        try:
            out[key] = arr.astype(np.float64)
        except (ValueError, TypeError):
            out[key] = arr
    return out

def interacted_kinetic_energy(snapshot_payload: Dict[str, object]) -> float:
    """
    Суммарная кинетическая энергия частиц, которые хоть раз взаимодействовали
    (NInteractions > 0), в системе отсчёта bulk-скорости. Используется диаг-
    графиком diag_eloss_vs_f: relative loss = (K_elastic - K_dissip)/K_elastic.

    snapshot_payload — результат prepare_visual_snapshot():
        velocities (N,3) уже ипс-centered (bulk вычтен), masses (N,), ninteractions.
    """
    vel = np.asarray(snapshot_payload["velocities"], dtype=np.float64)
    mass = np.asarray(snapshot_payload["masses"], dtype=np.float64)
    ni = snapshot_payload.get("ninteractions")
    if ni is None:
        return float("nan")
    mask = np.asarray(ni) > 0
    if not np.any(mask):
        return 0.0
    v = vel[mask]
    m = mass[mask]
    return float(0.5 * float(np.sum(m * np.sum(v * v, axis=1))))
