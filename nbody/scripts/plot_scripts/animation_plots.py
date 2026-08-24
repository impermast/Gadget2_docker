#!/usr/bin/env python3
"""
animation_plots.py — эволюционные анимации частиц (GIF).

Оба plots получают одинаковые подготовленные series-данные
(loaders.prepare_series): positions (T, N, 3) — уже halo-centered
(shrinkage center), masses (T, N), times (T,) в кодовых единицах.

- particles_2d: проекция плотности xy (hist2d) — перенос make_run_evolution.py;
- particles_3d: 3D scatter с цветом по log(r), wireframe-куб, scale bar —
  перенос make_3d_animation.py (reference implementation).

Временная конвертация: t_Gyr = t_code * GYR_PER_CODE.
"""

from __future__ import annotations

import os
import shutil
import tempfile
from pathlib import Path
from typing import Any, Dict, Mapping

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.colors import LogNorm
from PIL import Image

from base import BasePlot, F

GYR_PER_CODE = 0.9777923542981722


def _save_gif(frame_paths, out_path, duration_ms: int,
              palette_colors=None) -> Path:
    """Собрать GIF из PNG-кадров через PIL (imageio в контейнере нет)."""
    if palette_colors:
        imgs = [Image.open(p).convert("P", palette=Image.ADAPTIVE,
                                      colors=palette_colors)
                for p in frame_paths]
    else:
        imgs = [Image.open(p).convert("RGB") for p in frame_paths]
    imgs[0].save(out_path, save_all=True, append_images=imgs[1:],
                 duration=int(duration_ms), loop=0)
    return Path(out_path)


def _series_contract():
    return {
        "positions": F(("T", "N", 3)),
        "masses": F(("T", "N"), required=False),
        "times": F(("T",)),
        "snapshot_numbers": F(("T",), dtype="integer", required=False),
    }


# ──────────────────────────── 2D animation ──────────────────────────────────

class Particles2DAnimation(BasePlot):
    name = "particles_2d"
    description = (
        "Эволюционная GIF: проекция массовой плотности halo на плоскость xy "
        "(hist2d, log colorbar). Серия HDF5 snapshot'ов одного run; данные "
        "готовит loaders.prepare_series() — позиции уже shrinkage-центрированы. "
        "Размер поля (lim) авто по финальному кадру."
    )
    data_contract = _series_contract()
    default_config = {
        "fps": 4,
        "cmap": "inferno",
        "bins": 220,
        "lim": None,               # None = auto (98 percentile финального кадра)
        "min_lim": 10.0,
        "dpi": 110,
        "gyr_per_code": GYR_PER_CODE,
        "sigma_label": None,       # напр. 20 -> "sigma=20" в заголовке
        "colorbar_label": "mass per pixel",
        "filename": "evolution_2d.gif",
    }

    def render(self, data: Mapping[str, Any], config: Dict[str, Any]):
        positions = np.asarray(data["positions"], dtype=np.float64)
        times = np.asarray(data["times"], dtype=float)
        n_frames = len(times)

        masses = data.get("masses")
        weights_all = (np.asarray(masses, dtype=np.float64)
                       if masses is not None
                       else np.ones(positions.shape[:2]))

        lim = config.get("lim")
        if lim is None:
            r_last = np.linalg.norm(positions[-1], axis=1)
            lim = max(float(np.percentile(r_last[r_last > 0], 98)),
                      float(config["min_lim"]))

        frames_dir = tempfile.mkdtemp(prefix="nbody2d_")
        try:
            frame_files = []
            for i in range(n_frames):
                p, w = positions[i], weights_all[i]
                fig, ax = plt.subplots(figsize=(6, 6))
                hh = ax.hist2d(p[:, 0], p[:, 1], bins=config["bins"],
                               range=[[-lim, lim], [-lim, lim]],
                               weights=w, norm=LogNorm(), cmap=config["cmap"])
                ax.set_aspect("equal")
                ax.set_xlabel("x [kpc]")
                ax.set_ylabel("y [kpc]")
                sig_txt = "" if not config.get("sigma_label") \
                    else f"   sigma={config['sigma_label']:g}"
                ax.set_title(f"t={times[i]:.2f} "
                             f"({times[i] * config['gyr_per_code']:.2f} Gyr)"
                             f"{sig_txt}   N={len(p):d}")
                cb = fig.colorbar(hh[3], ax=ax, fraction=0.046)
                cb.set_label(config["colorbar_label"])
                fp = os.path.join(frames_dir, f"frame_{i:03d}.png")
                fig.savefig(fp, dpi=config["dpi"], bbox_inches="tight")
                plt.close(fig)
                frame_files.append(fp)
            out = _save_gif(frame_files, config["filename"],
                            duration_ms=1000 / max(float(config["fps"]), 1e-6))
        finally:
            shutil.rmtree(frames_dir, ignore_errors=True)
        return out


# ──────────────────────────── 3D animation ──────────────────────────────────

