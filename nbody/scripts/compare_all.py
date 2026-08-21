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

def make_common_log_edges(all_data, rmin=5.0, rmax=500.0, nbins=70):
    return np.logspace(np.log10(rmin), np.log10(rmax), nbins + 1)


def radial_density_profile(data, edges=None, nbins=70, rmin=5.0, rmax=500.0):
    _, _, r, _ = centered_phase(data)
    mass = data["mass"] if data["mass"] is not None else np.ones_like(r)

    mask = np.isfinite(r) & (r > 0) & np.isfinite(mass) & (mass > 0)
    r = r[mask]
    mass = mass[mask]

    if edges is None:
        edges = np.logspace(np.log10(rmin), np.log10(rmax), nbins + 1)

    centers = np.sqrt(edges[:-1] * edges[1:])

    shell_mass, _ = np.histogram(r, bins=edges, weights=mass)
    counts, _ = np.histogram(r, bins=edges)

    shell_volume = 4.0 / 3.0 * np.pi * (edges[1:]**3 - edges[:-1]**3)

    rho = np.full_like(centers, np.nan, dtype=float)
    good = counts > 0
    rho[good] = shell_mass[good] / shell_volume[good]

    return centers, rho, counts

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

def log_slope_profile_local(
    r_centers,
    rho,
    counts=None,
    min_count=10,
    half_width_dex=0.16,
    min_points=4,
    require_both_sides=True,
):
    """
    Локальный наклон d log(rho) / d log(r)
    через fit log(rho) = a + b log(r).

    half_width_dex=0.16 означает окно примерно в factor 10^0.16 = 1.45
    вокруг текущего радиуса.
    """

    r = np.asarray(r_centers, dtype=float)
    y = np.asarray(rho, dtype=float)

    valid = np.isfinite(r) & np.isfinite(y) & (r > 0) & (y > 0)

    if counts is not None:
        counts = np.asarray(counts, dtype=float)
        valid &= np.isfinite(counts) & (counts >= min_count)

    slope = np.full_like(y, np.nan, dtype=float)

    if np.sum(valid) < min_points:
        return slope

    log_r = np.log10(r)
    log_y = np.log10(y)

    for i in np.where(valid)[0]:
        use = valid & (np.abs(log_r - log_r[i]) <= half_width_dex)

        if require_both_sides:
            has_left = np.any(use & (log_r < log_r[i]))
            has_right = np.any(use & (log_r > log_r[i]))
            if not (has_left and has_right):
                continue

        if np.sum(use) < min_points:
            continue

        x = log_r[use]
        yy = log_y[use]

        if counts is not None:
            w = np.sqrt(counts[use])
            w = w / np.nanmedian(w)
        else:
            w = None

        try:
            p = np.polyfit(x, yy, deg=1, w=w)
            slope[i] = p[0]
        except Exception:
            slope[i] = np.nan

    return slope


def nfw_log_slope(r, rs):
    r = np.asarray(r, dtype=float)
    return -1.0 - 2.0 * r / (r + rs)

# ──────────────────────────── NFW / core fits ───────────────────────────────

def nfw_profile(r, rho0, rs):
    x = r / rs
    return rho0 / (x * (1 + x) ** 2)


def core_profile(r, rho0, rc):
    return rho0 / (1.0 + (r / rc) ** 2)

