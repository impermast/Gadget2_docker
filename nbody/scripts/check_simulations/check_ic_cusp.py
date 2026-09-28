#!/usr/bin/env python3
"""check_ic_cusp.py — физическая gate-проверка разрешимости каспа в GalIC IC.

v2 проверяет:
  1) target-профиль берётся из ФАКТИЧЕСКОГО вывода GalIC (rotcurve.txt) + NFW-фит;
  2) измеренный профиль IC сравнивается с target в центральной области
     (по умолчанию 0.3-3 kpc): медиана rho_meas/rho_target ~ 1;
  3) локальный наклон должен быть касповым (<= -0.75) и близок к target (<=0.25);
  4) разрешение: частиц в бинах, N(<r), t_relax (критерий Power et al. 2003).

Usage:
  python3 check_ic_cusp.py <ic.hdf5> [--galic-dir DIR] [--outdir DIR]
                           [--nmin 200] [--rlo 0.3] [--rhi 3.0]

Units: kpc, 1e10 Msun, km/s  ->  G_CODE = 4.301e4
Exit code: 0 = PASS, 2 = FAIL, 1 = ошибка входных данных.
"""
import argparse
import glob
import json
import os
import sys

import numpy as np
import h5py

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
    """NFW-фит (rho_s, r_s) к фактической rotcurve GalIC (по v_circ^2)."""
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


def read_particles(path):
    """Позиции/массы (PartType3 или 1) + r от COM."""
    with h5py.File(path, "r") as f:
        key = "PartType3" if "PartType3" in f else ("PartType1" if "PartType1" in f else None)
        if key is None:
            raise RuntimeError("нет PartType3/PartType1 в %s" % path)
        g = f[key]
        pos = g["Coordinates"][:]
        mass = g["Masses"][:] if "Masses" in g else np.full(len(pos), 1.0)
        hdr = dict(f["Header"].attrs)
    com = np.mean(pos, axis=0)
    r = np.linalg.norm(pos - com, axis=1)
    return r, mass, pos, com, hdr


def binned_profile(r, mass, rmin, rmax, nbins=60):
    edges = np.logspace(np.log10(rmin), np.log10(rmax), nbins + 1)
    vol = (4.0 / 3.0) * np.pi * np.diff(edges**3)
    idx = np.digitize(r, edges) - 1
    ok = (idx >= 0) & (idx < len(vol))
    cnt = np.bincount(idx[ok], minlength=len(vol))
    mm = np.bincount(idx[ok], weights=mass[ok], minlength=len(vol))
    with np.errstate(divide="ignore", invalid="ignore"):
        rho = np.where(vol > 0, mm / vol, np.nan)
    centers = np.sqrt(edges[1:] * edges[:-1])
    return centers, rho, cnt