class Particles3DAnimation(BasePlot):
    name = "particles_3d"
    description = (
        "Эволюционная GIF: настоящая 3D-визуализация частиц (scatter в осях "
        "projection='3d'), цвет по log(радиусу), тёмный фон, wireframe-куб и "
        "scale bar. Серия HDF5 snapshot'ов; данные готовит "
        "loaders.prepare_series(). Reference: старый make_3d_animation.py."
    )
    data_contract = _series_contract()
    default_config = {
        "max_points": 100_000,     # даунсэмпл на кадр (как в старом коде)
        "cmap": "inferno",
        "point_size": 2.2,
        "alpha": 0.82,
        "wireframe": True,
        "scale_bar": True,
        "label": "",               # подпись run/модели в кадре
        "duration_ms": 280,
        "gif_palette_colors": 180,
        "seed": 42,
        "filename": "evolution_3d.gif",
    }

    # --- элементы кадра (перенесено из make_3d_animation.draw) ---------------

    def _draw_frame(self, ax, pos, settings, cfg, snap_num, t_gyr):
        rng = np.random.default_rng(cfg["seed"] + snap_num)
        if len(pos) > cfg["max_points"]:
            pos = pos[rng.choice(len(pos), cfg["max_points"], replace=False)]

        r = np.linalg.norm(pos, axis=1)
        col = np.log10(r + 1e-6)
        vmin, vmax = np.percentile(col, 2), np.percentile(col, 98)
        # lim фиксируем геометрией текущего кадра (99 percentile), как в оригинале
        lim = max(float(np.percentile(np.abs(pos), 99) * 1.02), 35.0)

        bg = settings.background_3d
        ax.set_facecolor(bg)
        ax.set_axis_off()
        for pane in [ax.xaxis.pane, ax.yaxis.pane, ax.zaxis.pane]:
            pane.set_facecolor(bg)
            pane.set_alpha(0.0)

        L = lim
        edges = [
            ([-L, L], [-L, -L], [-L, -L]), ([L, L], [-L, L], [-L, -L]),
            ([L, -L], [L, L], [-L, -L]), ([-L, -L], [L, L], [-L, -L]),
            ([-L, L], [-L, -L], [L, L]), ([L, L], [-L, L], [L, L]),
            ([L, -L], [L, L], [L, L]), ([-L, -L], [L, L], [L, L]),
            ([-L, -L], [-L, -L], [-L, L]), ([L, L], [-L, -L], [-L, L]),
            ([L, L], [L, L], [-L, L]), ([-L, -L], [L, L], [-L, L]),
        ]
        if cfg["wireframe"]:
            for ex, ey, ez in edges:
                ax.plot(ex, ey, ez, color="#D0D0D0", lw=1.1, alpha=0.22)

        ax.scatter(pos[:, 0], pos[:, 1], pos[:, 2],
                   c=col, cmap=cfg["cmap"], vmin=vmin, vmax=vmax,
                   s=cfg["point_size"], alpha=cfg["alpha"], edgecolors="none")
        ax.set_xlim(-lim, lim)
        ax.set_ylim(-lim, lim)
        ax.set_zlim(-lim, lim)
        ax.view_init(**settings.view_3d)

        if cfg["label"]:
            ax.text2D(0.035, 0.08, str(cfg["label"]), transform=ax.transAxes,
                      color="#FFFFFF", fontsize=28, weight="bold",
                      va="bottom", ha="left")
        ax.text2D(0.035, 0.02, f"snap {snap_num}   t = {t_gyr:.2f} Gyr",
                  transform=ax.transAxes, color="#F2F2F2", fontsize=22,
                  va="bottom", ha="left")

        if cfg["scale_bar"]:
            bar_len = 500 if lim >= 600 else (100 if lim >= 120 else 50)
            x0 = -lim + 0.08 * (2 * lim)
            y0 = -lim + 0.14 * (2 * lim)
            z0 = -lim
            x1 = x0 + bar_len
            ax.plot([x0, x1], [y0, y0], [z0, z0],
                    color="#FFFFFF", lw=3.5, alpha=0.9)
            tick = 3.5
            ax.plot([x0, x0], [y0, y0], [z0, z0 + tick],
                    color="#FFFFFF", lw=2.0, alpha=0.9)
            ax.plot([x1, x1], [y0, y0], [z0, z0 + tick],
                    color="#FFFFFF", lw=2.0, alpha=0.9)
            ax.text2D(0.12, 0.32, f"{bar_len} kpc", transform=ax.transAxes,
                      color="#FFFFFF", fontsize=18, ha="center", va="top")

        ax.set_position([0, 0, 1, 1])

    def render(self, data: Mapping[str, Any], config: Dict[str, Any]):
        positions = np.asarray(data["positions"], dtype=np.float64)
        times = np.asarray(data["times"], dtype=float)
        snap_numbers = (np.asarray(data.get("snapshot_numbers"), dtype=int)
                        if data.get("snapshot_numbers") is not None
                        else np.arange(len(times)))
        gyr = GYR_PER_CODE

        frames_dir = tempfile.mkdtemp(prefix="nbody3d_")
        try:
            frame_files = []
            for i in range(len(times)):
                fig = plt.figure(figsize=self.settings.figure_size_3d,
                                 dpi=self.settings.dpi_3d)
                fig.patch.set_edgecolor("none")
                fig.subplots_adjust(left=0, right=1, top=1, bottom=0)
                ax = fig.add_subplot(111, projection="3d")
                self._draw_frame(ax, positions[i], self.settings, config,
                                 int(snap_numbers[i]), times[i] * gyr)
                fp = os.path.join(frames_dir, f"frame_{i:03d}.png")
                fig.savefig(fp, dpi=self.settings.dpi_3d,
                            bbox_inches="tight", pad_inches=0)
                plt.close(fig)
                frame_files.append(fp)
            out = _save_gif(frame_files, config["filename"],
                            duration_ms=config["duration_ms"],
                            palette_colors=config.get("gif_palette_colors"))
        finally:
            shutil.rmtree(frames_dir, ignore_errors=True)
        return out


ANIMATION_PLOT_CLASSES = [Particles2DAnimation, Particles3DAnimation]
