#!/usr/bin/env python3
"""loaders/prerun.py — метрики раннего гейта + диагностики серии (блок prerun).

Рисования здесь НЕТ (это plots/prerun.py). Состав — математика трёх гейтов
дословно:

  early_cdm_gate.py : read_state / com_and_radius / bulk_velocity /
      kinetic_energy / potential_energy_from_block / potential_energy_target_nfw /
      energy_summary / softening_stats / ninteractions_stats /
      timestep_stats_from_log / potential_energy_snap(ic, snap) /
      run_early_gate(ic, snap, galic_dir, outdir, run_log, ...) — метрики +
      report.txt/gate.json/profiles.csv, БЕЗ блока рисования;
  analyze_series.py : SeriesMetric / list_snapshots / bounded sync scan /
      weighted_center (shrink_center из loaders.snapshots) / shape_ratios /
      thickness_stats / rotation_stats / core_density /
      ninteractions_info / find_nearest_sync / read_metric /
      write_csv / classify_series / write_summary (без plot_lines/contact_sheet);
  compare_shape_series.py : ShapeSummary / summarize_run (эвристика disk_score) /
      write_summary_csv / write_text_report (без plot_compare).

Главная точка входа гейта — run_early_gate(); диагностики серии —
run_series_metrics() (metrics_series.csv + summary_partial_series.txt).
Графики по этим CSV строит plots/prerun.py.
"""

from __future__ import annotations

import csv
import glob
import json
import math
import os
import re
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from bisect import bisect_left, bisect_right
from collections.abc import Iterator, Sequence
from typing import Dict, Iterable, List, Optional, Tuple

import h5py
import numpy as np

from analysis.loaders.ic import (  # noqa: E402  (математика гейтов дословно)
    G_CODE,
    TIME_UNIT_GYR,
    binned_profile,
    find_galic_dir,
    fit_nfw_to_rotcurve,
    local_slope,
    potential_energy_from_rotcurve,
    read_galic_params,
    read_rotcurve,
    rho_nfw,
    rho_target_in_bins,
    slope_nfw,
    t_relax_gyr,
)

# ───────────────────────── early_cdm_gate.py (метрики) ─────────────────────────

def read_state(path, want_potential=True):
    """Позиции/скорости/массы/potential/softening/NInteractions из снапшота."""
    with h5py.File(path, "r") as f:
        key = None
        for k in ("PartType3", "PartType1"):
            if k in f:
                key = k
                break
        if key is None:
            raise RuntimeError("нет PartType3/PartType1 в %s" % path)
        g = f[key]
        pos = g["Coordinates"][:]
        vel = g["Velocities"][:]
        from analysis.loaders.snapshots import resolve_particle_masses
        ptype = int(key.removeprefix("PartType"))
        resolved_mass = resolve_particle_masses(g, f["Header"].attrs, ptype)
        # The early gate predates the physical Jz contract and still supports
        # particle-count geometry when no mass information exists.  Series Jz
        # below never uses this unit fallback: it marks physical moments nan.
        mass = (resolved_mass if resolved_mass is not None
                else np.full(len(pos), 1.0))
        pot = g["Potential"][:] if (want_potential and "Potential" in g) else None
        soft = g["Softening_KernelRadius"][:] if "Softening_KernelRadius" in g else None
        nint = g["NInteractions"][:] if "NInteractions" in g else None
        hdr = dict(f["Header"].attrs)
    return {"pos": pos, "vel": vel, "mass": mass, "potential": pot,
            "softening": soft, "nint": nint, "header": hdr}


def com_and_radius(state, center=None):
    pos, mass = state["pos"], state["mass"]
    if center is None:
        center = np.average(pos, axis=0, weights=mass)
    r = np.linalg.norm(pos - center, axis=1)
    return center, r


def bulk_velocity(state):
    """Масс-взвешенная средняя скорость (bulk drift) в км/с."""
    return np.average(state["vel"], axis=0, weights=state["mass"])


def kinetic_energy(state):
    """T = 0.5 * sum m v^2 относительно bulk-скорости."""
    v = state["vel"] - bulk_velocity(state)
    return float(0.5 * np.sum(state["mass"] * np.sum(v**2, axis=1)))


def potential_energy_from_block(state):
    """W = 0.5 * sum m Phi из блока Potential (GIZMO: Phi в (km/s)^2)."""
    if state["potential"] is None:
        return None
    return float(0.5 * np.sum(state["mass"] * state["potential"]))


_trapz = getattr(np, "trapezoid", None) or np.trapz  # numpy<2 / >=2


def potential_energy_target_nfw(rho_s, r_s, rmax=30.0, n=4000):
    """W для target NFW: -int_0^rmax G M(<r)/r * rho(r) 4 pi r^2 dr."""
    r = np.logspace(-3.0, np.log10(rmax), n)
    x = r / r_s
    rho = rho_s / (x * (1.0 + x) ** 2)
    m_enc = 4.0 * np.pi * rho_s * r_s**3 * (np.log(1.0 + x) - x / (1.0 + x))
    integ = G_CODE * m_enc / r * rho * 4.0 * np.pi * r**2
    return float(-_trapz(integ, r))


def energy_summary(s_ic, s_sn, rho_s, r_s):
    """2T/|W| для IC и snapshot; W_target — NFW-аппроксимация."""
    t_ic, t_sn = kinetic_energy(s_ic), kinetic_energy(s_sn)
    w_ic = potential_energy_from_block(s_ic)
    w_sn = potential_energy_from_block(s_sn)
    w_tg = potential_energy_target_nfw(rho_s, r_s)
    out = {"T_ic": t_ic, "T_snap": t_sn, "W_ic_block": w_ic,
           "W_snap_block": w_sn, "W_target_nfw": w_tg}
    if w_ic:
        out["virial_ic"] = 2.0 * t_ic / abs(w_ic)
    if w_sn:
        out["virial_snap"] = 2.0 * t_sn / abs(w_sn)
    if w_ic and w_sn and w_tg:
        out["dE_over_E_target"] = ((t_sn + w_sn) - (t_ic + w_ic)) / abs(t_ic + w_ic)
        out["dE_vs_target_scale"] = ((t_sn + w_sn) - (t_ic + w_ic)) / abs(w_tg)
    return out


def softening_stats(state):
    s = state["softening"]
    if s is None:
        return {"has_softening": False}
    s = np.asarray(s, dtype=float)
    return {"has_softening": True, "median": float(np.median(s)),
            "min": float(s.min()), "max": float(s.max())}


def ninteractions_stats(state):
    n = state["nint"]
    if n is None:
        return {"has_ninteractions": False}
    n = np.asarray(n).ravel()
    nz = n[n > 0]
    return {"has_ninteractions": True, "total": int(n.sum()),
            "frac_nonzero": float(len(nz) / len(n)) if len(n) else 0.0,
            "max": int(n.max()) if len(n) else 0,
            "median_nonzero": float(np.median(nz)) if len(nz) else 0.0}

def timestep_stats_from_log(run_log):
    """dt-статистика по Sync-Point строкам run.log (dtmin/dtmax/медиана/темп)."""
    if not run_log or not os.path.isfile(run_log):
        return {"has_log": False}
    times, dts = [], []
    for point in iter_sync_points(Path(run_log)):
        times.append(point.time)
        dts.append(point.step)
    if not dts:
        return {"has_log": True, "n_sync": 0}
    dts = np.array(dts)
    out = {"has_log": True, "n_sync": len(dts),
           "dt_min": float(dts.min()), "dt_max": float(dts.max()),
           "dt_median": float(np.median(dts))}
    if len(times) >= 2:
        out["pace_per_step"] = float((times[-1] - times[0]) / max(len(times) - 1, 1))
        out["time_first"] = float(times[0])
        out["time_last"] = float(times[-1])
    return out


