#!/usr/bin/env python3
"""loaders/ic.py — метрики IC-gate (математика дословно из check_ic_cusp.py).

Рисования здесь НЕТ (это plots/ic.py): модуль считает target-профиль из
фактического вывода GalIC (rotcurve.txt + NFW-фит), измеренный профиль IC,
локальные наклоны, разрешение бинов и t_relax (Power et al. 2003).

Главная точка входа — run_ic_gate(): возвращает dict метрик и пишет
ic_gate_report.txt / ic_gate.json / ic_profiles.csv в outdir.
"""

from __future__ import annotations

import glob
import json
import math
import os
from typing import Dict, Optional, Tuple

import h5py
import numpy as np

G_CODE = 4.301e4        # kpc (km/s)^2 / (1e10 Msun)
TIME_UNIT_GYR = 0.9778  # 1 kpc/(km/s) -> Gyr


def find_galic_dir(ic_path, explicit=None):
    """Каталог с фактическим выводом GalIC (rotcurve.txt, param_*.param)."""
    if explicit:
        return explicit if os.path.isdir(explicit) else None
    cands = []
    ic_dir = os.path.dirname(os.path.abspath(ic_path))
    for pat in (os.path.join(ic_dir, "galic_*"), ic_dir, os.path.join(ic_dir, "..")):
        cands.extend(glob.glob(pat))
    for c in cands:
        if os.path.isfile(os.path.join(c, "rotcurve.txt")):
            return c
    return None


def read_galic_params(galic_dir):
    """CC / V200 из фактического param-файла GalIC."""
    out = {}
    if not galic_dir:
        return out
    for p in glob.glob(os.path.join(galic_dir, "param*.param")):
        with open(p, "r", errors="ignore") as fh:
            for line in fh:
                parts = line.split()
                if len(parts) >= 2:
                    if parts[0] == "CC":
                        out["CC"] = float(parts[1])
                    elif parts[0] == "V200":
                        out["V200"] = float(parts[1])
    return out


def read_rotcurve(galic_dir):
    """Target rotation curve GalIC: (r [kpc], v_circ [km/s])."""
    path = os.path.join(galic_dir, "rotcurve.txt")
    rows = []
    with open(path, "r") as fh:
        fh.readline()  # первая строка — число точек
        for line in fh:
            parts = line.split()
            if len(parts) >= 2:
                try:
                    rows.append((float(parts[0]), float(parts[1])))
                except ValueError:
                    continue
    arr = np.array(rows)
    r, v = arr[:, 0], arr[:, 1]
    ok = (r > 0) & (v > 0)
    return r[ok], v[ok]


def target_profile_from_rotcurve(r_t, v_t):
    """M_target(<r) и rho_target(r) из rotcurve (self-consistent в units кода)."""
    m_t = v_t**2 * r_t / G_CODE                      # 1e10 Msun
    rho = np.full_like(r_t, np.nan)
    for i in range(1, len(r_t) - 1):
        dM = m_t[i + 1] - m_t[i - 1]
        dV = (4.0 / 3.0) * np.pi * (r_t[i + 1] ** 3 - r_t[i - 1] ** 3)
        if dV > 0:
            rho[i] = dM / dV
    return m_t, rho


def fit_nfw_to_rotcurve(r_t, v_t):
    """NFW-фит (rho_s, r_s) к фактической rotcurve GalIC (по v_circ^2).

    Только справочно: для чеков НЕ используется (см. rho_target_in_bins).
    Рецепт дословно из check_ic_cusp.py: сетка r_s, amp по МНК, rms(v^2).
    Возвращает (rho_s, r_s, rms).
    """
    r_s_grid = np.logspace(np.log10(max(r_t[0] / 50.0, 1e-3)),
                           np.log10(r_t[-1] * 2.0), 600)
    best = (None, None, np.inf)
    for r_s in r_s_grid:
        x = r_t / r_s
        shape = (np.log(1 + x) - x / (1 + x)) / x          # v^2/(4 pi G rho_s r_s^2)
        denom = float(np.sum(shape**2))
        if denom <= 0:
            continue
        amp = float(np.sum(shape * v_t**2)) / denom        # 4 pi G rho_s r_s^2
        if amp <= 0:
            continue
        rms = float(np.sqrt(np.mean((v_t**2 - amp * shape) ** 2)))
        if rms < best[2]:
            best = (amp / (4 * np.pi * G_CODE * r_s**2), r_s, rms)
    rho_s, r_s, rms = best
    return rho_s, r_s, rms


