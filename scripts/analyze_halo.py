#!/usr/bin/env python3
"""
SIDM halo analysis script.
Usage:
  python analyze_halo.py --cdm output_halo_cdm --sidm output_halo_sidm --rcore 50
  python analyze_halo.py --cdm output_halo_cdm  # single-run mode
"""
import argparse
import glob
import os
import re

import h5py
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.colors import LogNorm


# ─────────────────────────── I/O helpers ────────────────────────────────────

def list_snapshots(run_dir):
    files = sorted(glob.glob(os.path.join(run_dir, "snapshot*.hdf5")))
    if not files:
        raise FileNotFoundError(f"No HDF5 snapshots found in {run_dir}")
    return files


def snapshot_number(path):
    m = re.search(r"snapshot_?(\d+)\.hdf5$", os.path.basename(path))
    return int(m.group(1)) if m else -1


def latest_snapshot(run_dir):
    snaps = sorted(list_snapshots(run_dir), key=snapshot_number)
    return snaps[-1]


def read_snapshot(path, ptype=3):
    gname = f"PartType{ptype}"
    with h5py.File(path, "r") as f:
        if gname not in f:
            raise RuntimeError(f"{gname} not found in {path}. Available: {list(f.keys())}")
        g = f[gname]
        n_interact = None
        if "NInteractions" in g:
            n_interact = int(np.sum(g["NInteractions"][:]))
        data = {
            "pos":          g["Coordinates"][:].astype(np.float64),
            "vel":          g["Velocities"][:].astype(np.float64),
            "mass":         g["Masses"][:].astype(np.float64) if "Masses" in g else None,
            "ids":          g["ParticleIDs"][:] if "ParticleIDs" in g else None,
            "n_interact":   n_interact,
            "time":         float(f["Header"].attrs.get("Time", 0.0)),
            "boxsize":      float(f["Header"].attrs.get("BoxSize", 0.0)),
            "path":         path,
        }
    return data


# ──────────────────────── Centering & kinematics ────────────────────────────

def center_of_mass(pos, mass):
    if mass is None:
        return np.mean(pos, axis=0)
    msum = np.sum(mass)
    return np.sum(pos * mass[:, None], axis=0) / msum if msum > 0 else np.mean(pos, axis=0)


def center_velocity(vel, mass):
    if mass is None:
        return np.mean(vel, axis=0)
    msum = np.sum(mass)
    return np.sum(vel * mass[:, None], axis=0) / msum if msum > 0 else np.mean(vel, axis=0)


def centered_phase(data):
    pos = data["pos"].copy()
    vel = data["vel"].copy()
    mass = data["mass"]

    pos -= center_of_mass(pos, mass)
    vel -= center_velocity(vel, mass)

    r = np.linalg.norm(pos, axis=1)
    vr = np.zeros_like(r)
    mask = r > 0
    vr[mask] = np.einsum("ij,ij->i", pos[mask], vel[mask]) / r[mask]

    return pos, vel, r, vr


def log_bins(r, rmin=None, rmax=None, nbins=40):
    rr = r[r > 0]
    if len(rr) == 0:
        raise RuntimeError("No positive radii found.")
    rmin = max(rmin or np.percentile(rr, 1), 1e-6)
    rmax = rmax or np.percentile(rr, 99.5)
    return np.logspace(np.log10(rmin), np.log10(rmax), nbins + 1)


# ───────────────────────── Profile computation ──────────────────────────────

def radial_density_profile(data, nbins=40):
    _, _, r, _ = centered_phase(data)
    mass = data["mass"] if data["mass"] is not None else np.ones_like(r)
    edges = log_bins(r, nbins=nbins)
    centers = np.sqrt(edges[:-1] * edges[1:])
    rho = np.full(nbins, np.nan)
    for i in range(nbins):
        m = (r >= edges[i]) & (r < edges[i + 1])
        if np.any(m):
            vol = 4.0 / 3.0 * np.pi * (edges[i + 1] ** 3 - edges[i] ** 3)
            rho[i] = np.sum(mass[m]) / vol
    return centers, rho