def snapshot_profiles(ic_state, snap_state, rmin=0.02, rmax=20.0):
    """Профили IC/snap + производные (версия early_cdm_gate, сетка 61/60)."""
    c_ic, r_ic = com_and_radius(ic_state)
    c_sn, r_sn = com_and_radius(snap_state)
    edges = np.logspace(np.log10(rmin), np.log10(rmax), 61)
    centers = np.sqrt(edges[:-1] * edges[1:])
    vol = (4.0 / 3.0) * np.pi * (edges[1:] ** 3 - edges[:-1] ** 3)
    rho_ic = np.full(60, np.nan)
    rho_sn = np.full(60, np.nan)
    cnt_ic = np.zeros(60, dtype=int)
    cnt_sn = np.zeros(60, dtype=int)
    for i in range(60):
        m = (r_ic >= edges[i]) & (r_ic < edges[i + 1])
        cnt_ic[i] = int(m.sum())
        if cnt_ic[i]:
            rho_ic[i] = ic_state["mass"][m].sum() / vol[i]
        m = (r_sn >= edges[i]) & (r_sn < edges[i + 1])
        cnt_sn[i] = int(m.sum())
        if cnt_sn[i]:
            rho_sn[i] = snap_state["mass"][m].sum() / vol[i]
    return {"centers": centers, "edges": edges,
            "rho_ic": rho_ic, "rho_sn": rho_sn,
            "cnt_ic": cnt_ic, "cnt_sn": cnt_sn,
            "slope_ic": local_slope(centers, rho_ic),
            "slope_sn": local_slope(centers, rho_sn),
            "com_ic": c_ic, "com_snap": c_sn}

def parse_log_steps(log_path):
    """Шаги/тайминги из run.log (строки 'Sync-Point N, Time: t, Systemstep: dt').

    Дословно parse_log_steps() из early_cdm_gate.py.
    """
    times, dts = [], []
    if log_path and os.path.isfile(log_path):
        for point in iter_sync_points(Path(log_path)):
            times.append(point.time)
            dts.append(point.step)
    return np.array(times), np.array(dts)