def fit_nfw_logspace(r_centers, rho, rmin=None, rmax=None, weights=None):
    """
    Fit NFW profile in log-space:
        rho(r) = rho_s / ((r/r_s) * (1 + r/r_s)^2)

    Parameters
    ----------
    r_centers : array
        Radial bin centers.
    rho : array
        Density profile.
    rmin, rmax : float or None
        Fit range.
    weights : array or None
        Optional statistical weights. For example, number of particles per bin.

    Returns
    -------
    popt : tuple or None
        (rho_s, r_s)
    func : callable or None
        nfw_profile
    info : dict
        Fit diagnostics.
    """

    r = np.asarray(r_centers, dtype=float)
    y = np.asarray(rho, dtype=float)

    mask = np.isfinite(r) & np.isfinite(y) & (r > 0) & (y > 0)

    if rmin is not None:
        mask &= r >= rmin
    if rmax is not None:
        mask &= r <= rmax

    if np.sum(mask) < 6:
        return None, None, {"reason": "too few valid points", "n": int(np.sum(mask))}

    r = r[mask]
    y = y[mask]
    log_y = np.log(y)

    if weights is None:
        w = np.ones_like(log_y)
    else:
        weights = np.asarray(weights, dtype=float)[mask]
        weights = np.where(np.isfinite(weights) & (weights > 0), weights, 1.0)
        w = np.sqrt(weights / np.nanmedian(weights))

    # Grid search for initial r_s
    rs_grid = np.logspace(np.log10(r.min() / 5.0), np.log10(r.max() * 5.0), 500)

    best_chi2 = np.inf
    best_q = None

    for rs in rs_grid:
        x = r / rs
        base = -np.log(x) - 2.0 * np.log1p(x)

        # For fixed r_s, optimal log(rho_s) in weighted log-LS
        log_rhos = np.average(log_y - base, weights=w**2)

        res = w * (log_rhos + base - log_y)
        chi2 = np.sum(res**2)

        if np.isfinite(chi2) and chi2 < best_chi2:
            best_chi2 = chi2
            best_q = np.array([log_rhos, np.log(rs)])

    if best_q is None:
        return None, None, {"reason": "grid search failed"}

    # Optional scipy refinement
    try:
        from scipy.optimize import least_squares

        def residual(q):
            log_rhos, log_rs = q
            rs = np.exp(log_rs)
            x = r / rs
            log_model = log_rhos - np.log(x) - 2.0 * np.log1p(x)
            return w * (log_model - log_y)

        result = least_squares(
            residual,
            best_q,
            loss="soft_l1",
            f_scale=1.0,
            max_nfev=5000
        )

        q = result.x if result.success else best_q

    except Exception:
        q = best_q

    rho_s = float(np.exp(q[0]))
    r_s = float(np.exp(q[1]))

    x = r / r_s
    log_model = np.log(rho_s) - np.log(x) - 2.0 * np.log1p(x)
    rms_log = float(np.sqrt(np.mean((log_model - log_y) ** 2)))

    info = {
        "n": len(r),
        "rho_s": rho_s,
        "r_s": r_s,
        "rms_log": rms_log,
        "rmin": float(r.min()),
        "rmax": float(r.max())
    }

    return (rho_s, r_s), nfw_profile, info


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
    fig, (ax, axr) = plt.subplots(
        2, 1,
        figsize=(S["page"][0], S["page"][1] * 1.15),
        sharex=True,
        gridspec_kw={"height_ratios": [3.0, 1.15], "hspace": 0.05}
    )

    xlim = (5.0, 500.0)

    # CDM должен быть первым профилем
    r_cdm, rho_cdm, counts_cdm, _, _ = all_profiles[0]

    r_cdm = np.asarray(r_cdm, dtype=float)
    rho_cdm = np.asarray(rho_cdm, dtype=float)
    counts_cdm = np.asarray(counts_cdm, dtype=float)

    norm_mask = (
        np.isfinite(r_cdm)
        & np.isfinite(rho_cdm)
        & (r_cdm >= xlim[0])
        & (r_cdm <= xlim[1])
        & (rho_cdm > 0)
        & (counts_cdm >= 20)
    )

    if np.sum(norm_mask) == 0:
        raise RuntimeError("No valid CDM points for normalization.")

    # Более устойчивая нормировка, чем mean по всем log-бинам
    rho_norm = np.nanmedian(rho_cdm[norm_mask])

    plotted_y = []

    for i, (r, rho, counts, label, c) in enumerate(all_profiles):
        r = np.asarray(r, dtype=float)
        rho = np.asarray(rho, dtype=float)
        counts = np.asarray(counts, dtype=float)

        mask = (
            np.isfinite(r)
            & np.isfinite(rho)
            & (r > 0)
            & (rho > 0)
            & (counts >= 5)
        )

        y = np.full_like(rho, np.nan, dtype=float)
        y[mask] = rho[mask] / rho_norm

        ax.plot(
            r[mask],
            y[mask],
            color=c,
            lw=2.0 if i == 0 else 1.5,
            alpha=1.0 if i == 0 else 0.85,
            label=label,
            zorder=5 if i == 0 else 3
        )

        # Отношение к CDM только на общей сетке
        ratio_mask = (
            mask
            & np.isfinite(rho_cdm)
            & (rho_cdm > 0)
            & (counts_cdm >= 5)
        )

        ratio = np.full_like(rho, np.nan, dtype=float)
        ratio[ratio_mask] = rho[ratio_mask] / rho_cdm[ratio_mask]

        axr.plot(
            r[ratio_mask],
            ratio[ratio_mask],
            color=c,
            lw=1.5,
            alpha=1.0 if i == 0 else 0.85
        )

        vis = (
            mask
            & (r >= xlim[0])
            & (r <= xlim[1])
            & np.isfinite(y)
            & (y > 0)
        )
        if np.any(vis):
            plotted_y.append(y[vis])

    # NFW fit for CDM
    fit_rmin = 10.0
    fit_rmax = 350.0
    min_count_fit = 30

    fit_mask = (
        np.isfinite(r_cdm)
        & np.isfinite(rho_cdm)
        & (rho_cdm > 0)
        & (r_cdm >= fit_rmin)
        & (r_cdm <= fit_rmax)
        & (counts_cdm >= min_count_fit)
    )

    print("NFW fit points:", int(np.sum(fit_mask)))
    if np.sum(fit_mask) >= 6:
        popt_nfw, func_nfw, info = fit_nfw_logspace(
            r_cdm,
            rho_cdm,
            rmin=fit_rmin,
            rmax=fit_rmax,
            weights=counts_cdm
        )

        print("NFW fit info:", info)

        if popt_nfw is not None:
            r_fit = np.logspace(np.log10(fit_rmin), np.log10(fit_rmax), 300)
            rho_fit = func_nfw(r_fit, *popt_nfw)
            y_fit = rho_fit / rho_norm

            ax.plot(
                r_fit,
                y_fit,
                "--",
                lw=2.0,
                color="black",
                label=rf"NFW fit, $r_s={popt_nfw[1]:.1f}$ kpc",
                zorder=20
            )

            plotted_y.append(y_fit[np.isfinite(y_fit) & (y_fit > 0)])
    else:
        print("NFW fit skipped: too few populated bins in fit range.")

    apply(
        ax,
        ylabel=r"$\rho(r)/\langle\rho_{\rm CDM}\rangle$",
        xscale="log",
        yscale="log",
        legend=True,
        grid=False
    )

    apply(
        axr,
        xlabel="r [kpc]",
        ylabel=r"$\rho/\rho_{\rm CDM}$",
        xscale="log",
        grid=False,
    )

    ax.set_xlim(*xlim)
    axr.set_xlim(*xlim)
    axr.set_ylim(0.5, 1.5)

    if plotted_y:
        yy = np.concatenate(plotted_y)
        yy = yy[np.isfinite(yy) & (yy > 0)]

        if len(yy) > 0:
            ymin = np.nanpercentile(yy, 1)
            ymax = np.nanpercentile(yy, 99)

            ymin = 10 ** (np.floor(np.log10(ymin)) - 0.1)
            ymax = 10 ** (np.ceil(np.log10(ymax)) + 0.1)

            ax.set_ylim(ymin, ymax)


    fig.savefig(outpath, dpi=300, bbox_inches="tight")
    plt.close(fig)

