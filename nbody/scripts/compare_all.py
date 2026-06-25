#!/usr/bin/env python3
"""
Сравнительный анализ CDM vs все SIDM-прогоны.
Строит стандартные графики + дополнительные визуализации.

Использование:
  python3 compare_all.py --cdm runs/cdm_N1e6 [--sidm runs/sidm_sigma0.1_N1e6 ...] --outdir analysis_all
"""
import argparse, glob, os, re, sys

import h5py
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.colors import LogNorm
from plot_config import COLORS, SIZES, apply, setup
S = SIZES

setup()


# ─────────────── Общие функции (I/O, профили) ─────────────────────────────

def list_snapshots(run_dir):
    for d in [run_dir, os.path.join(run_dir, "output")]:
        files = sorted(glob.glob(os.path.join(d, "snapshot*.hdf5")))
        if files:
            return files
    raise FileNotFoundError(f"No HDF5 snapshots found in {run_dir} or {run_dir}/output/")

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
            raise RuntimeError(f"{gname} not found in {path}")
        g = f[gname]
        n_interact = None
        if "NInteractions" in g:
            n_interact = int(np.sum(g["NInteractions"][:]))
        data = {
            "pos":     g["Coordinates"][:].astype(np.float64),
            "vel":     g["Velocities"][:].astype(np.float64),
            "mass":    g["Masses"][:].astype(np.float64) if "Masses" in g else None,
            "n_interact": n_interact,
            "time":    float(f["Header"].attrs.get("Time", 0.0)),
            "path":    path,
        }
    return data

def center_of_mass(pos, mass):
    if mass is None:
        return np.mean(pos, axis=0)
    msum = np.sum(mass)
    return np.sum(pos * mass[:, None], axis=0) / msum if msum > 0 else np.mean(pos, axis=0)

def centered_phase(data):
    pos = data["pos"].copy()
    vel = data["vel"].copy()
    mass = data["mass"]
    pos -= center_of_mass(pos, mass)
    vel -= np.mean(vel, axis=0)
    r = np.linalg.norm(pos, axis=1)
    vr = np.zeros_like(r)
    mask = r > 0
    vr[mask] = np.einsum("ij,ij->i", pos[mask], vel[mask]) / r[mask]
    return pos, vel, r, vr

def log_bins(r, rmin=None, rmax=None, nbins=40):
    rr = r[r > 0]
    rmin = rmin or np.percentile(rr, 1)
    rmax = rmax or np.percentile(rr, 99.5)
    rmin = max(rmin, 1e-6)
    return np.logspace(np.log10(rmin), np.log10(rmax), nbins + 1)

def radial_density_profile(data, nbins=40):
    _, _, r, _ = centered_phase(data)
    mass = data["mass"] if data["mass"] is not None else np.ones_like(r)
    edges = log_bins(r, nbins=nbins)
    centers = np.sqrt(edges[:-1] * edges[1:])
    rho = np.full(nbins, np.nan)
    for i in range(nbins):
        m = (r >= edges[i]) & (r < edges[i + 1])
        if np.any(m):
            vol = 4./3. * np.pi * (edges[i+1]**3 - edges[i]**3)
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
    valid = np.isfinite(rho) & (rho > 0) & (r_centers > 0)
    slope = np.full_like(rho, np.nan)
    if np.sum(valid) < 3:
        return slope
    log_r = np.log10(r_centers[valid])
    log_rho = np.log10(rho[valid])
    d_log_rho = np.gradient(log_rho, log_r)
    slope[valid] = d_log_rho
    return slope

def core_density(data, rcore=50.0):
    _, _, r, _ = centered_phase(data)
    mass = data["mass"] if data["mass"] is not None else np.ones_like(r)
    m = r < rcore
    if not np.any(m):
        return np.nan
    return np.sum(mass[m]) / (4./3. * np.pi * rcore**3)

def projected_density_map(data, npix=400, width=None, plane=(0, 1)):
    pos = data["pos"].copy()
    com = center_of_mass(pos, data["mass"])
    pos -= com
    x, y = pos[:, plane[0]], pos[:, plane[1]]
    mass_arr = data["mass"] if data["mass"] is not None else np.ones(len(x))
    if width is None:
        p = np.percentile(np.hypot(x, y), 99.5)
        width = max(2.2 * p, 10.0)
    half = 0.5 * width
    sel = (np.abs(x) < half) & (np.abs(y) < half)
    H, _, _ = np.histogram2d(x[sel], y[sel], bins=npix,
                              range=[[-half, half], [-half, half]],
                              weights=mass_arr[sel])
    return H.T + 1e-20, [-half, half, -half, half]

def sigma_label(sigma_val):
    if sigma_val is None:
        return "CDM"
    return rf"$\sigma$={sigma_val}"


# ─────────────── Функции отрисовки ─────────────────────────────────────