def rho_nfw(r, rho_s, r_s):
    x = r / r_s
    return rho_s / (x * (1.0 + x) ** 2)


def slope_nfw(r, r_s):
    x = r / r_s
    return -(1.0 + 3.0 * x) / (1.0 + x)


def read_ic_state(path):
    """Позиции/массы (PartType3 или 1) + r от COM (невзвешенного среднего).

    Дословно read_particles() из check_ic_cusp.py: именно невзвешенное
    среднее (np.mean) — это центр, от которого строятся r в гейте.
    Возвращает (r, mass, pos, com, hdr) в том же порядке, что оригинал.
    """
    with h5py.File(path, "r") as f:
        key = "PartType3" if "PartType3" in f else (
            "PartType1" if "PartType1" in f else None)
        if key is None:
            raise RuntimeError("нет PartType3/PartType1 в %s" % path)
        g = f[key]
        pos = g["Coordinates"][:]
        mass = g["Masses"][:] if "Masses" in g else np.full(len(pos), 1.0)
        hdr = dict(f["Header"].attrs)
    com = np.mean(pos, axis=0)
    r = np.linalg.norm(pos - com, axis=1)
    return r, mass, pos, com, hdr


def potential_energy_from_rotcurve(r_t, v_t, g=G_CODE):
    """W = -G * int M(r) dM / r для профиля, заданного rotcurve GalIC."""
    m_t = v_t**2 * r_t / g
    dm = np.diff(m_t)
    r_mid = 0.5 * (r_t[1:] + r_t[:-1])
    m_mid = 0.5 * (m_t[1:] + m_t[:-1])
    return float(-g * np.sum(m_mid * dm / r_mid))


def local_slope(r, rho, window_dex=0.25, min_bins=3):
    """Локальный d log rho / d log r в скользящем окне (как в loaders.py)."""
    lr, lrho = np.log10(r), np.log10(np.where(rho > 0, rho, np.nan))
    slope = np.full_like(r, np.nan)
    for i in range(len(r)):
        m = np.abs(lr - lr[i]) <= window_dex
        m &= np.isfinite(lrho)
        if m.sum() >= min_bins:
            slope[i] = np.polyfit(lr[m], lrho[m], 1)[0]
    return slope


def binned_profile(r, mass, rmin, rmax, nbins=60):
    """Профиль по готовым радиусам r (dosловно из check_ic_cusp.py).

    Возвращает (centers, rho, counts, edges) — edges нужны для target
    по тем же границам бинов (rho_target_in_bins).
    """
    edges = np.logspace(np.log10(rmin), np.log10(rmax), nbins + 1)
    vol = (4.0 / 3.0) * np.pi * np.diff(edges**3)
    idx = np.digitize(r, edges) - 1
    ok = (idx >= 0) & (idx < len(vol))
    cnt = np.bincount(idx[ok], minlength=len(vol))
    mm = np.bincount(idx[ok], weights=mass[ok], minlength=len(vol))
    with np.errstate(divide="ignore", invalid="ignore"):
        rho = np.where(vol > 0, mm / vol, np.nan)
    centers = np.sqrt(edges[1:] * edges[:-1])
    return centers, rho, cnt, edges


def t_relax_gyr(n_in, m_in, r):
    """t_relax ~ 0.1 * N/lnN * t_orb (Power et al. 2003), в Gyr."""
    if n_in < 20:
        return float("nan")
    v_c = np.sqrt(G_CODE * m_in / r)
    t_orb = 2.0 * np.pi * r / v_c
    return 0.1 * n_in / np.log(n_in) * t_orb * TIME_UNIT_GYR


def rho_target_in_bins(r_t, v_t, edges, g=G_CODE):
    """Целевая плотность GalIC по границам бинов: dM_target/dV.

    M_target(<r) берётся напрямую из rotcurve (v^2 r / G), без NFW-фита,
    чтобы сравнение шло с фактическим target-профилем GalIC.
    Дословно из check_ic_cusp.py (рецепт коммита ca0d430).
    """
    m_t = v_t**2 * r_t / g
    m_edges = np.interp(edges, r_t, m_t)
    vol = (4.0 / 3.0) * np.pi * np.diff(edges**3)
    return np.diff(m_edges) / vol