def run_early_gate(ic_path, snap_path, galic_dir=None, outdir=".",
                  run_log=None, nmin=200, rlo=0.3, rhi=3.0,
                  drho_tol=0.05, dslope_tol=0.20) -> Dict:
    """Ранний гейт дословно из main() early_cdm_gate.py: метрики + 3 файла.

    Рисования НЕТ (matplotlib-блок гейта → plots/prerun.py:early_cusp_compare).
    Пишет report.txt / gate.json / profiles.csv в outdir и возвращает res
    (ключи как в gate.json); вердикт — res["gate_pass"].
    """
    ic = read_state(ic_path, want_potential=False)
    sn = read_state(snap_path)
    m_p = float(np.mean(ic["mass"]))
    t_snap = float(sn["header"].get("Time", float("nan")))
    r_min = max(float(np.min(np.linalg.norm(ic["pos"] - ic["pos"].mean(0),
                                            axis=1))) * 1.15, 0.02)

    ic_center, r_ic = com_and_radius(ic)
    sn_center, r_sn = com_and_radius(sn)
    centers, rho_ic, cnt_ic, edges = binned_profile(r_ic, ic["mass"], r_min, 20.0)
    _, rho_sn, cnt_sn, _ = binned_profile(r_sn, sn["mass"], r_min, 20.0)
    slope_ic = local_slope(centers, rho_ic)
    slope_sn = local_slope(centers, rho_sn)

    lines, res = [], {"ic": ic_path, "snap": snap_path, "t_snap": t_snap,
                      "galic_dir": galic_dir, "N": int(len(r_ic)), "m_p": m_p}
    lines.append("Early CDM gate report (early_cdm_gate.py)")
    lines.append("=" * 70)
    lines.append(f"IC:   {ic_path}")
    lines.append(f"snap: {snap_path}   Time = {t_snap:.6f} "
                 f"(~{t_snap * TIME_UNIT_GYR:.1f} Gyr)")
    lines.append(f"N snap: {len(r_sn)}  (IC N: {len(r_ic)})   "
                 f"m_p = {m_p:.4e} (1e10 Msun)")

    rho_target = slope_target = None
    r_t = v_t = None
    if galic_dir and os.path.isfile(os.path.join(galic_dir, "rotcurve.txt")):
        r_t, v_t = read_rotcurve(galic_dir)
        params = read_galic_params(galic_dir)
        rho_s_fit, r_s_fit, rms = fit_nfw_to_rotcurve(r_t, v_t)  # только справочно
        rho_target = rho_target_in_bins(r_t, v_t, edges)
        slope_target = local_slope(centers, rho_target)
        res["nfw_fit"] = {"r_s_kpc": float(r_s_fit), "rho_s": float(rho_s_fit),
                          "rms_v2": float(rms), "used_for_checks": False}
        res["galic_params"] = params
        lines.append(f"target: rotcurve GalIC напрямую (v^2 r / G) "
                     f"[CC={params.get('CC')}, V200={params.get('V200')}]; "
                     f"справочно NFW-fit: r_s={r_s_fit:.3f} kpc rms(v^2)={rms:.4g}")
    else:
        lines.append("WARNING: target (rotcurve) не найден — "
                     "сравнение с target пропущено")

    d_center = sn_center - ic_center
    v_ic, v_sn = bulk_velocity(ic), bulk_velocity(sn)
    lines.append("")
    lines.append("Center & bulk drift:")
    lines.append(f"  COM(IC)   = ({ic_center[0]:+.4f}, {ic_center[1]:+.4f}, "
                 f"{ic_center[2]:+.4f})")
    lines.append(f"  COM(snap) = ({sn_center[0]:+.4f}, {sn_center[1]:+.4f}, "
                 f"{sn_center[2]:+.4f})")
    lines.append(f"  |dCOM|    = {np.linalg.norm(d_center):.5f} kpc")
    lines.append(f"  v_bulk(IC)   = {np.array2string(v_ic, precision=3)} km/s "
                 f"|v|={np.linalg.norm(v_ic):.3f}")
    lines.append(f"  v_bulk(snap) = {np.array2string(v_sn, precision=3)} km/s "
                 f"|v|={np.linalg.norm(v_sn):.3f}")
    res["dCOM_kpc"] = float(np.linalg.norm(d_center))
    res["v_bulk_ic"] = [float(x) for x in v_ic]
    res["v_bulk_snap"] = [float(x) for x in v_sn]

    # ---------------- профили / сохранение каспа ----------------
    gate = (centers >= rlo) & (centers <= rhi) & \
           (cnt_ic >= nmin) & (cnt_sn >= nmin) & \
           np.isfinite(rho_ic) & np.isfinite(rho_sn) & (rho_ic > 0) & (rho_sn > 0)
    lines.append("")
    lines.append(f"Central gate range {rlo}-{rhi} kpc: "
                 f"{int(gate.sum())} bins with N>={nmin}")
    checks = {}
    if int(gate.sum()) >= 3:
        med_ratio = float(np.median(rho_ic[gate] / rho_sn[gate]))
        sl_ic = float(np.nanmedian(slope_ic[gate]))
        sl_sn = float(np.nanmedian(slope_sn[gate]))
        d_slope = sl_sn - sl_ic
        lines.append(f"  median slope IC    = {sl_ic:+.3f}")
        lines.append(f"  median slope snap  = {sl_sn:+.3f}   (Delta = {d_slope:+.3f}, "
                     f"tol {dslope_tol})")
        lines.append(f"  median rho_IC/rho_snap = {med_ratio:.4f} (tol {drho_tol:.0%})")
        checks["no_immediate_core"] = d_slope <= dslope_tol
        checks["central_density_stable"] = abs(med_ratio - 1.0) <= drho_tol
        if rho_target is not None:
            sl_tg = float(np.nanmedian(slope_target[gate]))
            r_tg = float(np.median(rho_sn[gate] / rho_target[gate]))
            lines.append(f"  median slope target = {sl_tg:+.3f}  "
                         f"(|snap-target| = {abs(sl_sn - sl_tg):.3f})")
            lines.append(f"  median rho_snap/rho_target = {r_tg:.4f}")
            res.update({"slope_target": sl_tg, "rho_snap_over_target": r_tg})
            checks["snap_matches_target"] = abs(sl_sn - sl_tg) <= dslope_tol + 0.10
        res.update({"slope_ic": sl_ic, "slope_snap": sl_sn, "d_slope": d_slope,
                    "rho_ic_over_snap": med_ratio, "gate_bins": int(gate.sum())})
    else:
        checks["enough_bins"] = False
        lines.append("  FAIL: недостаточно разрешённых бинов в центральной области")

    # ---------------- enclosed mass / N(<r) ----------------
    lines.append("")
    lines.append("Enclosed mass / N(<r):")
    lines.append("  r[kpc]     N_IC       N_snap     M_IC[1e10]   M_snap[1e10]   dM/M")
    for rr in (0.1, 0.3, 0.5, 1.0, 2.0, 5.0):
        mi, ms = r_ic < rr, r_sn < rr
        m_ic = float(ic["mass"][mi].sum())
        m_sn = float(sn["mass"][ms].sum())
        lines.append(f"  {rr:6.2f}  {int(mi.sum()):10d}  {int(ms.sum()):10d}   "
                     f"{m_ic:12.4e}  {m_sn:12.4e}   {(m_sn - m_ic) / m_ic:+.2e}")
        res[f"N_lt_{rr}_ic"] = int(mi.sum())
        res[f"N_lt_{rr}_snap"] = int(ms.sum())
    n1 = res.get("N_lt_1.0_snap", 0)
    m1 = float(sn["mass"][r_sn < 1.0].sum())
    tr1 = t_relax_gyr(n1, m1, 1.0)
    lines.append(f"  resolution check: N(<1 kpc)={n1}, t_relax(1 kpc)={tr1:.1f} Gyr")
    # Критерий Power et al. (2003): ~3000 частиц в релаксационно-ограниченной
    # области и t_relax > возраста симуляции (здесь с запасом >= 10 Gyr).
    checks["resolution_ok"] = bool(n1 >= 3000 and tr1 >= 10.0)

    # ---------------- энергии / вириал ----------------
    t_ic, t_sn = kinetic_energy(ic), kinetic_energy(sn)
    w_sn = potential_energy_from_block(sn)
    lines.append("")
    lines.append("Energy / virial diagnostics (units 1e10 Msun (km/s)^2):")
    lines.append(f"  T(IC)   = {t_ic:.6e}     T(snap) = {t_sn:.6e}   "
                 f"dT/T = {(t_sn - t_ic) / t_ic:+.3e}")
    res.update({"T_ic": t_ic, "T_snap": t_sn})
    if w_sn is not None:
        lines.append(f"  W(snap) = {w_sn:.6e} (из блока Potential)   "
                     f"2T/|W| = {2 * t_sn / abs(w_sn):.4f}")
        res.update({"W_snap": w_sn, "virial_2T_W_snap": 2 * t_sn / abs(w_sn)})
        checks["virial_sane"] = bool(0.6 <= 2 * t_sn / abs(w_sn) <= 1.8)
    if r_t is not None:
        w_tg = potential_energy_from_rotcurve(r_t, v_t)
        if w_sn is not None:
            de = (t_sn + w_sn) - (t_ic + w_tg)
            lines.append(f"  W(target rotcurve) = {w_tg:.6e}   2T/|W|(IC,target) = "
                         f"{2 * t_ic / abs(w_tg):.4f}")
            lines.append(f"  dE/|W_target| = {de / abs(w_tg):+.3e}  "
                         f"(энергия IC+target-W vs snap)")
            res.update({"W_target": w_tg, "dE_over_W": de / abs(w_tg),
                        "virial_2T_W_ic_target": 2 * t_ic / abs(w_tg)})
    # ---------------- timestep / softening sanity ----------------
    times, dts = parse_log_steps(run_log)
    lines.append("")
    lines.append("Timestep / softening sanity:")
    pos_dt = dts[dts > 0]
    if len(times):
        lines.append(f"  шагов (Sync-Point): {len(times)};  t range "
                     f"[{times.min():.3e}, {times.max():.3e}]")
        if len(pos_dt):
            lines.append(f"  dt (ненулевые): min={pos_dt.min():.3e} "
                         f"median={np.median(pos_dt):.3e} max={pos_dt.max():.3e}")
        checks["timesteps_sane"] = bool(len(pos_dt) and pos_dt.min() > 1e-7)
        res.update({"n_steps": int(len(times)),
                    "dt_min": float(pos_dt.min()) if len(pos_dt) else None,
                    "dt_max": float(pos_dt.max()) if len(pos_dt) else None})
    else:
        lines.append("  (run.log не найден/не распознан — "
                     "timestep-проверка пропущена)")
    if sn["softening"] is not None:
        soft = sn["softening"]
        inner = r_sn < 1.0
        n_in = int(inner.sum())
        rho_mean = n_in / ((4.0 / 3.0) * np.pi * 1.0**3)
        spacing = rho_mean ** (-1.0 / 3.0)
        lines.append(f"  Softening_KernelRadius: min={soft.min():.4e} "
                     f"median={np.median(soft):.4e} (code units); "
                     f"inner(r<1kpc) median={np.median(soft[inner]):.4e}")
        lines.append(f"  среднее межчастичное расстояние (r<1 kpc) ~ {spacing:.4f} kpc "
                     f"(n={n_in})")
        res.update({"soft_min": float(soft.min()),
                    "soft_median": float(np.median(soft)),
                    "soft_inner_median": float(np.median(soft[inner])),
                    "mean_spacing_1kpc": float(spacing)})
    if sn["nint"] is not None:
        nint_max = int(np.max(sn["nint"]))
        lines.append(f"  NInteractions max = {nint_max} (CDM: ожидается 0)")
        res["nint_max"] = nint_max
        checks["cdm_no_interactions"] = nint_max == 0

    # ---------------- вердикт ----------------
    ok = all(checks.values())
    lines.append("")
    for k, v in checks.items():
        lines.append(f"  [{'PASS' if v else 'FAIL'}] {k}")
    lines.append("")
    lines.append(f"EARLY GATE: {'PASS' if ok else 'FAIL'}")
    lines.append("Next state: WAITING_FOR_REVIEW (production continuation НЕ "
                 "запускается автоматически)")
    res["checks"] = checks
    res["gate_pass"] = ok

    os.makedirs(outdir, exist_ok=True)
    with open(os.path.join(outdir, "report.txt"), "w") as fh:
        fh.write("\n".join(lines) + "\n")
    with open(os.path.join(outdir, "gate.json"), "w") as fh:
        json.dump(res, fh, indent=2)
    with open(os.path.join(outdir, "profiles.csv"), "w") as fh:
        fh.write("r_kpc,rho_ic,rho_snap,rho_target,count_ic,count_snap,"
                 "slope_ic,slope_snap,slope_target\n")
        for i in range(len(centers)):
            rt = rho_target[i] if rho_target is not None else float("nan")
            st = slope_target[i] if slope_target is not None else float("nan")
            fh.write(f"{centers[i]:.5f},{rho_ic[i]:.6e},{rho_sn[i]:.6e},{rt:.6e},"
                     f"{cnt_ic[i]},{cnt_sn[i]},{slope_ic[i]:.4f},{slope_sn[i]:.4f},"
                     f"{st:.4f}\n")
    return res


def prepare_early_figure_data(csv_path) -> Dict[str, np.ndarray]:
    """Прочитать profiles.csv раннего гейта в plot-ready dict (plots/prerun.py)."""
    cols: Dict[str, list] = {}
    with open(csv_path, newline="") as fh:
        for row in csv.DictReader(fh):
            for k, v in row.items():
                cols.setdefault(k, []).append(float(v))
    return {k: np.asarray(v) for k, v in cols.items()}

# ───────────────────────── analyze_series.py (метрики серии) ────────────────────

GYR_PER_CODE = 0.9777923542981722


@dataclass
class SeriesMetric:
    snapshot: int
    file: str
    time: float
    particles: int
    rho_core_r1: float
    rho_core_r2: float
    rho_core_r5: float
    ba_r2: float
    ca_r2: float
    ba_r5: float
    ca_r5: float
    ba_r10: float
    ca_r10: float
    z_rms_over_R_rms_r5: float
    z_p68_over_R_p68_r5: float
    mean_vphi_r5: float
    median_vphi_r5: float
    sigma_vphi_r5: float
    vrot_over_sigma_r5: float
    ninteractions_total: int
    interacted_fraction: float
    ninteractions_mean_nonzero: float
    ninteractions_p90_nonzero: float
    ninteractions_max: int
    nearest_sync_point: int
    nearest_systemstep: float
    # Keep new fields at the end so legacy positional constructors remain
    # valid.  These are physical quantities in the fixed original z frame.
    jz_total_r5: float = math.nan
    jz_mass_r5: float = math.nan
    jz_per_mass_r5: float = math.nan