def plot_all_density_profiles(all_profiles, outpath):
    fig, ax = plt.subplots(figsize=S["page"])
    for i, (r, rho, label, c) in enumerate(all_profiles):
        ax.plot(r, rho, color=c, lw=1.5, label=label)
    apply(ax, "Radial density profiles", xlabel="r", ylabel=r"$\rho(r)$",
          xscale="log", yscale="log", legend=True)
    fig.tight_layout()
    fig.savefig(outpath, dpi=300, bbox_inches="tight")
    plt.close(fig)

def plot_all_slope_profiles(all_profiles, outpath):
    fig, ax = plt.subplots(figsize=S["page"])
    for i, (r, rho, label, c) in enumerate(all_profiles):
        slope = log_slope_profile(r, rho)
        ax.plot(r, slope, color=c, lw=1.5, label=label)
    ax.axhline(0, color=COLORS.mono[5], ls=":", lw=0.8, label="core (0)")
    ax.axhline(-1, color=COLORS.mono[3], ls="--", lw=0.8)
    ax.axhline(-3, color=COLORS.mono[4], ls="--", lw=0.8, label="NFW outer (-3)")
    apply(ax, "Log-slope profiles — core vs cusp", xlabel="r",
          ylabel=r"$d\log\rho/d\log r$", xscale="log", legend=True)
    ax.set_ylim(-5, 1)
    fig.tight_layout()
    fig.savefig(outpath, dpi=300, bbox_inches="tight")
    plt.close(fig)

def plot_all_sigma_profiles(all_sigmas, outpath):
    fig, ax = plt.subplots(figsize=S["page"])
    for i, (r, sig, label, c) in enumerate(all_sigmas):
        ax.plot(r, sig, color=c, lw=1.5, label=label)
    apply(ax, "1D velocity dispersion profiles", xlabel="r",
          ylabel=r"$\sigma_{1D}(r)$", xscale="log", legend=True)
    fig.tight_layout()
    fig.savefig(outpath, dpi=300, bbox_inches="tight")
    plt.close(fig)

def plot_core_density_vs_sigma(all_core, outpath, rcore=50.0):
    fig, ax = plt.subplots(figsize=S["square"])
    labels = [s[0] for s in all_core]
    values = [s[1] for s in all_core]
    colors = [s[2] for s in all_core]
    bars = ax.bar(labels, values, color=colors, edgecolor="white", lw=0.5)
    apply(ax, f"Core density vs SIDM cross-section (rcore={rcore})",
          ylabel=rf"$\rho(r < {rcore})$", yscale="log")
    for bar, val in zip(bars, values):
        if np.isfinite(val) and val > 0:
            ax.text(bar.get_x() + bar.get_width()/2, val*1.1,
                    f"{val:.2e}", ha="center", va="bottom", fontsize=8)
    fig.tight_layout()
    fig.savefig(outpath, dpi=300, bbox_inches="tight")
    plt.close(fig)

def plot_projected_density_grid(all_data, outpath):
    n = len(all_data)
    fig, axes = plt.subplots(2, 3, figsize=(15, 10))
    axes = axes.flatten()
    vmin_all, vmax_all = np.inf, -np.inf
    maps = []
    for data, label in all_data:
        H, ext = projected_density_map(data)
        maps.append((H, ext, label))
        vmin_all = min(vmin_all, np.nanmin(H[H > 0]) if np.any(H > 0) else 1)
        vmax_all = max(vmax_all, np.nanmax(H))
    for ax, (H, ext, label) in zip(axes, maps):
        im = ax.imshow(H, origin="lower", extent=ext,
                       norm=LogNorm(vmin=vmin_all, vmax=vmax_all),
                       cmap="inferno")
        apply(ax, title=label, xlabel="x", ylabel="y")
    for i in range(n, len(axes)):
        axes[i].set_visible(False)
    fig.colorbar(im, ax=axes[:n].tolist(), shrink=0.85).set_label("Projected mass")
    fig.tight_layout()
    fig.savefig(outpath, dpi=300, bbox_inches="tight")
    plt.close(fig)

def plot_contour_overlay(all_data, outpath):
    fig, ax = plt.subplots(figsize=S["square"])
    for data, label, c in all_data:
        H, ext = projected_density_map(data, npix=200)
        levels = np.logspace(np.log10(H[H > 0].min()*2),
                             np.log10(H.max()), 4)
        ax.contour(H, levels=levels, extent=ext,
                   colors=[c], alpha=0.7, linewidths=1.2)
    from matplotlib.lines import Line2D
    legend_elements = [Line2D([0], [0], color=c, lw=2, label=label)
                       for data, label, c in all_data]
    apply(ax, "Iso-density contours", xlabel="x", ylabel="y")
    ax.legend(handles=legend_elements, fontsize=9)
    fig.tight_layout()
    fig.savefig(outpath, dpi=300, bbox_inches="tight")
    plt.close(fig)

