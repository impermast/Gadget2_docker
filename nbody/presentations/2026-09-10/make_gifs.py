#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
make_gifs.py — 2D и 3D эволюционные GIF для кампании k=0.8 (spin transition).

2D: face-on (xy) + edge-on (xz) поверхностная плотность, LogNorm, тёмная тема.
3D: вращающаяся камера (азимут 360° за прогон), scatter, цвет по радиусу.

Режимы:
  preview — пробные PNG среднего снапшота (по одному 2D/3D на run) в gif/preview/
  final   — сборка финальных GIF в gif/, временные файлы удаляются

Имена: s{sigma}_f{D}_{kind}.gif, например s2p5_f0p25_2d.gif
"""
import sys
import os
import tempfile
import shutil
from pathlib import Path

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.colors import LogNorm
from PIL import Image

REPO = Path("/home/kds/sci/gadget2_docker")
sys.path.insert(0, str(REPO / "nbody/scripts/plot_scripts"))
from loaders import read_snapshot, shrink_center, list_snapshots  # noqa: E402

BASE = REPO / "nbody/runs/dsidm_spin_k08_transition"
OUT = REPO / "nbody/presentations/2026-09-10/gif"
PREVIEW = OUT / "preview"

RUNS = [
    ("cdm_N1e5_T2",              "s0_f0",      "CDM   k=0.8  sigma=0    D=0"),
    ("sidm_s2p5_N1e5_T2",        "s2p5_f0",    "SIDM  k=0.8  sigma=2.5  D=0"),
    ("dsidm_s2p5_D0p10_N1e5_T2", "s2p5_f0p10", "dSIDM k=0.8  sigma=2.5  D=0.10"),
    ("dsidm_s2p5_D0p25_N1e5_T2", "s2p5_f0p25", "dSIDM k=0.8  sigma=2.5  D=0.25"),
    ("dsidm_s2p5_D0p50_N1e5_T2", "s2p5_f0p50", "dSIDM k=0.8  sigma=2.5  D=0.50"),
    ("dsidm_s2p5_D0p75_N1e5_T2", "s2p5_f0p75", "dSIDM k=0.8  sigma=2.5  D=0.75"),
]
GYR_PER_CODE = 0.9777923542981722
BG = "#0B1F3A"
TXT = "#E8EEF6"
ACC = "#4FC3F7"
plt.rcParams.update({
    "text.color": TXT, "axes.edgecolor": ACC, "axes.labelcolor": TXT,
    "xtick.color": TXT, "ytick.color": TXT, "font.family": "DejaVu Sans",
})

LIM = 30.0
BINS = 180
SUBSAMPLE_3D = 30000


def load_run(run_dir):
    files = list_snapshots(Path(run_dir) / "output")
    series, times, snaps = [], [], []
    for fp in files:
        d = read_snapshot(fp)
        c = shrink_center(d["pos"], d["mass"])
        pos = d["pos"] - c
        m = d["mass"]
        r = np.linalg.norm(pos, axis=1)
        keep = r < LIM * 1.5
        series.append((pos[keep], m[keep], r[keep]))
        times.append(d["time"] * GYR_PER_CODE)
        snaps.append(int(Path(fp).stem.split("_")[-1]))
    return series, np.array(times), snaps


def dens_map(p2):
    h, xe, ye = np.histogram2d(p2[:, 0], p2[:, 1], bins=BINS,
                               range=[[-LIM, LIM], [-LIM, LIM]])
    return h, xe, ye


def frame_2d(run_series, t, snap, label):
    """Двухпанельный кадр: face-on (xy) слева, edge-on (xz) справа."""
    pos, m, r = run_series
    fig = plt.figure(figsize=(9.6, 5.0), facecolor=BG)
    gs = fig.add_gridspec(1, 2, left=0.06, right=0.90, top=0.84, bottom=0.11,
                          wspace=0.14)
    for col, (cols, ttl) in enumerate([((0, 1), "face-on (xy)"),
                                       ((0, 2), "edge-on (xz)")]):
        ax = fig.add_subplot(gs[0, col], facecolor=BG)
        h, xe, ye = dens_map(pos[:, cols])
        vmax = h.max() + 1.0
        im = ax.pcolormesh(xe, ye, (h.T + 0.5) / 1e3,
                           norm=LogNorm(vmin=(vmax + 1) / 1e6, vmax=vmax / 1e3),
                           cmap="inferno", shading="auto", rasterized=True)
        ax.set_aspect("equal")
        ax.set_xlim(-LIM, LIM); ax.set_ylim(-LIM, LIM)
        ax.set_xticks([-20, 0, 20]); ax.set_yticks([-20, 0, 20])
        ax.tick_params(labelsize=8)
        ax.set_xlabel("x [kpc]", fontsize=10)
        ax.set_ylabel(("y" if col == 0 else "z") + " [kpc]", fontsize=10)
        ax.set_title(ttl, color=ACC, fontsize=12, pad=6)
    cax = fig.add_axes([0.92, 0.11, 0.022, 0.73])
    cb = fig.colorbar(im, cax=cax)
    cb.set_label(r"$\Sigma$ [$10^3\,M_\odot$/px], log", color=TXT, fontsize=9)
    cb.ax.tick_params(colors=TXT, labelsize=8)
    fig.suptitle(f"{label}    t = {t:.2f} Gyr  (snap {snap:03d})",
                 color=TXT, fontsize=13, y=0.96)
    return fig


def frame_3d(run_series, t, snap, label, azim):
    """3D scatter, вращающаяся камера; цвет по радиусу."""
    pos, m, r = run_series
    if len(pos) > SUBSAMPLE_3D:
        sel = np.random.RandomState(0).choice(len(pos), SUBSAMPLE_3D, replace=False)
        pos, r = pos[sel], r[sel]
    fig = plt.figure(figsize=(7.2, 7.2), facecolor=BG)
    ax = fig.add_subplot(111, projection="3d", facecolor=BG)
    sc = ax.scatter(pos[:, 0], pos[:, 1], pos[:, 2], c=r, cmap="viridis",
                    vmin=0, vmax=LIM, s=1.2, alpha=0.55, edgecolors="none",
                    rasterized=True)
    L = LIM
    ax.set_xlim(-L, L); ax.set_ylim(-L, L); ax.set_zlim(-L, L)
    ax.set_xticks([-20, 0, 20]); ax.set_yticks([-20, 0, 20]); ax.set_zticks([-20, 0, 20])
    ax.tick_params(colors=TXT, labelsize=7, pad=-2)
    for pane in (ax.xaxis, ax.yaxis, ax.zaxis):
        pane.pane.set_facecolor(BG)
        pane.pane.set_edgecolor(ACC)
        pane.pane.set_alpha(0.0)
    ax.view_init(elev=22, azim=azim)
    cb = fig.colorbar(sc, ax=ax, fraction=0.04, pad=0.02, shrink=0.75)
    cb.set_label("r [kpc]", color=TXT, fontsize=9)
    cb.ax.tick_params(colors=TXT, labelsize=8)
    ax.set_title(f"{label}\nt = {t:.2f} Gyr  (snap {snap:03d})",
                 color=TXT, fontsize=12, pad=0)
    return fig


def build_run(run_dir, tag, label, kind, preview):
    series, times, snaps = load_run(run_dir)
    n = len(times)
    frames_dir = tempfile.mkdtemp(prefix=f"gif_{tag}_{kind}_")
    try:
        files = []
        for i in range(n):
            if kind == "2d":
                fig = frame_2d(series[i], times[i], snaps[i], label)
            else:
                azim = 30.0 + 360.0 * i / max(n - 1, 1)
                fig = frame_3d(series[i], times[i], snaps[i], label, azim)
            fp = os.path.join(frames_dir, f"f{i:03d}.png")
            fig.savefig(fp, dpi=110, facecolor=BG)
            plt.close(fig)
            files.append(fp)
        if preview:
            dst = PREVIEW / f"preview_{tag}_{kind}.png"
            shutil.copy(files[n // 2], dst)
            print(f"  preview: {dst}")
        else:
            imgs = [Image.open(p).convert("P", palette=Image.ADAPTIVE, colors=256)
                    for p in files]
            dst = OUT / f"{tag}_{kind}.gif"
            imgs[0].save(dst, save_all=True, append_images=imgs[1:],
                         duration=180, loop=0)
            print(f"  saved: {dst}")
    finally:
        shutil.rmtree(frames_dir, ignore_errors=True)


def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else "preview"
    only = sys.argv[2] if len(sys.argv) > 2 else None
    PREVIEW.mkdir(parents=True, exist_ok=True)
    OUT.mkdir(parents=True, exist_ok=True)
    for run_dir, tag, label in RUNS:
        if only and only not in tag:
            continue
        print(f"{tag} ({run_dir}):")
        build_run(BASE / run_dir, tag, label, "2d", preview=(mode == "preview"))
        build_run(BASE / run_dir, tag, label, "3d", preview=(mode == "preview"))


if __name__ == "__main__":
    main()