@dataclass
class SyncPoint:
    sync: int
    time: float
    step: float


@dataclass(frozen=True)
class SyncScanResult:
    """Bounded-memory result of one complete ``run.log`` scan.

    ``nearest_points`` is aligned with ``target_times`` and is the only set of
    sync points retained.  In particular, this object never stores all parsed
    log rows.  The two candidate extrema (the closest point below/above each
    target) are enough to recover the nearest point even when the log contains
    repeated or non-monotonic times.

    ``status`` is deliberately explicit.  It is one of ``ok``, ``empty``,
    ``missing``, ``unreadable``, ``malformed``, ``no-match`` or a ``+`` joined
    combination such as ``malformed+no-match``.  Malformed marker lines and
    targets without a finite nearest point are also exposed as counters, so a
    caller does not need to infer them from the status string.
    """

    target_times: Tuple[float, ...]
    nearest_points: Tuple[Optional[SyncPoint], ...]
    full_log_min_positive_systemstep: float
    parsed_sync_count: int
    malformed_count: int
    lines_scanned: int
    status: str

    @property
    def nearest(self) -> Tuple[Optional[SyncPoint], ...]:
        """Short alias for consumers that use the result as a scan record."""
        return self.nearest_points

    @property
    def global_min_positive_systemstep(self) -> float:
        """Compatibility alias for the canonical min-step field."""
        return self.full_log_min_positive_systemstep

    @property
    def min_positive_systemstep(self) -> float:
        return self.full_log_min_positive_systemstep

    @property
    def parsed_count(self) -> int:
        """Compatibility alias for the number of recognized sync rows."""
        return self.parsed_sync_count

    @property
    def n_sync(self) -> int:
        return self.parsed_sync_count

    @property
    def no_match_count(self) -> int:
        return sum(point is None for point in self.nearest_points)

    @property
    def unmatched_count(self) -> int:
        return self.no_match_count


_FLOAT_TOKEN = r"[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?"

# GIZMO's production spelling is ``Systemstep``.  Older logs and synthetic
# fixtures also use ``System step`` or ``System-step``; all are accepted.
# ``re.IGNORECASE`` handles ``Time``/``time`` and the corresponding variants.
SYNC_RE = re.compile(
    rf"\bSync\s*[-_ ]?\s*Point\b\s*[,;:#]?\s*"
    rf"(?P<sync>\d+)\b.*?\bTime\b\s*[:=]\s*(?P<time>{_FLOAT_TOKEN})"
    rf".*?\bSystem\s*[-_ ]?\s*step\b\s*[:=]\s*(?P<dt>{_FLOAT_TOKEN})",
    re.IGNORECASE,
)
_SYNC_MARKER_RE = re.compile(r"\bSync\s*[-_ ]?\s*Point\b", re.IGNORECASE)
_DEFAULT_LOG_CHUNK_SIZE = 1024 * 1024


def list_series_snapshots(run_root: Path) -> List[Path]:
    from analysis.loaders.snapshots import _snapshot_number as _sn
    files = sorted((run_root / "output").glob("snapshot_*.hdf5"),
                   key=lambda p: _sn(str(p)))
    if not files:
        raise FileNotFoundError(f"No snapshots in {run_root / 'output'}")
    return files


def _iter_log_lines(log_path: Path,
                    chunk_size: int = _DEFAULT_LOG_CHUNK_SIZE) -> Iterator[str]:
    """Yield log lines using bounded binary chunks.

    ``TextIO`` iteration is already streaming, but an explicit binary chunk
    reader gives deterministic behaviour for a test where a Sync-Point line is
    split exactly at a chunk boundary.  The only retained bytes are the
    current chunk and the unfinished line.  GIZMO logs are ASCII-compatible;
    malformed byte sequences are replaced rather than aborting a scan.
    """
    if chunk_size <= 0:
        raise ValueError("chunk_size must be positive")
    with Path(log_path).open("rb") as fh:
        pending = b""
        while True:
            chunk = fh.read(chunk_size)
            if not chunk:
                break
            pending += chunk
            lines = pending.split(b"\n")
            pending = lines.pop()
            for raw in lines:
                yield raw.decode("utf-8", errors="replace").rstrip("\r")
        if pending:
            yield pending.decode("utf-8", errors="replace").rstrip("\r")


def _parse_sync_line(line: str) -> Optional[SyncPoint]:
    """Parse one Sync-Point line, returning ``None`` for malformed rows."""
    match = SYNC_RE.search(line)
    if match is None:
        return None
    try:
        sync = int(match.group("sync"))
        point_time = float(match.group("time"))
        step = float(match.group("dt"))
    except (TypeError, ValueError, OverflowError):
        return None
    if not (math.isfinite(point_time) and math.isfinite(step)):
        return None
    return SyncPoint(sync=sync, time=point_time, step=step)


def iter_sync_points(log_path: Path,
                     *,
                     chunk_size: int = _DEFAULT_LOG_CHUNK_SIZE
                     ) -> Iterator[SyncPoint]:
    """Lazily yield recognized Sync-Point rows from ``log_path``.

    This is the migration path for callers that only need to iterate legacy
    rows.  It is reusable (a new iterator is created per call) and does not
    retain the log.  For nearest-point and min-step work use
    :func:`scan_sync_points`, which scans once instead of rescanning per
    snapshot.
    """
    path = Path(log_path)
    if not path.exists():
        return
    for line in _iter_log_lines(path, chunk_size=chunk_size):
        point = _parse_sync_line(line)
        if point is not None:
            yield point


class SyncPointStream:
    """Re-iterable lazy compatibility view of recognized sync rows.

    Historically ``read_all_sync_points`` returned a list.  A list is unsafe
    for multi-gigabyte logs, so this small view keeps the common iterable API
    while reopening the bounded parser for each iteration.  The canonical
    runner does not iterate it repeatedly; it uses ``scan_sync_points`` once.
    """

    def __init__(self, log_path: Path,
                 chunk_size: int = _DEFAULT_LOG_CHUNK_SIZE):
        self.log_path = Path(log_path)
        self.chunk_size = int(chunk_size)

    def __iter__(self) -> Iterator[SyncPoint]:
        return iter_sync_points(self.log_path, chunk_size=self.chunk_size)

    def __bool__(self) -> bool:
        try:
            next(iter(self))
        except StopIteration:
            return False
        return True

    def __len__(self) -> int:
        # Counting is still a full scan, but retains no rows.  It is provided
        # only for old callers that used len(points), not by the series runner.
        return sum(1 for _ in self)


def _prefer_extreme(old: Optional[SyncPoint], new: SyncPoint,
                    *, maximum: bool) -> SyncPoint:
    """Choose a deterministic predecessor/successor candidate."""
    if old is None:
        return new
    old_key = (old.time, -old.sync, -old.step)
    new_key = (new.time, -new.sync, -new.step)
    if maximum:
        return new if new_key > old_key else old
    old_key = (-old.time, -old.sync, -old.step)
    new_key = (-new.time, -new.sync, -new.step)
    return new if new_key > old_key else old


class _RangeExtremeTags:
    """Range-extreme tags with point queries and bounded storage.

    A parsed sync time updates a suffix (predecessors) or prefix
    (successors) of sorted targets.  Storing an extreme tag on the canonical
    segment-tree cover makes each update O(log N_target), while no parsed log
    row is retained.  Tags are resolved only once at the end of the scan.
    """

    def __init__(self, size: int, *, maximum: bool):
        self.maximum = maximum
        tree_size = 1
        while tree_size < size:
            tree_size <<= 1
        self._size = tree_size
        self._tags: List[Optional[SyncPoint]] = [None] * (2 * tree_size)

    def update(self, left: int, right: int, point: SyncPoint) -> None:
        if left >= right:
            return
        left += self._size
        right += self._size
        while left < right:
            if left & 1:
                self._tags[left] = _prefer_extreme(
                    self._tags[left], point, maximum=self.maximum)
                left += 1
            if right & 1:
                right -= 1
                self._tags[right] = _prefer_extreme(
                    self._tags[right], point, maximum=self.maximum)
            left >>= 1
            right >>= 1

    def query(self, index: int) -> Optional[SyncPoint]:
        index += self._size
        result: Optional[SyncPoint] = None
        while index:
            result = (_prefer_extreme(result, self._tags[index],
                                      maximum=self.maximum)
                      if self._tags[index] is not None else result)
            index >>= 1
        return result


