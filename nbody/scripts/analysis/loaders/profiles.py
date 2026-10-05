#!/usr/bin/env python3
"""profiles — переезд из plot_scripts/loaders.py (математика дословно, см. этап 1).
Радиальные профили (плотность/σ/NInteractions), сводка.
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

from .snapshots import (  # внутрипакетные связи (были одним модулем)
    UNRESOLVED_FACTOR,
    UNRESOLVED_INNER_R,
    list_snapshots,
    read_snapshot,
    shrink_center,
    unresolved_radius,
)

def prepare_profile_data(snapshot_path, rcore: float = 2.0) -> Dict[str, object]:
    """
    Рассчитать все стандартные radial-профили одного snapshot.
    Формулы дословно из analyze_final_snapshot.py.
    Возвращает dict для plots density / log_slope / sigma_v / interactions_radial.
    """
    d = read_snapshot(snapshot_path)
    center = shrink_center(d["pos"], d["mass"])
    pos = d["pos"] - center
    vel = d["vel"] - np.mean(d["vel"], axis=0)
    r = np.linalg.norm(pos, axis=1)
    mass = d["mass"]

    # --- профили (лог-биннинг) ---
    rmax = np.percentile(r[r > 0], 99.9)
    edges = np.logspace(np.log10(0.05), np.log10(max(rmax, 10)), 60)
    centers = np.sqrt(edges[:-1] * edges[1:])
    shell_m, _ = np.histogram(r, bins=edges, weights=mass)
    counts, _ = np.histogram(r, bins=edges)
    vol = 4.0 / 3.0 * np.pi * (edges[1:] ** 3 - edges[:-1] ** 3)
    rho = np.where(counts > 0, shell_m / vol, np.nan)

    valid = np.isfinite(rho) & (rho > 0) & (counts >= 5)
    lr, lrho = np.log10(centers), np.log10(np.where(rho > 0, rho, np.nan))
    slope = np.full_like(centers, np.nan)
    for i in np.where(valid)[0]:
        m = np.abs(lr - lr[i]) <= 0.25
        if m.sum() >= 3 and np.isfinite(lrho[m]).all():
            slope[i] = np.polyfit(lr[m], lrho[m], 1)[0]

    sv = np.full(len(centers), np.nan)
    for i in range(len(edges) - 1):
        mm = (r >= edges[i]) & (r < edges[i + 1])
        if mm.sum() >= 10:
            sv[i] = np.sqrt(np.mean(np.var(vel[mm], axis=0)))

    rho_core = float(mass[r < rcore].sum() / (4.0 / 3.0 * np.pi * rcore ** 3))

    # --- rot curve: v_circ(r) = sqrt(G * M(<r) / r) — в km/s ---------------
    # Единицы кода GIZMO: 1 кпк, 1e10 М_sun, 1 км/с → G_code ≈ 43009.2
    G_CODE = 43009.17
    m_enc = np.cumsum(shell_m)                       # масса внутри edges[i+1]
    m_enc_center = 0.5 * (np.concatenate([[0.0], m_enc[:-1]]) + m_enc)
    v_circ = np.sqrt(np.clip(G_CODE * m_enc_center / centers, 0.0, None))

    out = {
        "r": centers,
        "rho": rho,
        "slope": slope,
        "sigma_v": sv,
        "v_circ": v_circ,
        "time": float(d["time"]),
        "cross_section": float(d["sigma"]),
        "rho_core": rho_core,
        "core_radius": float(rcore),
    }

    # --- зона ниже разрешения (софтенинг + релаксация) ---
    r_unres = unresolved_radius(r, d.get("softening"))
    if r_unres is not None:
        out["unresolved_r_max"] = r_unres
        out["softening_kernel_median"] = float(
            np.median(d["softening"][r < UNRESOLVED_INNER_R])
            if (r < UNRESOLVED_INNER_R).sum() >= 50 else np.median(d["softening"]))

    # --- NInteractions ---
    if d["ni"] is not None:
        ni = d["ni"]
        nb = 12
        redges = np.logspace(np.log10(max(r[r > 0].min(), 0.05)),
                             np.log10(rmax), nb + 1)
        rcenters = np.sqrt(redges[:-1] * redges[1:])
        ni_mean_bin = np.full(nb, np.nan)
        frac_bin = np.full(nb, np.nan)
        for i in range(nb):
            mm = (r >= redges[i]) & (r < redges[i + 1])
            if mm.sum() >= 5:
                ni_mean_bin[i] = ni[mm].mean()
                frac_bin[i] = 100.0 * (ni[mm] > 0).sum() / mm.sum()
        out["r_ni"] = rcenters
        out["ni_mean"] = ni_mean_bin
        out["ni_frac"] = frac_bin
    return out


# ────────────────── подготовка series частиц (анимации) ─────────────────────

def inner_log_slope(slope: np.ndarray, rho: np.ndarray, r: np.ndarray,
                    n_first: int = 6) -> float:
    """Медиана первых валидных бинов slope (как в analyze_final_snapshot.py)."""
    valid = np.isfinite(slope) & np.isfinite(rho) & (rho > 0) & (r > 0)
    first = [slope[i] for i in np.where(valid)[0]][:n_first]
    return float(np.median(first)) if first else float("nan")

def write_summary(snapshot_path, out_path, rcore: float = 2.0) -> str:
    """
    Текстовая сводка по финальному snapshot (формат дословно из
    analyze_final_snapshot.py). Пишет файл, возвращает текст.
    """
    d = read_snapshot(snapshot_path)
    center = shrink_center(d["pos"], d["mass"])
    pos = d["pos"] - center
    vel = d["vel"] - np.mean(d["vel"], axis=0)
    r = np.linalg.norm(pos, axis=1)
    mass = d["mass"]
    t, sig_cs = d["time"], d["sigma"]

    com_all = np.sum(d["pos"] * d["mass"][:, None], axis=0) / d["mass"].sum()

    lines = [f"Snapshot: {snapshot_path}",
             f"Time: {t:.4f}   CrossSection: {sig_cs}",
             f"Particles: {len(r)}   Mtot={mass.sum():.4e}",
             "COM(all): ({:.3f}, {:.3f}, {:.3f})".format(*com_all),
             "Shrink-center: ({:.3f}, {:.3f}, {:.3f})".format(*center)]

    rmax = np.percentile(r[r > 0], 99.9)
    edges = np.logspace(np.log10(0.05), np.log10(max(rmax, 10)), 60)
    centers = np.sqrt(edges[:-1] * edges[1:])
    shell_m, _ = np.histogram(r, bins=edges, weights=mass)
    counts, _ = np.histogram(r, bins=edges)
    vol = 4.0 / 3.0 * np.pi * (edges[1:] ** 3 - edges[:-1] ** 3)
    rho = np.where(counts > 0, shell_m / vol, np.nan)

    valid = np.isfinite(rho) & (rho > 0) & (counts >= 5)
    lr, lrho = np.log10(centers), np.log10(np.where(rho > 0, rho, np.nan))
    slope = np.full_like(centers, np.nan)
    for i in np.where(valid)[0]:
        m = np.abs(lr - lr[i]) <= 0.25
        if m.sum() >= 3 and np.isfinite(lrho[m]).all():
            slope[i] = np.polyfit(lr[m], lrho[m], 1)[0]

    rho_core = mass[r < rcore].sum() / (4.0 / 3.0 * np.pi * rcore ** 3)
    inner_slope = inner_log_slope(slope, rho, centers)
    lines.append(f"Core density (r<{rcore}): {rho_core:.4e}")
    lines.append(f"Inner log-slope (median first bins): {inner_slope:.3f}")

    lines.append("")
    if d["ni"] is not None:
        ni = d["ni"]
        tot = int(ni.sum())
        nz = int((ni > 0).sum())
        lines.append(f"NInteractions TOTAL: {tot}")
        lines.append(f"Particles interacted: {nz}/{len(ni)} ({100 * nz / len(ni):.2f}%)")
        if nz:
            nn = ni[ni > 0].astype(float)
            lines.append(f"Per-interacted: mean={nn.mean():.2f} "
                         f"median={np.median(nn):.0f} "
                         f"p90={np.percentile(nn, 90):.0f} max={int(nn.max())}")
    else:
        lines.append("NInteractions: NOT IN SNAPSHOT")

    txt = "\n".join(lines)
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(txt + "\n")
    print(f"  → {out_path}")
    return txt
