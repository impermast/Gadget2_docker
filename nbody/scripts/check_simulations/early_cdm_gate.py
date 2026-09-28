#!/usr/bin/env python3
"""early_cdm_gate.py — ранний физический gate по первому эволюционировавшему
CDM-снапшоту (или по любой паре IC/snapshot) для кампании corecusp.

Сравнивает: analytic target (NFW-фит к фактической rotcurve GalIC) vs GalIC IC vs
первый CDM snapshot. Проверяет:
  * radial density profile, локальный лог-наклон и его отклонение от target;
  * enclosed mass / N(<r);
  * центр системы и bulk drift (нет ли остаточного импульса/дрейфа);
  * изменение центральной плотности и наклона (нет ли мгновенного core formation);
  * вириальные/энергетические диагностики (2T/|W|, сохранение полной энергии);
  * timestep/softening sanity (по run.log и блокам снапшота).

Usage:
  python3 early_cdm_gate.py --ic IC.hdf5 --snap snapshot_000.hdf5 \
      [--galic-dir DIR] [--run-log DIR/run.log.early] [--outdir DIR]

Exit code: 0 = PASS, 2 = FAIL, 1 = ошибка входных данных.
"""
import argparse
import glob
import json
import os
import re
import sys

import numpy as np
import h5py

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from check_ic_cusp import (  # noqa: E402
    G_CODE,
    TIME_UNIT_GYR,
    find_galic_dir,
    read_galic_params,
    read_rotcurve,
    fit_nfw_to_rotcurve,
    local_slope,
    binned_profile,
    t_relax_gyr,
    rho_target_in_bins,
    potential_energy_from_rotcurve,
)


# ---------------------------------------------------------------- utilities
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
        mass = g["Masses"][:] if "Masses" in g else np.full(len(pos), 1.0)
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
    """T = 0.5 * sum m v^2 относительно bulk-скорости (units: 1e10 Msun (km/s)^2)."""
    v = state["vel"] - bulk_velocity(state)
    return float(0.5 * np.sum(state["mass"] * np.sum(v**2, axis=1)))


def potential_energy_from_block(state):
    """W = 0.5 * sum m Phi из блока Potential (GIZMO пишет Phi в (km/s)^2)."""
    if state["potential"] is None:
        return None
    return float(0.5 * np.sum(state["mass"] * state["potential"]))


_trapz = getattr(np, "trapezoid", None) or np.trapz  # numpy<2 / >=2 совместимость


def potential_energy_target_nfw(rho_s, r_s, rmax=30.0, n=4000):
    """W для сферического NFW: W = -4 pi G int rho(r) M(<r) r dr."""
    r = np.logspace(np.log10(max(r_s / 100.0, 1e-3)), np.log10(rmax), n)
    x = r / r_s
    rho = rho_s / (x * (1 + x) ** 2)
    m_in = 4 * np.pi * rho_s * r_s**3 * (np.log(1 + x) - x / (1 + x))
    integrand = rho * m_in * r
    return float(-4 * np.pi * G_CODE * _trapz(integrand, r))