def radial_sigma_profile(data, nbins=40):
    _, vel, r, _ = centered_phase(data)
    edges = log_bins(r, nbins=nbins)
    centers = np.sqrt(edges[:-1] * edges[1:])
    sigma = np.full(nbins, np.nan)
    for i in range(nbins):
        m = (r >= edges[i]) & (r < edges[i + 1])
        if np.any(m):
            vv = vel[m]
            sigma[i] = np.sqrt(sum(np.var(vv[:, k]) for k in range(3)) / 3.0)
    return centers, sigma


def log_slope_profile(r_centers, rho):
    """d log rho / d log r — should be ~0 in core, ~-3 in NFW cusp."""
    valid = np.isfinite(rho) & (rho > 0) & (r_centers > 0)
    slope = np.full_like(rho, np.nan)
    if np.sum(valid) < 3:
        return slope
    log_r = np.log10(r_centers[valid])
    log_rho = np.log10(rho[valid])
    # central difference
    d_log_rho = np.gradient(log_rho, log_r)
    slope[valid] = d_log_rho
    return slope


def core_density(data, rcore=50.0):
    _, _, r, _ = centered_phase(data)
    mass = data["mass"] if data["mass"] is not None else np.ones_like(r)
    m = r < rcore
    if not np.any(m):
        return np.nan
    return np.sum(mass[m]) / (4.0 / 3.0 * np.pi * rcore ** 3)


# ──────────────────────────── NFW / core fits ───────────────────────────────

def nfw_profile(r, rho0, rs):
    x = r / rs
    return rho0 / (x * (1 + x) ** 2)


def core_profile(r, rho0, rc):
    """Isothermal core: rho0 / (1 + (r/rc)^2)"""
    return rho0 / (1.0 + (r / rc) ** 2)


def _lm_fit(func, r, rho, p0, n_iter=2000, lam=1e-3):
    """Levenberg-Marquardt style fitter without scipy. Works in log-space."""
    log_rho = np.log(rho)
    p = np.array(p0, dtype=float)
    lam_val = lam
    best_p, best_res = p.copy(), np.inf

    for _ in range(n_iter):
        try:
            pred = func(r, *p)
            if not np.all(np.isfinite(pred)) or np.any(pred <= 0):
                break
            res = np.sum((np.log(pred) - log_rho) ** 2)
        except Exception:
            break

        if res < best_res:
            best_res, best_p = res, p.copy()

        eps = np.abs(p) * 1e-5 + 1e-10
        J = np.zeros((len(r), len(p)))
        for k in range(len(p)):
            dp = np.zeros_like(p); dp[k] = eps[k]
            try:
                J[:, k] = (np.log(func(r, *(p + dp))) - np.log(func(r, *(p - dp)))) / (2 * eps[k])
            except Exception:
                return best_p, func

        JtJ = J.T @ J
        g = J.T @ (np.log(func(r, *p)) - log_rho)
        try:
            dp = np.linalg.solve(JtJ + lam_val * np.diag(np.diag(JtJ) + 1e-10), -g)
        except np.linalg.LinAlgError:
            break

        p_new = np.abs(p + dp)
        try:
            pred_new = func(r, *p_new)
            res_new = np.sum((np.log(pred_new) - log_rho) ** 2) if np.all(np.isfinite(pred_new)) and np.all(pred_new > 0) else np.inf
        except Exception:
            res_new = np.inf

        if res_new < res:
            p, lam_val = p_new, lam_val * 0.5
        else:
            lam_val = lam_val * 2.0

        if np.max(np.abs(dp) / (np.abs(p) + 1e-10)) < 1e-7:
            break

    return best_p, func