def t_relax_gyr(n_in, m_in, r):
    """t_relax ~ 0.1 * N/lnN * t_orb (Power et al. 2003), в Gyr."""
    if n_in < 20:
        return float("nan")
    v_c = np.sqrt(G_CODE * m_in / r)
    t_orb = 2.0 * np.pi * r / v_c
    return 0.1 * n_in / np.log(n_in) * t_orb * TIME_UNIT_GYR


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("ic")
    ap.add_argument("--galic-dir", default=None)
    ap.add_argument("--outdir", default=None)
    ap.add_argument("--nmin", type=int, default=200)
    ap.add_argument("--rlo", type=float, default=0.3)
    ap.add_argument("--rhi", type=float, default=3.0)
    args = ap.parse_args()

    outdir = args.outdir or os.path.dirname(os.path.abspath(args.ic))
    os.makedirs(outdir, exist_ok=True)
    galic_dir = find_galic_dir(args.ic, args.galic_dir)

    r, mass, _pos, _com, _hdr = read_particles(args.ic)

    m_p = float(np.mean(mass))
    r_min = max(float(r.min()) * 1.15, 0.02)
    centers, rho, cnt = binned_profile(r, mass, r_min, 20.0)

    lines, result = [], {"ic": args.ic, "galic_dir": galic_dir, "N": int(len(r)),
                         "m_p": m_p, "r_min": r_min}
    lines.append("IC gate report (check_ic_cusp.py v2)")
    lines.append("=" * 64)
    lines.append(f"IC:           {args.ic}")
    lines.append(f"N:            {len(r)}   m_p = {m_p:.4e} (1e10 Msun)")
    lines.append(f"GalIC output: {galic_dir or 'NOT FOUND'}")

    rho_target, slope_target = None, None
    if galic_dir and os.path.isfile(os.path.join(galic_dir, "rotcurve.txt")):
        r_t, v_t = read_rotcurve(galic_dir)
        m_t, rho_t = target_profile_from_rotcurve(r_t, v_t)
        rho_s, r_s, rms = fit_nfw_to_rotcurve(r_t, v_t)
        params = read_galic_params(galic_dir)
        i_pk = int(np.argmax(v_t))
        lines.append(f"GalIC params (fact): CC={params.get('CC')}  "
                     f"V200={params.get('V200')} km/s")
        lines.append(f"NFW fit to rotcurve: r_s={r_s:.3f} kpc  rho_s={rho_s:.4e}  "
                     f"rms(v^2)={rms:.4g}")
        lines.append(f"rotcurve: v_max={v_t[i_pk]:.1f} km/s @ {r_t[i_pk]:.2f} kpc, "
                     f"r range [{r_t[0]:.3f}, {r_t[-1]:.1f}] kpc")
        result["galic_params"] = params
        result["nfw_fit"] = {"r_s_kpc": float(r_s), "rho_s": float(rho_s),
                             "rms_v2": float(rms)}
        x = centers / r_s
        rho_target = rho_s / (x * (1 + x) ** 2)
        m_target = 4 * np.pi * rho_s * r_s**3 * (np.log(1 + x) - x / (1 + x))
        slope_target = local_slope(centers, rho_target)
        result["M_target_2kpc"] = float(np.interp(2.0, centers, m_target))
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
    gate = (centers >= args.rlo) & (centers <= args.rhi) & (cnt >= args.nmin) & \
           np.isfinite(rho) & (rho > 0)

    if rho_target is not None and int(gate.sum()) >= 3:
        ratio = rho[gate] / rho_target[gate]
        med_ratio = float(np.median(ratio))
        slope_gate = float(np.nanmedian(slope[gate]))
        slope_tgt = float(np.nanmedian(slope_target[gate]))
        lines.append("")
        lines.append(f"Central gate: {args.rlo}-{args.rhi} kpc, "
                     f"{int(gate.sum())} bins with N>={args.nmin}")
        lines.append(f"  median rho_meas/rho_target = {med_ratio:.3f}  (expect 1.00 +-0.15)")
        lines.append(f"  median local slope (meas)  = {slope_gate:+.3f}")
        lines.append(f"  median local slope (target)= {slope_tgt:+.3f}")
        lines.append(f"  |Delta slope|              = {abs(slope_gate - slope_tgt):.3f} (<=0.25)")
        checks["ratio_ok"] = abs(med_ratio - 1.0) <= 0.15
        checks["cusp_ok"] = slope_gate <= -0.75
        checks["slope_match"] = abs(slope_gate - slope_tgt) <= 0.25
        checks["min_count_ok"] = int(cnt[gate].min()) >= args.nmin
        result.update({"median_ratio": med_ratio, "slope_meas": slope_gate,
                       "slope_target": slope_tgt, "gate_bins": int(gate.sum())})
    else:
        checks["enough_bins"] = False
        lines.append("")
        lines.append("FAIL: недостаточно разрешённых бинов в центральной области "
                     "(или нет target) — увеличить N / изменить область.")

    n_1kpc = result.get("N_lt_1.0", 0)
    t_relax_1 = result.get("t_relax_1.0", float("nan"))
    checks["resolution_ok"] = bool(n_1kpc >= 1e5 and t_relax_1 >= 10.0)
    lines.append("")
    lines.append(f"Resolution: N(<1 kpc)={n_1kpc} (need >=1e5), "
                 f"t_relax(1 kpc)={t_relax_1:.1f} Gyr (need >=10)")

    ok = all(checks.values())
    lines.append("")
    for k, v in checks.items():
        lines.append(f"  [{'PASS' if v else 'FAIL'}] {k}")
    lines.append("")
    lines.append(f"GATE: {'PASS' if ok else 'FAIL'}")
    result["checks"] = checks
    result["gate_pass"] = ok

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

    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        fig, ax = plt.subplots(1, 3, figsize=(15, 4.5))
        good = (rho > 0) & (cnt > 0)
        ax[0].loglog(centers[good], rho[good], "o-", ms=3, label="GalIC IC (measured)")
        if rho_target is not None:
            ax[0].loglog(centers, rho_target, "k--", label="target (NFW fit to rotcurve)")
        ax[0].axvspan(args.rlo, args.rhi, color="0.85", alpha=0.5, label="gate range")
        ax[0].set_xlabel("r [kpc]")
        ax[0].set_ylabel("rho [1e10 Msun/kpc^3]")
        ax[0].legend(fontsize=8)
        ax[0].set_title("density profile")
        ax[1].semilogx(centers, slope, "o-", ms=3, label="measured")
        if slope_target is not None:
            ax[1].semilogx(centers, slope_target, "k--", label="target")
        ax[1].axhline(-1.0, color="r", ls=":", lw=1)
        ax[1].axvspan(args.rlo, args.rhi, color="0.85", alpha=0.5)
        ax[1].set_xlabel("r [kpc]")
        ax[1].set_ylabel("d log rho / d log r")
        ax[1].legend(fontsize=8)
        ax[1].set_title("local logarithmic slope")
        ax[2].loglog(centers, cnt, "o-", ms=3)
        ax[2].axhline(args.nmin, color="r", ls=":")
        ax[2].axvspan(args.rlo, args.rhi, color="0.85", alpha=0.5)
        ax[2].set_xlabel("r [kpc]")
        ax[2].set_ylabel("particles per bin")
        ax[2].set_title("radial resolution")
        fig.tight_layout()
        fig.savefig(os.path.join(outdir, "ic_gate_profile.png"), dpi=130)
    except Exception as exc:  # noqa: BLE001 - plot не должен ломать gate
        lines.append(f"(plot skipped: {exc})")

    print("\n".join(lines))
    sys.exit(0 if ok else 2)


if __name__ == "__main__":
    main()