def run_ic_gate(ic_path, galic_dir=None, outdir=".", nmin=200,
                rlo=0.3, rhi=3.0) -> Dict:
    """IC-gate целиком: метрики + ic_gate_report.txt/json + ic_profiles.csv.

    Рецепт main() из check_ic_cusp.py дословно (сетка r_min–20 кпк,
    60 бинов; target — rotcurve напрямую по тем же границам бинов;
    slope — local_slope скользящим окном; N(<r)/M(<r)/t_relax — маской r<rr).
    РИСОВАНИЯ НЕТ — графики по ic_profiles.csv строит plots/ic.py.
    Возвращает dict метрик (JSON-сериализуемый); поле gate_pass — вердикт.
    """
    r, mass, _pos, _com, _hdr = read_ic_state(ic_path)
    m_p = float(np.mean(mass))
    r_min = max(float(r.min()) * 1.15, 0.02)
    centers, rho, cnt, edges = binned_profile(r, mass, r_min, 20.0)

    result: Dict = {"ic": os.path.abspath(ic_path),
                    "galic_dir": os.path.abspath(galic_dir) if galic_dir else None,
                    "N": int(len(r)), "m_p": m_p, "r_min": r_min,
                    "n_particles": int(len(r)), "m_particle": m_p}
    lines = ["IC gate report (check_ic_cusp.py v2)",
             "=" * 64,
             f"IC:           {os.path.abspath(ic_path)}",
             f"N:            {len(r)}   m_p = {m_p:.4e} (1e10 Msun)",
             f"GalIC output: {os.path.abspath(galic_dir) if galic_dir else 'NOT FOUND'}"]

    rho_target = slope_target = None
    if galic_dir and os.path.isfile(os.path.join(galic_dir, "rotcurve.txt")):
        r_t, v_t = read_rotcurve(galic_dir)
        params = read_galic_params(galic_dir)
        i_pk = int(np.argmax(v_t))
        # target — напрямую из фактической rotcurve GalIC, по тем же границам бинов
        rho_target = rho_target_in_bins(r_t, v_t, edges)
        slope_target = local_slope(centers, rho_target)
        rho_s, r_s, rms = fit_nfw_to_rotcurve(r_t, v_t)   # только справочно
        lines.append(f"GalIC params (fact): CC={params.get('CC')}  "
                     f"V200={params.get('V200')} km/s")
        lines.append(f"target: rotcurve GalIC напрямую (v^2 r / G), "
                     f"v_max={v_t[i_pk]:.1f} km/s @ {r_t[i_pk]:.2f} kpc, "
                     f"r range [{r_t[0]:.3f}, {r_t[-1]:.1f}] kpc")
        lines.append(f"справочно NFW-fit к rotcurve (для чеков НЕ используется): "
                     f"r_s={r_s:.3f} kpc rho_s={rho_s:.4e} rms(v^2)={rms:.4g}")
        result["galic_params"] = params
        result["nfw_fit"] = {"r_s_kpc": float(r_s), "rho_s": float(rho_s),
                             "rms_v2": float(rms), "used_for_checks": False}
        result["M_target_2kpc"] = float(np.interp(2.0, r_t, v_t**2 * r_t / G_CODE))
    else:
        lines.append("WARNING: rotcurve.txt не найден — сравнение с target невозможно")

    slope = local_slope(centers, rho)

    lines.append("")
    lines.append("Radial resolution / enclosed quantities:")
    lines.append("  r[kpc]      N(<r)          M(<r)[1e10 Msun]   t_relax[Gyr]")
    for rr in (0.1, 0.3, 0.5, 1.0, 2.0, 5.0):
        m = r < rr
        n_in = int(m.sum())
        m_in = float(mass[m].sum())
        tr = t_relax_gyr(n_in, m_in, rr)
        lines.append(f"  {rr:6.2f}  {n_in:12d}   {m_in:14.4e}   {tr:10.1f}")
        result[f"N_lt_{rr}"] = n_in
        result[f"M_lt_{rr}"] = m_in
        result[f"t_relax_{rr}"] = tr
    checks = {}
    gate = (centers >= rlo) & (centers <= rhi) & (cnt >= nmin) & \
        np.isfinite(rho) & (rho > 0)

    if rho_target is not None and int(gate.sum()) >= 3:
        ratio = rho[gate] / rho_target[gate]
        med_ratio = float(np.median(ratio))
        slope_gate = float(np.nanmedian(slope[gate]))
        slope_tgt = float(np.nanmedian(slope_target[gate]))
        lines.append("")
        lines.append(f"Central gate: {rlo}-{rhi} kpc, "
                     f"{int(gate.sum())} bins with N>={nmin}")
        lines.append(f"  median rho_meas/rho_target = {med_ratio:.3f}  (expect 1.00 +-0.15)")
        lines.append(f"  median local slope (meas)  = {slope_gate:+.3f}")
        lines.append(f"  median local slope (target)= {slope_tgt:+.3f}")
        lines.append(f"  |Delta slope|              = {abs(slope_gate - slope_tgt):.3f} (<=0.25)")
        checks["ratio_ok"] = abs(med_ratio - 1.0) <= 0.15
        checks["cusp_ok"] = slope_gate <= -0.75
        checks["slope_match"] = abs(slope_gate - slope_tgt) <= 0.25
        checks["min_count_ok"] = int(cnt[gate].min()) >= nmin
        result.update({"median_ratio": med_ratio, "slope_meas": slope_gate,
                       "slope_target": slope_tgt, "gate_bins": int(gate.sum()),
                       "rho_ratio_median": med_ratio,
                       "nbins_used": int(gate.sum()),
                       "slope_meas_median": slope_gate,
                       "slope_target_median": slope_tgt})
    else:
        checks["enough_bins"] = False
        lines.append("")
        lines.append("FAIL: недостаточно разрешённых бинов в центральной области "
                     "(или нет target) — увеличить N / изменить область.")

    n_1kpc = result.get("N_lt_1.0", 0)
    t_relax_1 = result.get("t_relax_1.0", float("nan"))
    checks["resolution_ok"] = bool(
        n_1kpc >= 3000 and np.isfinite(t_relax_1) and t_relax_1 >= 10.0)
    lines.append("")
    lines.append(f"Resolution: N(<1 kpc)={n_1kpc} (Power criterion >=3000), "
                 f"t_relax(1 kpc)={t_relax_1:.1f} Gyr (need >=10)")

    ok = all(checks.values())
    lines.append("")
    for k, v in checks.items():
        lines.append(f"  [{'PASS' if v else 'FAIL'}] {k}")
    lines.append("")
    lines.append(f"GATE: {'PASS' if ok else 'FAIL'}")
    result["checks"] = checks
    result["gate_pass"] = ok

    os.makedirs(outdir, exist_ok=True)
    with open(os.path.join(outdir, "ic_gate_report.txt"), "w") as fh:
        fh.write("\n".join(lines) + "\n")
    with open(os.path.join(outdir, "ic_gate.json"), "w") as fh:
        json.dump(result, fh, indent=2)
    with open(os.path.join(outdir, "ic_profiles.csv"), "w") as fh:
        fh.write("r_kpc,rho_meas,count,rho_nfw_target,slope_meas,slope_target\n")
        for i in range(len(centers)):
            rt = rho_target[i] if rho_target is not None else float("nan")
            st = slope_target[i] if slope_target is not None else float("nan")
            fh.write(f"{centers[i]:.5f},{rho[i]:.6e},{cnt[i]},{rt:.6e},"
                     f"{slope[i]:.4f},{st:.4f}\n")
    return result


def prepare_ic_figure_data(csv_path) -> Dict[str, np.ndarray]:
    """Прочитать ic_profiles.csv в plot-ready dict для plots/ic.py."""
    import csv as _csv
    cols: Dict[str, list] = {}
    with open(csv_path, newline="") as fh:
        for row in _csv.DictReader(fh):
            for k, v in row.items():
                cols.setdefault(k, []).append(float(v))
    return {k: np.asarray(v) for k, v in cols.items()}