def plot_circularity_hist(all_data, outpath):
    fig, ax = plt.subplots(figsize=S["page"])
    for data, label, c in all_data:
        pos, vel, r, vr = centered_phase(data)
        Lz = pos[:, 0] * vel[:, 1] - pos[:, 1] * vel[:, 0]
        v_amp = np.linalg.norm(vel, axis=1)
        Lcirc = r * v_amp
        mask = Lcirc > 0
        eps = np.zeros_like(r)
        eps[mask] = Lz[mask] / Lcirc[mask]
        eps = np.clip(eps, -1, 1)
        ax.hist(eps, bins=50, range=(-1, 1),
                histtype="step", lw=1.5,
                color=c, label=label, density=True)
    apply(ax, "Orbital circularity distribution",
          xlabel="Circularity $\\epsilon = L_z / L_{circ}$",
          ylabel="PDF", legend=True)
    fig.tight_layout()
    fig.savefig(outpath, dpi=300, bbox_inches="tight")
    plt.close(fig)


# ─────────────── Main ───────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="CDM vs all SIDM comparison")
    parser.add_argument("--cdm", required=True, help="CDM run directory")
    parser.add_argument("--sidm", nargs="*", default=[], help="SIDM run directories")
    parser.add_argument("--outdir", default="analysis_all")
    parser.add_argument("--rcore", type=float, default=50.0)
    args = parser.parse_args()

    os.makedirs(args.outdir, exist_ok=True)

    # Читаем CDM
    print(f"Reading CDM: {args.cdm}")
    cdm_data = read_snapshot(latest_snapshot(args.cdm), ptype=3)
    all_data = [cdm_data]
    labels = ["CDM"]

    # Читаем SIDM
    for sidm_dir in args.sidm:
        name = os.path.basename(os.path.normpath(sidm_dir))
        print(f"Reading SIDM: {sidm_dir}  (name={name})")
        d = read_snapshot(latest_snapshot(sidm_dir), ptype=3)
        all_data.append(d)
        m = re.search(r"sigma([\d.]+)", name)
        sigma_val = float(m.group(1)) if m else None
        labels.append(sigma_label(sigma_val))

    # Собираем профили
    all_profiles = []
    all_sigmas = []
    all_core = []
    proj_data = []
    colors = COLORS.palette[:len(all_data)]

    for i, (d, label) in enumerate(zip(all_data, labels)):
        c = colors[i]
        r, rho = radial_density_profile(d)
        all_profiles.append((r, rho, label, c))
        rs, sig = radial_sigma_profile(d)
        all_sigmas.append((rs, sig, label, c))
        rhoc = core_density(d, rcore=args.rcore)
        all_core.append((label, rhoc, c))
        proj_data.append((d, label, c))

    print("1/8: All density profiles...")
    plot_all_density_profiles(all_profiles, os.path.join(args.outdir, "01_all_density_profiles.png"))

    print("2/8: All slope profiles...")
    plot_all_slope_profiles(all_profiles, os.path.join(args.outdir, "02_all_slope_profiles.png"))

    print("3/8: All sigma profiles...")
    plot_all_sigma_profiles(all_sigmas, os.path.join(args.outdir, "03_all_sigma_profiles.png"))

    print("4/8: Core density vs sigma...")
    plot_core_density_vs_sigma(all_core, os.path.join(args.outdir, "04_core_density_vs_sigma.png"), rcore=args.rcore)

    print("5/8: Projected density grid...")
    plot_projected_density_grid(list(zip(all_data, labels)),
                                os.path.join(args.outdir, "05_projected_density_grid.png"))

    print("6/8: Contour overlay...")
    plot_contour_overlay(proj_data, os.path.join(args.outdir, "06_contour_overlay.png"))

    print("7/8: Circularity histogram...")
    plot_circularity_hist(proj_data, os.path.join(args.outdir, "07_circularity_histogram.png"))

    print("8/8: Writing summary...")
    with open(os.path.join(args.outdir, "summary.txt"), "w", encoding="utf-8") as f:
        f.write("CDM vs SIDM comparison summary\n")
        f.write("=" * 50 + "\n\n")
        for d, label in zip(all_data, labels):
            r, rho = radial_density_profile(d)
            slope = log_slope_profile(r, rho)
            rhoc = core_density(d, rcore=args.rcore)
            valid = slope[np.isfinite(slope)]
            inner_slope = float(np.median(valid[:3])) if len(valid) >= 3 else np.nan
            f.write(f"{label}:\n")
            f.write(f"  Snapshot:        {d['path']}\n")
            f.write(f"  Time:            {d['time']:.4f}\n")
            f.write(f"  Particles:       {len(d['pos'])}\n")
            f.write(f"  Core density:    {rhoc:.4e}\n")
            f.write(f"  Inner log-slope: {inner_slope:.3f}\n")
            if d['n_interact'] is not None:
                f.write(f"  NInteractions:   {d['n_interact']}\n")
            f.write("\n")

    print(f"Done! Saved to {args.outdir}")


if __name__ == "__main__":
    main()