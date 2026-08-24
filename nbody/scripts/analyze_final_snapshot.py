#!/usr/bin/env python3
"""
Анализ финального снапшота SIDM-прогона: профили + статистика NInteractions.
Usage:
    python3 analyze_final_snapshot.py --snapshot <path.hdf5> --outdir <dir> [--rcore 2]
"""
import argparse, os
import numpy as np
import h5py
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

try:
    from plot_config import COLORS, SIZES, apply, setup
    setup()
    C0 = COLORS.palette[0]; C1 = COLORS.palette[1]
    FIG = SIZES["page"]
except Exception:
    C0 = "C0"; C1 = "C1"; FIG = (7, 5)
    def apply(ax, xlabel=None, ylabel=None, **kw):
        if xlabel: ax.set_xlabel(xlabel)
        if ylabel: ax.set_ylabel(ylabel)


def read_snap(path):
    with h5py.File(path, "r") as f:
        g = f["PartType3"]
        return {
            "pos": g["Coordinates"][:].astype(np.float64),
            "vel": g["Velocities"][:].astype(np.float64),
            "mass": g["Masses"][:].astype(np.float64),
            "time": float(f["Header"].attrs.get("Time", 0.0)),
            "sigma": float(f["Header"].attrs.get("DM_InteractionCrossSection", 0.0)),
            "ni": g["NInteractions"][:].astype(np.uint64) if "NInteractions" in g else None,
        }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--snapshot", required=True)
    ap.add_argument("--outdir", required=True)
    ap.add_argument("--rcore", type=float, default=2.0, help="core radius [kpc]")
    args = ap.parse_args()
    os.makedirs(args.outdir, exist_ok=True)

    d = read_snap(args.snapshot)
    pos = d["pos"] - np.sum(d["pos"] * d["mass"][:, None], axis=0) / d["mass"].sum()
    vel = d["vel"] - np.mean(d["vel"], axis=0)
    r = np.linalg.norm(pos, axis=1)
    mass = d["mass"]
    t, sig_cs = d["time"], d["sigma"]

    lines = [f"Snapshot: {args.snapshot}",
             f"Time: {t:.4f}   CrossSection: {sig_cs}",
             f"Particles: {len(r)}   Mtot={mass.sum():.4e}"]

    # --- профили (лог-биннинг) ---
    rmax = np.percentile(r[r > 0], 99.9)
    edges = np.logspace(np.log10(0.05), np.log10(max(rmax, 10)), 60)
    centers = np.sqrt(edges[:-1] * edges[1:])
    shell_m, _ = np.histogram(r, bins=edges, weights=mass)
    counts, _ = np.histogram(r, bins=edges)
    vol = 4.0 / 3.0 * np.pi * (edges[1:]**3 - edges[:-1]**3)
    rho = np.where(counts > 0, shell_m / vol, np.nan)

    valid = np.isfinite(rho) & (rho > 0) & (counts >= 5)
    lr, lrho = np.log10(centers), np.log10(np.where(rho > 0, rho, np.nan))
    slope = np.full_like(centers, np.nan)
    for i in np.where(valid)[0]:
        m = np.abs(lr - lr[i]) <= 0.16
        if m.sum() >= 4:
            slope[i] = np.polyfit(lr[m], lrho[m], 1)[0]

    sv = np.full(len(centers), np.nan)
    for i in range(len(edges) - 1):
        mm = (r >= edges[i]) & (r < edges[i + 1])
        if mm.sum() >= 10:
            sv[i] = np.sqrt(np.mean(np.var(vel[mm], axis=0)))

    rc = args.rcore
    rho_core = mass[r < rc].sum() / (4.0 / 3.0 * np.pi * rc**3)
    inner_slope = np.nanmedian(slope[valid][:6])
    lines.append(f"Core density (r<{rc}): {rho_core:.4e}")
    lines.append(f"Inner log-slope (median first bins): {inner_slope:.3f}")

    # --- NInteractions ---
    lines.append("")
    ni_mean_bin = frac_bin = rcenters = None
    if d["ni"] is not None:
        ni = d["ni"]
        tot = int(ni.sum()); nz = int((ni > 0).sum())
        lines.append(f"NInteractions TOTAL: {tot}")
        lines.append(f"Particles interacted: {nz}/{len(ni)} ({100*nz/len(ni):.2f}%)")
        if nz:
            nn = ni[ni > 0].astype(float)
            lines.append(f"Per-interacted: mean={nn.mean():.2f} median={np.median(nn):.0f} "
                         f"p90={np.percentile(nn,90):.0f} max={int(nn.max())}")
        nb = 12
        redges = np.logspace(np.log10(max(r[r > 0].min(), 0.05)), np.log10(rmax), nb + 1)
        rcenters = np.sqrt(redges[:-1] * redges[1:])
        ni_mean_bin = np.full(nb, np.nan); frac_bin = np.full(nb, np.nan)
        for i in range(nb):
            mm = (r >= redges[i]) & (r < redges[i + 1])
            if mm.sum() >= 5:
                ni_mean_bin[i] = ni[mm].mean()
                frac_bin[i] = 100.0 * (ni[mm] > 0).sum() / mm.sum()
        lines.append("Radial NI profile (r_center, mean_ni, %_interacted):")
        for i in range(nb):
            if np.isfinite(ni_mean_bin[i]):
                lines.append(f"  r={rcenters[i]:8.2f}  ni_mean={ni_mean_bin[i]:8.3f}  pct={frac_bin[i]:6.1f}%")
    else:
        lines.append("NInteractions: NOT IN SNAPSHOT")

    txt = "\n".join(lines)
    print(txt)
    with open(os.path.join(args.outdir, "summary_analysis.txt"), "w") as fo:
        fo.write(txt + "\n")
    # --- графики ---
    def _save(fig, name):
        fig.savefig(os.path.join(args.outdir, name), dpi=200, bbox_inches="tight")
        plt.close(fig)

    fig, ax = plt.subplots(figsize=FIG)
    m = np.isfinite(rho) & (rho > 0)
    if m.any():
        ax.plot(centers[m], rho[m], color=C0, lw=1.5)
        ax.set_xscale("log"); ax.set_yscale("log")
    apply(ax, xlabel="r [kpc]", ylabel="rho")
    _save(fig, "01_density_profile.png")

    fig, ax = plt.subplots(figsize=FIG)
    m = np.isfinite(slope)
    if m.any():
        ax.plot(centers[m], slope[m], color=C1, lw=1.5)
        ax.axhline(-1.0, ls=":", color="0.4", lw=0.8)
        ax.set_xscale("log")
    apply(ax, xlabel="r [kpc]", ylabel="d log rho / d log r")
    _save(fig, "02_log_slope.png")

    fig, ax = plt.subplots(figsize=FIG)
    m = np.isfinite(sv)
    if m.any():
        ax.plot(centers[m], sv[m], color=C0, lw=1.5)
        ax.set_xscale("log")
    apply(ax, xlabel="r [kpc]", ylabel="sigma_1D [km/s]")
    _save(fig, "03_sigma_v.png")

    if ni_mean_bin is not None:
        fig, axs = plt.subplots(1, 2, figsize=(11, 4.2))
        mb = np.isfinite(ni_mean_bin) & (ni_mean_bin > 0)
        if mb.any():
            axs[0].plot(rcenters[mb], ni_mean_bin[mb], color=C0, lw=1.5)
            axs[0].set_xscale("log"); axs[0].set_yscale("log")
        apply(axs[0], xlabel="r [kpc]", ylabel="mean NInteractions")
        fb = np.isfinite(frac_bin) & (frac_bin > 0)
        if fb.any():
            axs[1].plot(rcenters[fb], frac_bin[fb], color=C1, lw=1.5)
            axs[1].set_xscale("log")
        apply(axs[1], xlabel="r [kpc]", ylabel="% particles interacted")
        _save(fig, "04_ninteractions_radial.png")
    print(f"[OK] analysis saved to {args.outdir}")


if __name__ == "__main__":
    main()