def fit_profile(r_centers, rho, model="nfw"):
    valid = np.isfinite(rho) & (rho > 0) & (r_centers > 0)
    if np.sum(valid) < 4:
        return None, None
    r_fit = r_centers[valid]
    rho_fit = rho[valid]
    func = nfw_profile if model == "nfw" else core_profile
    try:
        p0 = [rho_fit[0], r_fit[len(r_fit) // 3]]
        popt, f = _lm_fit(func, r_fit, rho_fit, p0)
        return popt, f
    except Exception:
        return None, None


# ──────────────────────────── 2D projections ────────────────────────────────

def projected_density_map(data, npix=400, width=None, plane=(0, 1)):
    _, _, r, _ = centered_phase(data)
    pos_c = data["pos"] - center_of_mass(data["pos"], data["mass"])
    mass = data["mass"] if data["mass"] is not None else np.ones(len(r))
    x, y = pos_c[:, plane[0]], pos_c[:, plane[1]]
    if width is None:
        p = np.percentile(np.hypot(x, y), 99.5)
        width = max(2.2 * p, 10.0)
    half = 0.5 * width
    sel = (np.abs(x) < half) & (np.abs(y) < half)
    H, xe, ye = np.histogram2d(x[sel], y[sel], bins=npix,
                                range=[[-half, half], [-half, half]],
                                weights=mass[sel])
    return H.T + 1e-20, [-half, half, -half, half]


def phase_hist_r_vr(data, nbins=250):
    _, _, r, vr = centered_phase(data)
    rmax = np.percentile(r[r > 0], 99.5) if np.any(r > 0) else 1.0
    vmax = np.percentile(np.abs(vr), 99.5) if len(vr) else 1.0
    H, _, _ = np.histogram2d(r, vr, bins=[nbins, nbins],
                              range=[[0, rmax], [-vmax, vmax]])
    return H.T + 1e-20, [0, rmax, -vmax, vmax]


# ──────────────────────────── Plot helpers ──────────────────────────────────

def style_ax(ax, title=None):
    ax.set_facecolor("#111111")
    for sp in ax.spines.values():
        sp.set_color("#888888")
    ax.tick_params(colors="#BBBBBB")
    ax.xaxis.label.set_color("#DDDDDD")
    ax.yaxis.label.set_color("#DDDDDD")
    if title:
        ax.set_title(title, color="#DDDDDD", fontsize=11)


# ──────────────────────────── Plot functions ────────────────────────────────

def plot_surface_density_compare(cdm, sidm, outpath):
    H1, ext1 = projected_density_map(cdm)
    H2, ext2 = projected_density_map(sidm, width=ext1[1] - ext1[0])
    vmin = min(np.nanmin(H1[H1 > 0]), np.nanmin(H2[H2 > 0]))
    vmax = max(np.nanmax(H1), np.nanmax(H2))
    fig, axes = plt.subplots(1, 2, figsize=(12, 5), facecolor="#111111")
    for ax, H, title in zip(axes, [H1, H2], ["CDM-like: projected density", "SIDM-like: projected density"]):
        im = ax.imshow(H, origin="lower", extent=ext1,
                       norm=LogNorm(vmin=vmin, vmax=vmax), cmap="inferno")
        ax.set_xlabel("x"); ax.set_ylabel("y")
        style_ax(ax, title)
    fig.colorbar(im, ax=axes.ravel().tolist(), shrink=0.85).set_label("Projected mass")
    fig.tight_layout()
    fig.savefig(outpath, dpi=250, facecolor=fig.get_facecolor())
    plt.close(fig)


def plot_density_profiles(cdm, sidm, outpath):
    rc, rhoc = radial_density_profile(cdm)
    rs, rhos = radial_density_profile(sidm)

    # fits
    popt_nfw, func_nfw = fit_profile(rc, rhoc, "nfw")
    popt_core, func_core = fit_profile(rs, rhos, "core")

    fig, ax = plt.subplots(figsize=(7, 5), facecolor="#111111")
    ax.plot(rc, rhoc, lw=2, label="CDM-like")
    ax.plot(rs, rhos, lw=2, label="SIDM-like")
    if popt_nfw is not None:
        r_fine = np.logspace(np.log10(rc[0]), np.log10(rc[-1]), 200)
        ax.plot(r_fine, func_nfw(r_fine, *popt_nfw), "--", lw=1.2,
                color="steelblue", alpha=0.7, label=f"NFW fit (rs={popt_nfw[1]:.1f})")
    if popt_core is not None:
        r_fine = np.logspace(np.log10(rs[0]), np.log10(rs[-1]), 200)
        ax.plot(r_fine, func_core(r_fine, *popt_core), "--", lw=1.2,
                color="orange", alpha=0.7, label=f"Core fit (rc={popt_core[1]:.1f})")
    ax.set_xscale("log"); ax.set_yscale("log")
    ax.set_xlabel("r"); ax.set_ylabel(r"$\rho(r)$")
    ax.legend(fontsize=9)
    style_ax(ax, "Radial density profile")
    fig.tight_layout()
    fig.savefig(outpath, dpi=250, facecolor=fig.get_facecolor())
    plt.close(fig)


def plot_log_slope(cdm, sidm, outpath):
    """d log rho / d log r — диагностика core vs cusp."""
    rc, rhoc = radial_density_profile(cdm)
    rs, rhos = radial_density_profile(sidm)
    sc = log_slope_profile(rc, rhoc)
    ss = log_slope_profile(rs, rhos)
    fig, ax = plt.subplots(figsize=(7, 5), facecolor="#111111")
    ax.plot(rc, sc, lw=2, label="CDM-like")
    ax.plot(rs, ss, lw=2, label="SIDM-like")
    ax.axhline(-1, color="#888", lw=0.8, ls="--", label="slope = -1")
    ax.axhline(-3, color="#555", lw=0.8, ls="--", label="slope = -3 (NFW outer)")
    ax.axhline(0,  color="#aaa", lw=0.8, ls=":",  label="slope = 0 (core)")
    ax.set_xscale("log")
    ax.set_ylim(-5, 1)
    ax.set_xlabel("r"); ax.set_ylabel(r"$d\log\rho/d\log r$")
    ax.legend(fontsize=9)
    style_ax(ax, "Log-slope profile (core=0, cusp<-1)")
    fig.tight_layout()
    fig.savefig(outpath, dpi=250, facecolor=fig.get_facecolor())
    plt.close(fig)


def plot_sigma_profiles(cdm, sidm, outpath):
    rc, sc = radial_sigma_profile(cdm)
    rs, ss = radial_sigma_profile(sidm)
    fig, ax = plt.subplots(figsize=(7, 5), facecolor="#111111")
    ax.plot(rc, sc, lw=2, label="CDM-like")
    ax.plot(rs, ss, lw=2, label="SIDM-like")
    ax.set_xscale("log")
    ax.set_xlabel("r"); ax.set_ylabel(r"$\sigma_{1D}(r)$")
    ax.legend()
    style_ax(ax, "1D velocity dispersion profile")
    fig.tight_layout()
    fig.savefig(outpath, dpi=250, facecolor=fig.get_facecolor())
    plt.close(fig)


def plot_phase_compare(cdm, sidm, outpath):
    H1, ext1 = phase_hist_r_vr(cdm)
    H2, ext2 = phase_hist_r_vr(sidm)
    vmin = min(np.nanmin(H1[H1 > 0]), np.nanmin(H2[H2 > 0]))
    vmax = max(np.nanmax(H1), np.nanmax(H2))
    fig, axes = plt.subplots(1, 2, figsize=(12, 5), facecolor="#111111")
    for ax, H, ext, title in zip(axes, [H1, H2], [ext1, ext2],
                                  ["CDM-like: phase space (r, vr)", "SIDM-like: phase space (r, vr)"]):
        im = ax.imshow(H, origin="lower", extent=ext,
                       norm=LogNorm(vmin=vmin, vmax=vmax), cmap="magma", aspect="auto")
        ax.set_xlabel("r"); ax.set_ylabel(r"$v_r$")
        style_ax(ax, title)
    fig.colorbar(im, ax=axes.ravel().tolist(), shrink=0.85).set_label("Counts per pixel")
    fig.tight_layout()
    fig.savefig(outpath, dpi=250, facecolor=fig.get_facecolor())
    plt.close(fig)


def core_density_evolution(run_dir, ptype=3, rcore=50.0):
    snaps = sorted(list_snapshots(run_dir), key=snapshot_number)
    times, rho_core, n_interact = [], [], []
    for s in snaps:
        d = read_snapshot(s, ptype=ptype)
        times.append(d["time"])
        rho_core.append(core_density(d, rcore=rcore))
        n_interact.append(d["n_interact"])
    return np.array(times), np.array(rho_core), n_interact


def plot_core_density_evolution(cdm_dir, sidm_dir, outpath, ptype=3, rcore=50.0):
    tc, rc, _ = core_density_evolution(cdm_dir, ptype=ptype, rcore=rcore)
    ts, rs, ni = core_density_evolution(sidm_dir, ptype=ptype, rcore=rcore)

    fig, axes = plt.subplots(1, 2, figsize=(12, 4), facecolor="#111111")

    axes[0].plot(tc, rc, "-o", ms=3, lw=1.7, label="CDM-like")
    axes[0].plot(ts, rs, "-o", ms=3, lw=1.7, label="SIDM-like")
    axes[0].set_yscale("log")
    axes[0].set_xlabel("time"); axes[0].set_ylabel(rf"$\rho(r<{rcore})$")
    axes[0].legend()
    style_ax(axes[0], "Core density evolution")

    # NInteractions per snapshot — SIDM diagnostics
    ni_vals = [x if x is not None else 0 for x in ni]
    axes[1].plot(ts, ni_vals, "-o", ms=3, lw=1.7, color="orange")
    axes[1].set_xlabel("time"); axes[1].set_ylabel("Total NInteractions")
    style_ax(axes[1], "Cumulative SIDM interactions")

    fig.tight_layout()
    fig.savefig(outpath, dpi=250, facecolor=fig.get_facecolor())
    plt.close(fig)


# ────────────────────────────── Summary ─────────────────────────────────────

def write_summary(cdm, sidm, outpath, rcore=50.0):
    rc_val = core_density(cdm, rcore=rcore)
    rs_val = core_density(sidm, rcore=rcore)

    _, cdm_rho = radial_density_profile(cdm)
    _, sidm_rho = radial_density_profile(sidm)
    cdm_r, _ = radial_density_profile(cdm)
    sidm_r, _ = radial_density_profile(sidm)

    cdm_slope = log_slope_profile(cdm_r, cdm_rho)
    sidm_slope = log_slope_profile(sidm_r, sidm_rho)

    # inner slope: median of innermost 3 valid bins
    def inner_slope(slope_arr):
        valid = slope_arr[np.isfinite(slope_arr)]
        return float(np.median(valid[:3])) if len(valid) >= 3 else np.nan

    _, func_nfw   = fit_profile(cdm_r, cdm_rho, "nfw")
    popt_nfw, _   = fit_profile(cdm_r, cdm_rho, "nfw")
    popt_core, _  = fit_profile(sidm_r, sidm_rho, "core")

    with open(outpath, "w", encoding="utf-8") as f:
        f.write("Halo compare summary\n")
        f.write("=" * 40 + "\n\n")
        f.write(f"CDM snapshot : {cdm['path']}\n")
        f.write(f"SIDM snapshot: {sidm['path']}\n")
        f.write(f"CDM  time    : {cdm['time']:.4f}\n")
        f.write(f"SIDM time    : {sidm['time']:.4f}\n\n")

        f.write(f"Core radius used : {rcore}\n")
        f.write(f"rho_core CDM     : {rc_val:.4e}\n")
        f.write(f"rho_core SIDM    : {rs_val:.4e}\n")
        if np.isfinite(rc_val) and np.isfinite(rs_val) and rc_val > 0:
            f.write(f"ratio SIDM/CDM   : {rs_val/rc_val:.4f}\n\n")

        f.write(f"Inner log-slope CDM  : {inner_slope(cdm_slope):.3f}  (0=core, -1..-3=cusp)\n")
        f.write(f"Inner log-slope SIDM : {inner_slope(sidm_slope):.3f}\n\n")

        if popt_nfw is not None:
            f.write(f"NFW fit CDM  : rho0={popt_nfw[0]:.3e}, rs={popt_nfw[1]:.2f}\n")
        if popt_core is not None:
            f.write(f"Core fit SIDM: rho0={popt_core[0]:.3e}, rc={popt_core[1]:.2f}\n\n")

        ni = sidm.get("n_interact")
        f.write(f"NInteractions (last snap): {ni if ni is not None else 'not saved — check DM_SIDM flag'}\n")


# ─────────────────────────────── Main ───────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="SIDM halo analysis.")
    parser.add_argument("--cdm",   required=True,  help="Directory with CDM snapshots")
    parser.add_argument("--sidm",  required=False,  help="Directory with SIDM snapshots")
    parser.add_argument("--ptype", type=int, default=3)
    parser.add_argument("--outdir", default="analysis_halo_compare")
    parser.add_argument("--rcore", type=float, default=50.0,
                        help="Core radius for rho_core(t). Use ~5x softening.")
    args = parser.parse_args()

    os.makedirs(args.outdir, exist_ok=True)

    cdm = read_snapshot(latest_snapshot(args.cdm), ptype=args.ptype)

    if args.sidm:
        sidm = read_snapshot(latest_snapshot(args.sidm), ptype=args.ptype)
        plot_surface_density_compare(cdm, sidm,
            os.path.join(args.outdir, "01_surface_density_compare.png"))
        plot_density_profiles(cdm, sidm,
            os.path.join(args.outdir, "02_density_profile_compare.png"))
        plot_log_slope(cdm, sidm,
            os.path.join(args.outdir, "03_log_slope_compare.png"))
        plot_sigma_profiles(cdm, sidm,
            os.path.join(args.outdir, "04_sigma1d_profile_compare.png"))
        plot_phase_compare(cdm, sidm,
            os.path.join(args.outdir, "05_phase_r_vr_compare.png"))
        plot_core_density_evolution(args.cdm, args.sidm,
            os.path.join(args.outdir, "06_core_density_evolution.png"),
            ptype=args.ptype, rcore=args.rcore)
        write_summary(cdm, sidm,
            os.path.join(args.outdir, "summary.txt"), rcore=args.rcore)
        print(f"Saved to: {args.outdir}")
    else:
        # single-run fallback — базовые 4 графика
        r, rho = radial_density_profile(cdm)
        r2, sig = radial_sigma_profile(cdm)
        H, ext = projected_density_map(cdm)
        P, pext = phase_hist_r_vr(cdm)

        fig, ax = plt.subplots(figsize=(6, 5), facecolor="#111111")
        ax.imshow(H, origin="lower", extent=ext, norm=LogNorm(), cmap="inferno")
        ax.set_xlabel("x"); ax.set_ylabel("y")
        style_ax(ax, "Projected density")
        fig.tight_layout()
        fig.savefig(os.path.join(args.outdir, "01_surface_density.png"), dpi=250, facecolor=fig.get_facecolor())
        plt.close(fig)

        fig, ax = plt.subplots(figsize=(7, 5), facecolor="#111111")
        ax.plot(r, rho, lw=2)
        ax.set_xscale("log"); ax.set_yscale("log")
        ax.set_xlabel("r"); ax.set_ylabel(r"$\rho(r)$")
        style_ax(ax, "Density profile")
        fig.tight_layout()
        fig.savefig(os.path.join(args.outdir, "02_density_profile.png"), dpi=250, facecolor=fig.get_facecolor())
        plt.close(fig)

        slope = log_slope_profile(r, rho)
        fig, ax = plt.subplots(figsize=(7, 5), facecolor="#111111")
        ax.plot(r, slope, lw=2)
        ax.axhline(0, color="#aaa", ls=":", lw=0.8, label="core")
        ax.set_xscale("log"); ax.set_ylim(-5, 1)
        ax.set_xlabel("r"); ax.set_ylabel(r"$d\log\rho/d\log r$")
        ax.legend()
        style_ax(ax, "Log-slope profile")
        fig.tight_layout()
        fig.savefig(os.path.join(args.outdir, "03_log_slope.png"), dpi=250, facecolor=fig.get_facecolor())
        plt.close(fig)

        print(f"Saved to: {args.outdir}")


if __name__ == "__main__":
    main()