def plot_all_slope_profiles(all_profiles, outpath):
    fig, ax = plt.subplots(figsize=S["page"])

    for i, (r, rho, counts, label, c) in enumerate(all_profiles):
        slope = log_slope_profile_local(
            r,
            rho,
            counts=counts,
            min_count=1,
            half_width_dex=0.12,
            min_points=5,
            require_both_sides=True,
        )

        print(
            label,
            "bins =", len(r),
            "rho valid =", np.sum(np.isfinite(rho) & (rho > 0)),
            "counts>=1 =", np.sum(np.asarray(counts) >= 1),
            "slope finite =", np.sum(np.isfinite(slope)),
        )

        mask = np.isfinite(r) & np.isfinite(slope) & (r > 0)

        ax.plot(
            r[mask],
            slope[mask],
            color=c,
            lw=2.0 if i == 0 else 1.6,
            label=label,
        )

    # NFW analytic slope for CDM fit
    r_cdm, rho_cdm, counts_cdm, _, _ = all_profiles[0]

    fit_mask = (
        np.isfinite(r_cdm)
        & np.isfinite(rho_cdm)
        & np.isfinite(counts_cdm)
        & (r_cdm > 0)
        & (rho_cdm > 0)
        & (counts_cdm >= 20)
    )

    if np.sum(fit_mask) >= 6:
        popt_nfw, _, info = fit_nfw_logspace(
            r_cdm[fit_mask],
            rho_cdm[fit_mask],
            weights=counts_cdm[fit_mask],
        )

        if popt_nfw is not None:
            rs_nfw = popt_nfw[1]

            r_fit = np.logspace(np.log10(1.0), np.log10(80.0), 300)
            slope_fit = nfw_log_slope(r_fit, rs_nfw)

            ax.plot(
                r_fit,
                slope_fit,
                color="black",
                ls="--",
                lw=1.8,
                label=rf"NFW slope, $r_s={rs_nfw:.1f}$ kpc",
                zorder=20,
            )

            print(f"NFW slope overlay: r_s = {rs_nfw:.3f} kpc")

    # ax.axhline(-1.0, color="0.35", lw=0.9, ls=":", alpha=0.7)
    # ax.axhline(-2.0, color="0.35", lw=0.9, ls=":", alpha=0.7)
    # ax.axhline(-3.0, color="0.35", lw=0.9, ls=":", alpha=0.7)

    apply(
        ax,
        xlabel="r [kpc]",
        ylabel=r"$d\log\rho/d\log r$",
        xscale="log",
        legend=True,
        grid=False,
    )

    ax.set_xlim(1.0, 80.0)
    ax.set_ylim(-4.2, 0.3)
    ax.set_xticks([1, 2, 5, 10, 20, 50, 80])

    sf = plt.ScalarFormatter()
    sf.set_scientific(False)
    ax.get_xaxis().set_major_formatter(sf)

    fig.savefig(outpath, dpi=300, bbox_inches="tight")
    plt.close(fig)