def parse_log_steps(log_path):
    """Шаги/тайминги из run.log (строки 'Sync-Point N, Time: t, Systemstep: dt')."""
    times, dts = [], []
    if log_path and os.path.isfile(log_path):
        pat = re.compile(r"Sync-Point\s+(\d+),\s*Time:\s*([0-9.eE+-]+),"
                         r"\s*Systemstep:\s*([0-9.eE+-]+)")
        with open(log_path, "r", errors="ignore") as fh:
            for line in fh:
                m = pat.search(line)
                if m:
                    times.append(float(m.group(2)))
                    dts.append(float(m.group(3)))
    return np.array(times), np.array(dts)
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ic", required=True)
    ap.add_argument("--snap", required=True)
    ap.add_argument("--galic-dir", default=None)
    ap.add_argument("--run-log", default=None)
    ap.add_argument("--outdir", default=None)
    ap.add_argument("--nmin", type=int, default=200)
    ap.add_argument("--rlo", type=float, default=0.3)
    ap.add_argument("--rhi", type=float, default=3.0)
    ap.add_argument("--drho-tol", type=float, default=0.05)    # 5% на центральную плотность
    ap.add_argument("--dslope-tol", type=float, default=0.20)  # размывание каспа
    args = ap.parse_args()

    outdir = args.outdir or os.path.dirname(os.path.abspath(args.snap))
    os.makedirs(outdir, exist_ok=True)
    galic_dir = find_galic_dir(args.ic, args.galic_dir)

    ic = read_state(args.ic, want_potential=False)
    sn = read_state(args.snap)
    m_p = float(np.mean(ic["mass"]))
    t_snap = float(sn["header"].get("Time", float("nan")))
    r_min = max(float(np.min(np.linalg.norm(ic["pos"] - ic["pos"].mean(0), axis=1))) * 1.15,
                0.02)

    ic_center, r_ic = com_and_radius(ic)
    sn_center, r_sn = com_and_radius(sn)
    centers, rho_ic, cnt_ic, edges = binned_profile(r_ic, ic["mass"], r_min, 20.0)
    _, rho_sn, cnt_sn, _ = binned_profile(r_sn, sn["mass"], r_min, 20.0)
    slope_ic = local_slope(centers, rho_ic)
    slope_sn = local_slope(centers, rho_sn)

    lines, res = [], {"ic": args.ic, "snap": args.snap, "t_snap": t_snap,
                      "galic_dir": galic_dir, "N": int(len(r_ic)), "m_p": m_p}
    lines.append("Early CDM gate report (early_cdm_gate.py)")
    lines.append("=" * 70)
    lines.append(f"IC:   {args.ic}")
    lines.append(f"snap: {args.snap}   Time = {t_snap:.6f} "
                 f"(~{t_snap * TIME_UNIT_GYR:.1f} Gyr)")
    lines.append(f"N snap: {len(r_sn)}  (IC N: {len(r_ic)})   m_p = {m_p:.4e} (1e10 Msun)")

    rho_target = slope_target = None
    r_t = v_t = None
    if galic_dir and os.path.isfile(os.path.join(galic_dir, "rotcurve.txt")):
        r_t, v_t = read_rotcurve(galic_dir)
        params = read_galic_params(galic_dir)
        rho_s_fit, r_s_fit, rms = fit_nfw_to_rotcurve(r_t, v_t)  # только справочно
        # target — напрямую из фактической rotcurve GalIC, по тем же границам бинов
        rho_target = rho_target_in_bins(r_t, v_t, edges)
        slope_target = local_slope(centers, rho_target)
        res["nfw_fit"] = {"r_s_kpc": float(r_s_fit), "rho_s": float(rho_s_fit),
                          "rms_v2": float(rms), "used_for_checks": False}
        res["galic_params"] = params
        lines.append(f"target: rotcurve GalIC напрямую (v^2 r / G) "
                     f"[CC={params.get('CC')}, V200={params.get('V200')}]; "
                     f"справочно NFW-fit: r_s={r_s_fit:.3f} kpc rms(v^2)={rms:.4g}")
    else:
        lines.append("WARNING: target (rotcurve) не найден — сравнение с target пропущено")

    d_center = sn_center - ic_center
    v_ic, v_sn = bulk_velocity(ic), bulk_velocity(sn)
    lines.append("")
    lines.append("Center & bulk drift:")
    lines.append(f"  COM(IC)   = ({ic_center[0]:+.4f}, {ic_center[1]:+.4f}, {ic_center[2]:+.4f})")
    lines.append(f"  COM(snap) = ({sn_center[0]:+.4f}, {sn_center[1]:+.4f}, {sn_center[2]:+.4f})")
    lines.append(f"  |dCOM|    = {np.linalg.norm(d_center):.5f} kpc")
    lines.append(f"  v_bulk(IC)   = {np.array2string(v_ic, precision=3)} km/s "
                 f"|v|={np.linalg.norm(v_ic):.3f}")
    lines.append(f"  v_bulk(snap) = {np.array2string(v_sn, precision=3)} km/s "
                 f"|v|={np.linalg.norm(v_sn):.3f}")
    res["dCOM_kpc"] = float(np.linalg.norm(d_center))
    res["v_bulk_ic"] = [float(x) for x in v_ic]
    res["v_bulk_snap"] = [float(x) for x in v_sn]

    # ---------------- профили / сохранение каспа ----------------
    gate = (centers >= args.rlo) & (centers <= args.rhi) & \
           (cnt_ic >= args.nmin) & (cnt_sn >= args.nmin) & \
           np.isfinite(rho_ic) & np.isfinite(rho_sn) & (rho_ic > 0) & (rho_sn > 0)
    lines.append("")
    lines.append(f"Central gate range {args.rlo}-{args.rhi} kpc: "
                 f"{int(gate.sum())} bins with N>={args.nmin}")
    checks = {}
    if int(gate.sum()) >= 3:
        med_ratio = float(np.median(rho_ic[gate] / rho_sn[gate]))
        sl_ic = float(np.nanmedian(slope_ic[gate]))
        sl_sn = float(np.nanmedian(slope_sn[gate]))
        d_slope = sl_sn - sl_ic
        lines.append(f"  median slope IC    = {sl_ic:+.3f}")
        lines.append(f"  median slope snap  = {sl_sn:+.3f}   (Delta = {d_slope:+.3f}, "
                     f"tol {args.dslope_tol})")
        lines.append(f"  median rho_IC/rho_snap = {med_ratio:.4f} (tol {args.drho_tol:.0%})")
        checks["no_immediate_core"] = d_slope <= args.dslope_tol
        checks["central_density_stable"] = abs(med_ratio - 1.0) <= args.drho_tol
        if rho_target is not None:
            sl_tg = float(np.nanmedian(slope_target[gate]))
            r_tg = float(np.median(rho_sn[gate] / rho_target[gate]))
            lines.append(f"  median slope target = {sl_tg:+.3f}  "
                         f"(|snap-target| = {abs(sl_sn - sl_tg):.3f})")
            lines.append(f"  median rho_snap/rho_target = {r_tg:.4f}")
            res.update({"slope_target": sl_tg, "rho_snap_over_target": r_tg})
            checks["snap_matches_target"] = abs(sl_sn - sl_tg) <= args.dslope_tol + 0.10
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
    lines.append(f"  T(IC)   = {t_ic:.6e}     T(snap) = {t_sn:.6e}   dT/T = {(t_sn - t_ic) / t_ic:+.3e}")
    res.update({"T_ic": t_ic, "T_snap": t_sn})
    if w_sn is not None:
        lines.append(f"  W(snap) = {w_sn:.6e} (из блока Potential)   2T/|W| = {2 * t_sn / abs(w_sn):.4f}")
        res.update({"W_snap": w_sn, "virial_2T_W_snap": 2 * t_sn / abs(w_sn)})
        checks["virial_sane"] = bool(0.6 <= 2 * t_sn / abs(w_sn) <= 1.8)
    if r_t is not None:
        w_tg = potential_energy_from_rotcurve(r_t, v_t)
        if w_sn is not None:
            de = (t_sn + w_sn) - (t_ic + w_tg)
            lines.append(f"  W(target rotcurve) = {w_tg:.6e}   2T/|W|(IC,target) = "
                         f"{2 * t_ic / abs(w_tg):.4f}")
            lines.append(f"  dE/|W_target| = {de / abs(w_tg):+.3e}  (энергия IC+target-W vs snap)")
            res.update({"W_target": w_tg, "dE_over_W": de / abs(w_tg),
                        "virial_2T_W_ic_target": 2 * t_ic / abs(w_tg)})

    # ---------------- timestep / softening sanity ----------------
    times, dts = parse_log_steps(args.run_log)
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
        res.update({"n_steps": int(len(times)), "dt_min": float(pos_dt.min()) if len(pos_dt) else None,
                    "dt_max": float(pos_dt.max()) if len(pos_dt) else None})
    else:
        lines.append("  (run.log не найден/не распознан — timestep-проверка пропущена)")
    if sn["softening"] is not None:
        soft = sn["softening"]
        inner = r_sn < 1.0
        n_in = int(inner.sum())
        rho_mean = n_in / ((4.0 / 3.0) * np.pi * 1.0**3)
        spacing = rho_mean ** (-1.0 / 3.0)
        lines.append(f"  Softening_KernelRadius: min={soft.min():.4e} median={np.median(soft):.4e} "
                     f"(code units); inner(r<1kpc) median={np.median(soft[inner]):.4e}")
        lines.append(f"  среднее межчастичное расстояние (r<1 kpc) ~ {spacing:.4f} kpc "
                     f"(n={n_in})")
        res.update({"soft_min": float(soft.min()), "soft_median": float(np.median(soft)),
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
    lines.append("Next state: WAITING_FOR_REVIEW (production continuation НЕ запускается "
                 "автоматически)")
    res["checks"] = checks
    res["gate_pass"] = ok

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

    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        fig, ax = plt.subplots(1, 3, figsize=(16, 4.8))
        g_ic = (rho_ic > 0) & (cnt_ic > 0)
        g_sn = (rho_sn > 0) & (cnt_sn > 0)
        ax[0].loglog(centers[g_ic], rho_ic[g_ic], "o-", ms=3, label="GalIC IC")
        ax[0].loglog(centers[g_sn], rho_sn[g_sn], "s-", ms=3, label="first CDM snapshot")
        if rho_target is not None:
            ax[0].loglog(centers, rho_target, "k--", label="analytic target (NFW fit)")
        ax[0].axvspan(args.rlo, args.rhi, color="0.85", alpha=0.5, label="gate range")
        ax[0].set_xlabel("r [kpc]")
        ax[0].set_ylabel("rho [1e10 Msun/kpc^3]")
        ax[0].legend(fontsize=8)
        ax[0].set_title(f"density: IC vs snapshot (t={t_snap:.4g})")
        ax[1].semilogx(centers, slope_ic, "o-", ms=3, label="IC")
        ax[1].semilogx(centers, slope_sn, "s-", ms=3, label="snapshot")
        if slope_target is not None:
            ax[1].semilogx(centers, slope_target, "k--", label="target")
        ax[1].axhline(-1.0, color="r", ls=":", lw=1)
        ax[1].axvspan(args.rlo, args.rhi, color="0.85", alpha=0.5)
        ax[1].set_xlabel("r [kpc]")
        ax[1].set_ylabel("d log rho / d log r")
        ax[1].legend(fontsize=8)
        ax[1].set_title("local logarithmic slope")
        ax[2].semilogx(centers[centers > 0],
                       np.where(rho_sn > 0, rho_sn, np.nan)[centers > 0] /
                       np.where(rho_ic > 0, rho_ic, np.nan)[centers > 0],
                       "d-", ms=3, label="rho_snap/rho_IC")
        ax[2].axhline(1.0, color="r", ls=":")
        ax[2].axvspan(args.rlo, args.rhi, color="0.85", alpha=0.5)
        ax[2].set_xlabel("r [kpc]")
        ax[2].set_ylabel("ratio")
        ax[2].set_ylim(0.8, 1.2)
        ax[2].legend(fontsize=8)
        ax[2].set_title("density change (cusp preservation)")
        fig.tight_layout()
        fig.savefig(os.path.join(outdir, "cusp_compare.png"), dpi=130)
    except Exception as exc:  # noqa: BLE001
        lines.append(f"(plot skipped: {exc})")

    print("\n".join(lines))
    sys.exit(0 if ok else 2)


if __name__ == "__main__":
    main()