def _nearest_from_candidates(target: float,
                            *candidates: Optional[SyncPoint]
                            ) -> Optional[SyncPoint]:
    finite = [p for p in candidates
              if p is not None and math.isfinite(p.time)]
    if not math.isfinite(target) or not finite:
        return None
    # Tie policy: smallest distance, then earlier sync time, then lower sync
    # number, then lower step.  It is independent of log order and therefore
    # deterministic for repeated/non-monotonic sync times.
    return min(finite, key=lambda p: (abs(p.time - target), p.time,
                                      p.sync, p.step))


def scan_sync_points(log_path: Path,
                     target_times: Sequence[float],
                     *,
                     chunk_size: int = _DEFAULT_LOG_CHUNK_SIZE
                     ) -> SyncScanResult:
    """Scan a log once and retain nearest points for explicit target times.

    The scan is complete even when target times are unsorted or repeated.  It
    also computes the minimum positive ``Systemstep`` over every recognized
    row.  Memory is O(number of targets + chunk size), not O(number of log
    rows).  A missing/unreadable log is represented in the result rather than
    raising, because physical snapshot metrics remain meaningful without
    timestep provenance.
    """
    targets = tuple(float(value) for value in target_times)
    path = Path(log_path)
    if not path.exists():
        return SyncScanResult(
            target_times=targets,
            nearest_points=(None,) * len(targets),
            full_log_min_positive_systemstep=math.nan,
            parsed_sync_count=0, malformed_count=0, lines_scanned=0,
            status="missing")
    try:
        # Keep duplicate target entries: each output position corresponds to
        # exactly one requested snapshot, while sorting is only internal.
        # Non-finite targets can never have a nearest point and are excluded
        # from bisect operations explicitly.
        ordered_pairs = sorted((value, index)
                               for index, value in enumerate(targets)
                               if math.isfinite(value))
        ordered_targets = [value for value, _ in ordered_pairs]
        predecessor = _RangeExtremeTags(len(ordered_targets), maximum=True)
        successor = _RangeExtremeTags(len(ordered_targets), maximum=False)
        min_positive = math.inf
        parsed = malformed = lines_scanned = 0
        for line in _iter_log_lines(path, chunk_size=chunk_size):
            lines_scanned += 1
            if _SYNC_MARKER_RE.search(line) is None:
                continue
            point = _parse_sync_line(line)
            if point is None:
                malformed += 1
                continue
            parsed += 1
            if point.step > 0.0 and point.step < min_positive:
                min_positive = point.step
            if ordered_targets:
                # A point is a predecessor for targets >= time and a
                # successor for targets <= time.  bisect_left/right preserve
                # exact matches on both sides, which is harmless and makes
                # the deterministic tie policy explicit.
                left = bisect_left(ordered_targets, point.time)
                right = bisect_right(ordered_targets, point.time)
                predecessor.update(left, len(ordered_targets), point)
                successor.update(0, right, point)
        if ordered_targets:
            nearest_sorted = tuple(
                _nearest_from_candidates(value, predecessor.query(index),
                                         successor.query(index))
                for index, value in enumerate(ordered_targets))
            # sorted() is stable, so this mapping handles duplicate and
            # non-monotonic target inputs without collapsing equal times.
            positions = [original for _, original in ordered_pairs]
            by_original = [None] * len(targets)
            for original, candidate in zip(positions, nearest_sorted):
                by_original[original] = candidate
            nearest = tuple(by_original)
        else:
            nearest = ()
    except OSError:
        return SyncScanResult(
            target_times=targets,
            nearest_points=(None,) * len(targets),
            full_log_min_positive_systemstep=math.nan,
            parsed_sync_count=0, malformed_count=0,
            lines_scanned=0, status="unreadable")

    no_match = any(point is None for point in nearest)
    if parsed == 0:
        status = "malformed" if malformed else ("no-match" if targets else "empty")
    else:
        flags = []
        if malformed:
            flags.append("malformed")
        if no_match:
            flags.append("no-match")
        status = "+".join(flags) if flags else "ok"
    return SyncScanResult(
        target_times=targets,
        nearest_points=nearest,
        full_log_min_positive_systemstep=(
            float(min_positive) if math.isfinite(min_positive) else math.nan),
        parsed_sync_count=parsed, malformed_count=malformed,
        lines_scanned=lines_scanned, status=status)


def read_all_sync_points(log_path: Path) -> SyncPointStream:
    """Compatibility wrapper with a lazy, bounded-memory result.

    Code that truly requires a concrete list can use ``list(...)`` explicitly
    at its own boundary.  New series code should migrate to
    :func:`scan_sync_points`, which avoids rescanning the log for each
    snapshot and also exposes global min-step/status metadata.
    """
    return SyncPointStream(log_path)


def read_snapshot_time(snap: Path) -> float:
    """Read only ``Header/Time`` before any particle datasets are loaded."""
    with h5py.File(snap, "r") as f:
        return float(f["Header"].attrs.get("Time", math.nan))


SERIES_METADATA_SCHEMA = "series-metadata-v1"
SERIES_ANALYSIS_SCHEMA = "series-jz-v2"


def _metadata_float(value: float) -> Optional[float]:
    value = float(value)
    return value if math.isfinite(value) else None


def build_series_metadata(*,
                          run_root: Path,
                          artifact_identity: str,
                          ptype: int,
                          snapshot_times: Sequence[float],
                          scan: SyncScanResult,
                          command: Optional[str] = None) -> Dict:
    """Build deterministic provenance for a canonical metrics series.

    No file hashes or wall-clock timestamps are invented here.  The metadata
    records only facts available to the runner invocation and explicitly
    states the mass/frame policy used by ``read_series_metric``.
    """
    finite_times = [float(value) for value in snapshot_times
                    if math.isfinite(float(value))]
    metadata = {
        "schema": SERIES_METADATA_SCHEMA,
        "schema_version": SERIES_METADATA_SCHEMA,
        "analysis_schema_version": SERIES_ANALYSIS_SCHEMA,
        "run_root": str(run_root),
        "run_id": Path(run_root).name,
        "artifact_identity": str(artifact_identity),
        "ptype": int(ptype),
        "aperture": {"kind": "spherical", "radius": 5.0,
                      "radius_unit": "snapshot coordinate units"},
        "aperture_r": 5.0,
        "fixed_axis": "z",
        "mass_source_policy": {
            "preferred": "PartType<ptype>/Masses",
            "fallback": "Header/MassTable[ptype] when finite and positive",
            "missing_or_invalid": "physical Jz fields are nan",
            "geometry_fallback": "unit weights are legacy geometry-only; never physical Jz",
        },
        "shrink_center": {"method": "shrink_center", "iterations": 6},
        "velocity_frame": {
            "method": "mass_weighted_bulk_velocity",
            "scope": "all particles of selected PartType",
            "axis": "fixed original z; no per-snapshot rotation",
        },
        "snapshot_count": len(snapshot_times),
        "snapshot_time_min": min(finite_times) if finite_times else None,
        "snapshot_time_max": max(finite_times) if finite_times else None,
        "snapshot_time_range": ([min(finite_times), max(finite_times)]
                                if finite_times else None),
        "full_log_min_positive_systemstep": _metadata_float(
            scan.full_log_min_positive_systemstep),
        "parsed_sync_count": int(scan.parsed_sync_count),
        "parsed_sync_status": scan.status,
        "malformed_sync_count": int(scan.malformed_count),
        "unmatched_snapshot_count": int(scan.no_match_count),
        "scanned_log_lines": int(scan.lines_scanned),
        "provenance": {
            "command": command,
            "log_path": str(Path(run_root) / "run.log"),
            "hdf5_hash": None,
            "log_hash": None,
            "hashes_note": "large HDF5/log files were not hashed by this runner",
        },
    }
    return metadata