def plot_all_sigma_profiles(all_sigmas, outpath):
    fig, ax = plt.subplots(figsize=S["page"])
    for i, (r, sig, label, c) in enumerate(all_sigmas):
        ax.plot(r, sig, color=c, lw=1.5, label=label)
    apply(ax, "1D velocity dispersion profiles", xlabel="r [kpc]",
          ylabel=r"$\sigma_{1D} [km/s]$", xscale="log", legend=True)
    ax.set_xlim(5, 800)      
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
    # Прячем неиспользуемые субплоты, последний отдаём под colorbar
    for i in range(n, len(axes) - 1):
        axes[i].set_visible(False)
    if n < len(axes):
        axes[-1].set_visible(False)
        cax = axes[-1].inset_axes([0.2, 0.3, 0.4, 0.4])
        fig.colorbar(im, cax=cax).set_label("Projected mass")
    else:
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

    from itertools import cycle
    colors = list(COLORS.palette)
    color_iter = cycle(colors)

    edges = make_common_log_edges(
        all_data,
        rmin=1.0,
        rmax=1000.0,
        nbins=60
    )

    for i, (d, label) in enumerate(zip(all_data, labels)):
        c = next(color_iter)

        r, rho, counts = radial_density_profile(d, edges=edges)
        all_profiles.append((r, rho, counts, label, c))

        rs, sig = radial_sigma_profile(d, nbins=70)
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
            r, rho, counts = radial_density_profile(d)
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