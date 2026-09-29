#!/usr/bin/env python3
"""
loaders.py — минимальные адаптеры: HDF5 snapshots -> plot-ready данные.

Математика НЕ изменялась, перенесена дословно:

- prepare_profile_data() — расчёты из analyze_final_snapshot.py
  (shrinkage-центрирование, лог-биннинг 60 бинов от 0.05 kpc до p99.9,
  slope-окно 0.25 dex при >=3 бинах, sigma при >=10 частицах в бине,
  NInteractions в 12 лог-бинах при >=5 частицах);
- shrink_center() / prepare_series() — из analyze_final_snapshot.py и
  make_run_evolution.py.

Это единственное место нового plotting-слоя, знающее про физику подготовки
данных. NbodyPlotter и plots о ней ничего не знают.
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


# ───────────────────────────── чтение snapshot ──────────────────────────────

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