def write_series_metadata(metadata: Dict, path: Path) -> None:
    """Write stable, sorted JSON metadata next to ``metrics_series.csv``."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fh:
        json.dump(metadata, fh, indent=2, sort_keys=True, ensure_ascii=False)
        fh.write("\n")


def weighted_center(pos: np.ndarray, mass: np.ndarray) -> np.ndarray:
    from analysis.loaders.snapshots import shrink_center
    if len(pos) == 0:
        return np.full(3, np.nan, dtype=float)
    return shrink_center(pos, mass, niter=6)


def shape_ratios(pos: np.ndarray, mass: np.ndarray, radius: float) -> Tuple[float, float]:
    r = np.linalg.norm(pos, axis=1)
    m = r < radius
    if int(m.sum()) < 20:
        return math.nan, math.nan
    x = pos[m]
    w = mass[m]
    cov = (x * w[:, None]).T @ x / np.sum(w)
    vals = np.linalg.eigvalsh(cov)
    vals = np.sort(vals)
    if vals[2] <= 0:
        return math.nan, math.nan
    return float(np.sqrt(vals[1] / vals[2])), float(np.sqrt(vals[0] / vals[2]))

def thickness_stats(pos: np.ndarray, radius: float) -> Tuple[float, float]:
    r = np.linalg.norm(pos, axis=1)
    m = r < radius
    if int(m.sum()) < 20:
        return math.nan, math.nan
    x, y, z = pos[m][:, 0], pos[m][:, 1], pos[m][:, 2]
    R = np.sqrt(x**2 + y**2)
    z_rms = float(np.sqrt(np.mean(z**2)))
    R_rms = float(np.sqrt(np.mean(R**2)))
    z_p68 = float(np.percentile(np.abs(z), 68))
    R_p68 = float(np.percentile(R, 68))
    return (z_rms / R_rms if R_rms > 0 else math.nan,
            z_p68 / R_p68 if R_p68 > 0 else math.nan)


def rotation_stats(pos: np.ndarray, vel: np.ndarray, radius: float) -> Tuple[float, ...]:
    r = np.linalg.norm(pos, axis=1)
    m = r < radius
    if int(m.sum()) < 20:
        return math.nan, math.nan, math.nan, math.nan
    x, y = pos[m][:, 0], pos[m][:, 1]
    vx, vy = vel[m][:, 0], vel[m][:, 1]
    R = np.sqrt(x**2 + y**2)
    with np.errstate(divide="ignore", invalid="ignore"):
        vphi = np.where(R > 0, (x * vy - y * vx) / R, np.nan)
    vphi = vphi[np.isfinite(vphi)]
    if len(vphi) < 20:
        return math.nan, math.nan, math.nan, math.nan
    mean_v = float(np.mean(vphi))
    med_v = float(np.median(vphi))
    sig_v = float(np.std(vphi))
    return mean_v, med_v, sig_v, (abs(mean_v) / sig_v if sig_v > 0 else math.nan)


def angular_momentum_stats(pos_centered: np.ndarray,
                           vel_centered: np.ndarray,
                           mass: Optional[np.ndarray],
                           radius: float) -> Tuple[float, float, float]:
    """Return ``(Jz, M, Jz/M)`` inside a spherical aperture.

    ``pos_centered`` and ``vel_centered`` must already use the series frame:
    the shrinkage center and the mass-weighted bulk velocity of the selected
    particle type.  The z axis is deliberately not fitted or rotated.  The
    helper only computes the raw observable; Jz/Jz0 normalisation belongs to a
    series/summarisation layer.

    A missing or malformed mass array makes the physical result invalid and
    returns three ``nan`` values.  For a valid mass array with no particles in
    the aperture, the enclosed mass and total Jz are zero while the specific
    value is undefined (``nan``).
    """
    pos = np.asarray(pos_centered, dtype=float)
    vel = np.asarray(vel_centered, dtype=float)
    if mass is None:
        return math.nan, math.nan, math.nan
    try:
        m_all = np.asarray(mass, dtype=float)
    except (TypeError, ValueError):
        return math.nan, math.nan, math.nan
    if (pos.ndim != 2 or pos.shape[1] < 2 or vel.shape != pos.shape
            or m_all.ndim != 1 or len(m_all) != len(pos)
            or np.any(~np.isfinite(m_all)) or np.any(m_all < 0)):
        return math.nan, math.nan, math.nan
    if pos.shape[0] == 0:
        return 0.0, 0.0, math.nan
    r = np.linalg.norm(pos, axis=1)
    selected = np.isfinite(r) & (r < float(radius))
    if not np.any(selected):
        return 0.0, 0.0, math.nan
    m = m_all[selected]
    if np.any(~np.isfinite(pos[selected])) or np.any(~np.isfinite(vel[selected])):
        return math.nan, math.nan, math.nan
    enclosed_mass = float(np.sum(m))
    if not np.isfinite(enclosed_mass) or enclosed_mass < 0.0:
        return math.nan, math.nan, math.nan
    cross_z = (pos[selected, 0] * vel[selected, 1]
               - pos[selected, 1] * vel[selected, 0])
    total_jz = float(np.sum(m * cross_z))
    specific = total_jz / enclosed_mass if enclosed_mass > 0.0 else math.nan
    return total_jz, enclosed_mass, specific


def core_density(pos: np.ndarray, mass: np.ndarray, radius: float) -> float:
    r = np.linalg.norm(pos, axis=1)
    m = r < radius
    vol = 4.0 / 3.0 * math.pi * radius**3
    return float(mass[m].sum() / vol) if vol > 0 else math.nan


def ninteractions_info(snap_path: Path, ptype: int) -> Tuple[int, float, float, float, int]:
    total, frac, mean_nz, p90_nz, mx = 0, 0.0, 0.0, 0.0, 0
    try:
        with h5py.File(snap_path, "r") as f:
            g = f[f"PartType{ptype}"]
            if "NInteractions" in g:
                n = np.asarray(g["NInteractions"][:]).ravel()
                total = int(n.sum())
                frac = float((n > 0).mean()) if len(n) else 0.0
                nz = n[n > 0]
                if len(nz):
                    mean_nz = float(nz.mean())
                    p90_nz = float(np.percentile(nz, 90))
                    mx = int(nz.max())
    except Exception:
        pass
    return total, frac, mean_nz, p90_nz, mx


def find_nearest_sync(time: float,
                      points: Iterable[SyncPoint]) -> Tuple[int, float]:
    if points is None or not math.isfinite(float(time)):
        return -1, math.nan
    iterator = iter(points)
    try:
        best = next(iterator)
    except StopIteration:
        return -1, math.nan
    for point in iterator:
        if (abs(point.time - time), point.time, point.sync, point.step) < \
                (abs(best.time - time), best.time, best.sync, best.step):
            best = point
    return best.sync, best.step

def read_series_metric(snap: Path, ptype: int,
                      log_points: Sequence[SyncPoint]) -> SeriesMetric:
    """Метрики одного снапшота серии (read_metric из analyze_series.py)."""
    from analysis.loaders.snapshots import (_snapshot_number as _sn,
                                            resolve_particle_masses)
    with h5py.File(snap, "r") as f:
        g = f[f"PartType{ptype}"]
        pos = np.asarray(g["Coordinates"][:], dtype=float)
        vel = np.asarray(g["Velocities"][:], dtype=float)
        mass = resolve_particle_masses(g, f["Header"].attrs, ptype)
        if mass is not None:
            mass = np.asarray(mass, dtype=float)
        t = float(f["Header"].attrs.get("Time", math.nan))
    # Geometry can retain the historical particle-weighted fallback when a
    # snapshot has no mass information, but no physical Jz/M is reported in
    # that case.  Known masses are used for the same shrinkage center as shape
    # metrics and for the bulk-velocity frame below.
    mass_valid = (mass is not None and mass.ndim == 1 and len(mass) == len(pos)
                  and np.all(np.isfinite(mass)) and np.all(mass >= 0.0)
                  and (len(mass) == 0 or float(np.sum(mass)) > 0.0))
    geometry_mass = (mass if mass_valid
                     else np.ones(len(pos), dtype=float))
    center = weighted_center(pos, geometry_mass)
    pos_c = pos - center
    ba2, ca2 = shape_ratios(pos_c, geometry_mass, 2.0)
    ba5, ca5 = shape_ratios(pos_c, geometry_mass, 5.0)
    ba10, ca10 = shape_ratios(pos_c, geometry_mass, 10.0)
    zr_rms, zr_p68 = thickness_stats(pos_c, 5.0)
    if mass_valid and len(pos):
        bulk = np.average(vel, axis=0, weights=mass)
        vel_c = vel - bulk
    elif len(pos):
        # This is only for legacy geometric/rotation diagnostics.  The
        # physical moment below remains invalid when masses are unavailable.
        vel_c = vel - np.mean(vel, axis=0)
    else:
        vel_c = vel
    mv, medv, sigv, vsup = rotation_stats(pos_c, vel_c, 5.0)
    jz, jz_mass, jz_specific = angular_momentum_stats(
        pos_c, vel_c, mass if mass_valid else None, 5.0)
    ni_tot, ni_frac, ni_mean, ni_p90, ni_max = ninteractions_info(snap, ptype)
    sync, step = find_nearest_sync(t, log_points)
    return SeriesMetric(
        snapshot=_sn(str(snap)), file=snap.name, time=t,
        particles=int(len(pos)),
        rho_core_r1=(core_density(pos_c, mass, 1.0)
                     if mass_valid else math.nan),
        rho_core_r2=(core_density(pos_c, mass, 2.0)
                     if mass_valid else math.nan),
        rho_core_r5=(core_density(pos_c, mass, 5.0)
                     if mass_valid else math.nan),
        ba_r2=ba2, ca_r2=ca2, ba_r5=ba5, ca_r5=ca5, ba_r10=ba10, ca_r10=ca10,
        z_rms_over_R_rms_r5=zr_rms, z_p68_over_R_p68_r5=zr_p68,
        mean_vphi_r5=mv, median_vphi_r5=medv, sigma_vphi_r5=sigv,
        vrot_over_sigma_r5=vsup,
        ninteractions_total=ni_tot, interacted_fraction=ni_frac,
        ninteractions_mean_nonzero=ni_mean, ninteractions_p90_nonzero=ni_p90,
        ninteractions_max=ni_max,
        nearest_sync_point=sync, nearest_systemstep=step,
        jz_total_r5=jz, jz_mass_r5=jz_mass,
        jz_per_mass_r5=jz_specific)


def write_metrics_csv(metrics: List[SeriesMetric], path: Path) -> None:
    """Write a stable metrics schema, including a header for empty series."""
    from dataclasses import fields

    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [field.name for field in fields(SeriesMetric)]
    with path.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        for m in metrics:
            w.writerow(asdict(m))


def prepare_series_frames(run_root: Path, ptype: int = 3,
                          max_frames: Optional[int] = None) -> List[Dict]:
    """Кадры contact-sheet (downsample x-y/x-z + vphi) — данные для plots."""
    from analysis.loaders.snapshots import _snapshot_number
    snaps = list_series_snapshots(run_root)
    idx = set(range(len(snaps)))
    if max_frames and len(snaps) > max_frames:
        idx = set(np.round(np.linspace(0, len(snaps) - 1, max_frames)).astype(int))
    frames: List[Dict] = []
    for i, snap in enumerate(snaps):
        if i not in idx:
            continue
        with h5py.File(snap, "r") as f:
            g = f[f"PartType{ptype}"]
            pos = np.asarray(g["Coordinates"][:], dtype=float)
            vel = np.asarray(g["Velocities"][:], dtype=float)
        center = weighted_center(pos, np.ones(len(pos)))
        pos_c = pos - center
        n = len(pos_c)
        take = np.random.RandomState(7).choice(
            n, size=min(n, 20000), replace=False) if n > 20000 else np.arange(n)
        frames.append({"xy": pos_c[take][:, [0, 1]], "xz": pos_c[take][:, [0, 2]],
                       "vphi": rotation_stats(pos_c, vel, 5.0)[0],
                       "snapshot": _sn(str(snap))})
    return frames

def classify_series(metrics: List[SeriesMetric]) -> Tuple[str, List[str]]:
    """Вердикт по частичной серии (classify_series из analyze_series.py)."""
    times = np.array([m.time for m in metrics], dtype=float)
    cas = np.array([m.ca_r5 for m in metrics], dtype=float)
    thick = np.array([m.z_rms_over_R_rms_r5 for m in metrics], dtype=float)
    support = np.array([m.vrot_over_sigma_r5 for m in metrics], dtype=float)
    rhos = np.array([m.rho_core_r2 for m in metrics], dtype=float)
    steps = np.array([m.nearest_systemstep for m in metrics], dtype=float)
    finite = np.isfinite(times)
    for arr in (cas, thick, support, rhos, steps):
        finite &= np.isfinite(arr)
    notes: List[str] = []
    if not finite.any():
        return "no-usable-metrics", ["No finite metrics in series."]
    t, ca, th, sup, rh, st = (a[finite] for a in
                              (times, cas, thick, support, rhos, steps))
    order = np.argsort(t)
    t, ca, th, sup, rh, st = t[order], ca[order], th[order], sup[order], rh[order], st[order]
    notes.append(f"Series covers {len(t)} snapshots t={t[0]:.3f}..{t[-1]:.3f}.")
    notes.append(f"c/a(r<5): start={ca[0]:.3f} min={ca.min():.3f} final={ca[-1]:.3f}.")
    notes.append(f"z/R(r<5): start={th[0]:.3f} min={th.min():.3f} final={th[-1]:.3f}.")
    notes.append(f"|vrot|/sigma(r<5): start={sup[0]:.3f} max={sup.max():.3f} "
                 f"final={sup[-1]:.3f}.")
    if np.isfinite(rh[0]) and rh[0] > 0:
        notes.append(f"rho_core(r<2): start={rh[0]:.4g} final={rh[-1]:.4g} "
                     f"(x{rh[-1]/rh[0]:.2f}).")
    # The first snapshot can be paired with an initial sync marker whose
    # Systemstep is a zero placeholder.  It must not veto the physical
    # timestep-collapse check; only finite, strictly positive steps are
    # meaningful for the ``< 1e-6`` pathology threshold.
    positive_steps = st[np.isfinite(st) & (st > 0)]
    min_step = float(positive_steps.min()) if positive_steps.size else math.nan
    notes.append(f"nearest systemstep: min={min_step:.3g} final={st[-1]:.3g}.")
    if len(t) >= 3:
        slope, _ = np.polyfit(t, ca, 1)
        notes.append(f"c/a trend d(c/a)/dt={slope:.4g} per code time unit.")
    min_ca, min_thick = float(ca.min()), float(th.min())
    max_support = float(sup.max())
    if (np.isfinite(min_ca) and min_ca < 0.45 and np.isfinite(min_thick)
            and min_thick < 0.35 and np.isfinite(max_support) and max_support > 0.6
            and (not np.isfinite(min_step) or min_step >= 1e-6)):
        verdict = "disk-like-candidate"
        notes.append("Interpretation: sustained flattening with rotation support "
                     "and no timestep collapse looks disk-like; confirm with "
                     "controls rather than a stable disk.")
    elif np.isfinite(min_ca) and min_ca < 0.45 and np.isfinite(max_support) \
            and max_support > 0.4 and (not np.isfinite(min_step) or min_step >= 1e-6):
        verdict = "promising-disk-like"
        notes.append("Interpretation: flattening with rotation support and no "
                     "severe timestep collapse looks promising.")
    elif np.isfinite(min_step) and min_step < 1e-6 \
            and (not np.isfinite(min_ca) or min_ca > 0.55):
        verdict = "no-disk-before-pathology"
        notes.append("Interpretation: numerical pathology appears before clear "
                     "disk-like flattening.")
    else:
        verdict = "ambiguous-partial-series"
        notes.append("Interpretation: partial data are ambiguous; inspect static "
                     "contact sheets and metrics before choosing next parameters.")
    return verdict, notes


def write_series_summary(metrics: List[SeriesMetric], verdict: str,
                         notes: List[str], out: Path, made: Iterable[Path]) -> None:
    lines = ["PARTIAL SERIES DIAGNOSTIC SUMMARY", f"Verdict: {verdict}", "",
             "Key notes:"] + [f"- {n}" for n in notes] + ["", "Generated files:"]
    lines += [f"- {p.name} ({p.stat().st_size} bytes)" for p in made if p.exists()]
    lines += ["",
              "Agent note: GIF/animation viewing is not used for verdict; "
              "conclusions are based on CSV/TXT metrics and static PNG outputs."]
    out.write_text("\n".join(lines) + "\n")

# ──────────────────── compare_shape_series.py (метрики сравнения) ───────────────

SHAPE_KEYS = [
    "ca_r5",
    "ca_r10",
    "z_rms_over_R_rms_r5",
    "z_p68_over_R_p68_r5",
    "vrot_over_sigma_r5",
    "mean_vphi_r5",
    "rho_core_r2",
    "ninteractions_total",
    "interacted_fraction",
]


@dataclass
class ShapeSummary:
    run: str
    time_start: float
    time_final: float
    snapshots: int
    ca_r5_initial: float
    ca_r5_final: float
    ca_r5_min: float
    ca_r10_final: float
    thickness_r5_final: float
    thickness_p68_r5_final: float
    vrot_over_sigma_r5_final: float
    mean_vphi_r5_final: float
    rho_core_r2_growth: float
    ninteractions_final: int
    interacted_fraction_final: float
    disk_score: float
    verdict: str


def _sfloat(row: Dict[str, str], key: str, default: float = math.nan) -> float:
    try:
        return float(row.get(key, default))
    except Exception:
        return default


def _sint(row: Dict[str, str], key: str, default: int = 0) -> int:
    try:
        return int(float(row.get(key, default)))
    except Exception:
        return default


def read_shape_metrics(path: Path) -> List[Dict[str, str]]:
    if not path.exists():
        raise FileNotFoundError(path)
    with path.open(newline="") as f:
        rows = list(csv.DictReader(f))
    if not rows:
        raise ValueError(f"empty metrics file: {path}")
    return rows


def resolve_metrics_path(run_root: Path, metrics_rel: str) -> Path:
    """Resolve a series CSV from canonical or legacy analysis locations.

    Explicit existing paths keep priority.  The default legacy relative path
    remains accepted for old runs, while new runner output is read from
    ``AnalysisPaths.prerun_dir(run_root.name)``.
    """
    run_root = Path(run_root)
    requested = run_root / metrics_rel
    if requested.exists():
        return requested
    if metrics_rel == "partial_analysis/metrics_series.csv":
        from analysis.paths import AnalysisPaths
        canonical = AnalysisPaths().prerun_dir(run_root.name) / "metrics_series.csv"
        if canonical.exists():
            return canonical
    return requested


def summarize_shape_run(run_root: Path, metrics_rel: str) -> ShapeSummary:
    rows = read_shape_metrics(resolve_metrics_path(run_root, metrics_rel))
    first, last = rows[0], rows[-1]
    ca_series = [_sfloat(r, "ca_r5") for r in rows]
    finite_ca = [x for x in ca_series if math.isfinite(x)]
    ca_min = min(finite_ca) if finite_ca else math.nan
    ca_f = _sfloat(last, "ca_r5")
    thick_f = _sfloat(last, "z_rms_over_R_rms_r5")
    vrot_f = _sfloat(last, "vrot_over_sigma_r5")
    rho0 = _sfloat(first, "rho_core_r2")
    rhof = _sfloat(last, "rho_core_r2")
    rho_growth = rhof / rho0 if rho0 and math.isfinite(rho0) and rho0 > 0 else math.nan
    disk_score = 0.0
    if math.isfinite(ca_f):
        disk_score += max(0.0, 0.75 - ca_f)
    if math.isfinite(thick_f):
        disk_score += max(0.0, 0.55 - thick_f)
    if math.isfinite(vrot_f):
        disk_score += 0.5 * max(0.0, vrot_f - 0.15)
    if disk_score >= 0.35 and math.isfinite(vrot_f) and vrot_f >= 0.25:
        verdict = "disk-candidate"
    elif disk_score >= 0.15:
        verdict = "worth-follow-up"
    else:
        verdict = "no-disk-signature"
    return ShapeSummary(
        run=run_root.name,
        time_start=_sfloat(first, "time"), time_final=_sfloat(last, "time"),
        snapshots=len(rows),
        ca_r5_initial=_sfloat(first, "ca_r5"), ca_r5_final=ca_f, ca_r5_min=ca_min,
        ca_r10_final=_sfloat(last, "ca_r10"),
        thickness_r5_final=thick_f,
        thickness_p68_r5_final=_sfloat(last, "z_p68_over_R_p68_r5"),
        vrot_over_sigma_r5_final=vrot_f,
        mean_vphi_r5_final=_sfloat(last, "mean_vphi_r5"),
        rho_core_r2_growth=rho_growth,
        ninteractions_final=_sint(last, "ninteractions_total"),
        interacted_fraction_final=_sfloat(last, "interacted_fraction"),
        disk_score=disk_score, verdict=verdict)

def discover_shape_runs(group_root: Path,
                        runs: Optional[List[str]]) -> List[Path]:
    if runs:
        return [group_root / r for r in runs]
    found = []
    for run in sorted(group_root.iterdir()):
        if run.is_dir() and resolve_metrics_path(
                run, "partial_analysis/metrics_series.csv").exists():
            found.append(run)
    return found


def write_shape_summary_csv(summaries: List[ShapeSummary], path: Path) -> None:
    with path.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(asdict(summaries[0]).keys()))
        w.writeheader()
        for s in summaries:
            w.writerow(asdict(s))


def write_shape_text_report(summaries: List[ShapeSummary], path: Path,
                            group_root: Path) -> str:
    def fmt(x):
        return f"{x:.3f}" if isinstance(x, float) and math.isfinite(x) else "nan"
    best = max(summaries, key=lambda s: (s.disk_score, s.ninteractions_final))
    lines = [f"Shape/thickness comparison: {group_root}", "",
             "| run | snaps | t_final | c/a_r5_f | thick_r5_f | vrot/sig_f | "
             "NI_total | score | verdict |",
             "| --- | --- | --- | --- | --- | --- | --- | --- | --- |"]
    for s in summaries:
        lines.append(
            f"| {s.run} | {s.snapshots} | {fmt(s.time_final)} | {fmt(s.ca_r5_final)} "
            f"| {fmt(s.thickness_r5_final)} | {fmt(s.vrot_over_sigma_r5_final)} "
            f"| {s.ninteractions_final} | {fmt(s.disk_score)} | {s.verdict}")
    lines.append("")
    if best.disk_score > 0:
        lines.append(f"Best disk-score candidate: {best.run} "
                     f"(score={fmt(best.disk_score)})")
    else:
        lines.append("Best disk-score candidate: none (all scores are 0)")
    lines += [
        "Interpretation: score is a follow-up ranking, not a detection claim.",
        "A robust dark disk would require low c/a, low z/R, and significant "
        "rotation support relative to controls.",
        f"CSV: {path.with_name('shape_summary.csv')}",
    ]
    text = "\n".join(lines) + "\n"
    path.write_text(text)
    return text


def prepare_shape_figure_data(runs: List[Path], metrics_rel: str) -> Dict[str, list]:
    """Данные 5 compare-панелей shape_compare для plots/prerun.py (shape_panel)."""
    specs = [
        ("c/a r<5", "ca_r5"),
        ("z_rms/R_rms r<5", "z_rms_over_R_rms_r5"),
        ("|vrot|/sigma r<5", "vrot_over_sigma_r5"),
        ("NInteractions total", "ninteractions_total"),
        ("rho_core r<2", "rho_core_r2"),
    ]
    panels = []
    for title, key in specs:
        series = []
        for run in runs:
            rows = read_shape_metrics(resolve_metrics_path(run, metrics_rel))
            series.append({
                "label": run.name.replace("_N1e5_T2", ""),
                "time": np.asarray([_sfloat(r, "time") for r in rows]),
                "value": np.asarray([_sfloat(r, key) for r in rows])})
        panels.append({"title": title, "key": key, "series": series})
    return {"panels": panels}
