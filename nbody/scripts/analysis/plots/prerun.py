#!/usr/bin/env python3
"""plots/prerun — блок prerun реестра: ранний гейт + диагностика серии.

Оформление дословно из гейтов (early_cdm_gate.py: cusp_compare 3 панели;
analyze_series.py: plot_lines 3 панели + contact_sheet faceon/edgeon;
compare_shape_series.py: plot_compare 5 панелей). Данные — plot-ready dicts
из loaders/prerun (prepare_early_figure_data / metrics_series.csv /
prepare_series_frames / prepare_shape_figure_data). HDF5 plots не читают.
"""
from __future__ import annotations

from typing import Any, Dict, Mapping

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.colors import LogNorm

from analysis.base import (
    BasePlot,
    FieldSpec as F,
)
from analysis.registry import register


@register
class EarlyCuspComparePlot(BasePlot):
    name = "early_cusp_compare"
    block = "prerun"
    summary = "Ранний гейт: IC vs snapshot vs target + сохранение каспа"
    data_source = "prepare_early_figure_data"
    inputs = ("run",)
    runner = "runners/make_prerun_plots.py"
    description = (
        "Три панели early_cdm_gate.py (cusp_compare): density IC/snap/target "
        "с gate-диапазоном, наклоны IC/snap/target с опорой -1.0, отношение "
        "rho_snap/rho_IC (сохранение каспа). Данные — profiles.csv гейта."
    )
    data_contract = {
        "r_kpc": F(("R",)),
        "rho_ic": F(("R",)),
        "rho_snap": F(("R",)),
        "count_ic": F(("R",)),
        "count_snap": F(("R",)),
        "slope_ic": F(("R",), required=False),
        "slope_snap": F(("R",), required=False),
        "rho_target": F(("R",), required=False),
        "slope_target": F(("R",), required=False),
    }
    default_config = {
        "title": "Early gate: IC vs snapshot",
        "gate_range": (0.3, 3.0),
        "dpi": 130,
        "figsize": (16, 4.8),
        "filename": "early_cusp_compare.png",
    }

    def render(self, data: Mapping[str, Any], config: Dict[str, Any]):
        centers = np.asarray(data["r_kpc"], dtype=float)
        rho_ic = np.asarray(data["rho_ic"], dtype=float)
        rho_sn = np.asarray(data["rho_snap"], dtype=float)
        cnt_ic = np.asarray(data["count_ic"], dtype=float)
        cnt_sn = np.asarray(data["count_snap"], dtype=float)
        rlo, rhi = config.get("gate_range", (0.3, 3.0))
        fig, ax = plt.subplots(1, 3, figsize=tuple(config.get("figsize", (16, 4.8))))
        g_ic = (rho_ic > 0) & (cnt_ic > 0)
        g_sn = (rho_sn > 0) & (cnt_sn > 0)
        ax[0].loglog(centers[g_ic], rho_ic[g_ic], "o-", ms=3, label="GalIC IC")
        ax[0].loglog(centers[g_sn], rho_sn[g_sn], "s-", ms=3,
                     label="first snapshot")
        if data.get("rho_target") is not None:
            ax[0].loglog(centers, np.asarray(data["rho_target"], dtype=float),
                         "k--", label="analytic target (NFW fit)")
        ax[0].axvspan(rlo, rhi, color="0.85", alpha=0.5, label="gate range")
        ax[0].set_xlabel("r [kpc]")
        ax[0].set_ylabel("rho [1e10 Msun/kpc^3]")
        ax[0].legend(fontsize=8)
        ax[0].set_title(f"density: IC vs snapshot (t={config.get('time', 0):.4g})")
        if data.get("slope_ic") is not None:
            ax[1].semilogx(centers, np.asarray(data["slope_ic"], dtype=float),
                           "o-", ms=3, label="IC")
        if data.get("slope_snap") is not None:
            ax[1].semilogx(centers, np.asarray(data["slope_snap"], dtype=float),
                           "s-", ms=3, label="snapshot")
        if data.get("slope_target") is not None:
            ax[1].semilogx(centers, np.asarray(data["slope_target"], dtype=float),
                           "k--", label="target")
        ax[1].axhline(-1.0, color="r", ls=":", lw=1)
        ax[1].axvspan(rlo, rhi, color="0.85", alpha=0.5)
        ax[1].set_xlabel("r [kpc]")
        ax[1].set_ylabel("d log rho / d log r")
        ax[1].legend(fontsize=8)
        ax[1].set_title("local logarithmic slope")
        ok = centers > 0
        with np.errstate(divide="ignore", invalid="ignore"):
            ratio = np.where(rho_sn > 0, rho_sn, np.nan)[ok] / \
                np.where(rho_ic > 0, rho_ic, np.nan)[ok]
        ax[2].semilogx(centers[ok], ratio, "d-", ms=3, label="rho_snap/rho_IC")
        ax[2].axhline(1.0, color="r", ls=":")
        ax[2].axvspan(rlo, rhi, color="0.85", alpha=0.5)
        ax[2].set_xlabel("r [kpc]")
        ax[2].set_ylabel("ratio")
        ax[2].set_ylim(0.8, 1.2)
        ax[2].legend(fontsize=8)
        ax[2].set_title("density change (cusp preservation)")
        fig.suptitle(config.get("title", ""))
        fig.tight_layout()
        path = self.settings.save_figure(fig, config["filename"],
                                         dpi=config.get("dpi"))
        plt.close(fig)
        return path

@register
class SeriesEvolutionPlot(BasePlot):
    name = "series_evolution"
    block = "prerun"
    summary = "Эволюция серии: плотность ядра, форма, NI по времени"
    data_source = "metrics_series.csv"
    inputs = ("run",)
    runner = "runners/make_prerun_plots.py"
    description = (
        "Три панели analyze_series.py (plot_lines): rho_core(r<2) по времени "
        "(log), c/a(r<5)+z/R по времени, mean|vphi| + NInteractions total "
        "(twin-linear/log). Данные — metrics_series.csv."
    )
    data_contract = {
        "time": F(("T",)),
        "rho_core_r2": F(("T",)),
        "ca_r5": F(("T",)),
        "z_rms_over_R_rms_r5": F(("T",)),
        "mean_vphi_r5": F(("T",)),
        "ninteractions_total": F(("T",)),
    }
    default_config = {
        "title": "Run-series evolution",
        "dpi": 150,
        "figsize": (12, 9),
        "filename": "series_evolution.png",
    }

    def render(self, data: Mapping[str, Any], config: Dict[str, Any]):
        t = np.asarray(data["time"], dtype=float)
        rho = np.asarray(data["rho_core_r2"], dtype=float)
        ca = np.asarray(data["ca_r5"], dtype=float)
        thick = np.asarray(data["z_rms_over_R_rms_r5"], dtype=float)
        vphi = np.asarray(data["mean_vphi_r5"], dtype=float)
        ni = np.asarray(data["ninteractions_total"], dtype=float)
        fig, axes = plt.subplots(3, 1, figsize=tuple(config.get("figsize", (12, 9))),
                                 sharex=True)
        axes[0].plot(t, rho, marker="o", lw=1.4, ms=4)
        axes[0].set_yscale("log")
        axes[0].set_ylabel("rho_core r<2")
        axes[0].grid(True, alpha=0.3)
        axes[1].plot(t, ca, marker="o", lw=1.4, ms=4, label="c/a r<5")
        axes[1].plot(t, thick, marker="s", lw=1.4, ms=4, label="z_rms/R_rms r<5")
        axes[1].set_ylabel("shape")
        axes[1].legend(frameon=False, fontsize=9)
        axes[1].grid(True, alpha=0.3)
        (ln1,) = axes[2].plot(t, np.abs(vphi), marker="o", lw=1.4, ms=4,
                              label="mean|vphi| r<5")
        axes[2].set_ylabel("mean|vphi|")
        ax2 = axes[2].twinx()
        positive_ni = np.isfinite(ni) & (ni > 0)
        if positive_ni.any():
            (ln2,) = ax2.plot(t[positive_ni], ni[positive_ni], marker="s",
                              lw=1.2, ms=4, color="tab:red",
                              label="NInteractions total")
            ax2.set_yscale("log")
        else:
            ax2.set_ylim(0, 1)
            (ln2,) = ax2.plot([], [], marker="s", lw=1.2, ms=4,
                              color="tab:red", label="NInteractions total = 0")
        ax2.set_ylabel("NInteractions")
        axes[2].set_xlabel("Time [code units]")
        axes[2].grid(True, alpha=0.3)
        axes[2].legend(handles=[ln1, ln2], frameon=False, fontsize=9)
        fig.suptitle(config.get("title", ""))
        fig.tight_layout()
        path = self.settings.save_figure(fig, config["filename"],
                                         dpi=config.get("dpi"))
        plt.close(fig)
        return path


@register
class ShapePanelPlot(BasePlot):
    name = "shape_panel"
    block = "prerun"
    summary = "Сравнение shape-серий группы: 5 панелей по времени"
    data_source = "metrics_series.csv (группа)"
    inputs = ("runs",)
    runner = "runners/make_prerun_plots.py"
    description = (
        "Пять панелей compare_shape_series.py (plot_compare): c/a, thickness, "
        "rotation support, NInteractions, rho_core по времени для каждого run. "
        "Данные — metrics_series.csv каждого прогона группы."
    )
    data_contract = {
        "panels": F(("P",), dtype="any"),
    }
    default_config = {
        "title": "Shape series comparison",
        "dpi": 170,
        "figsize": (11.5, 5.8),
        "filename": "shape_panel_{key}.png",
    }

    def validate_data(self, data):
        panels = data.get("panels")
        if not isinstance(panels, (list, tuple)) or not panels:
            from analysis.base import PlotValidationError
            raise PlotValidationError(
                f"{self.name}: data['panels'] must be a non-empty list")
        for i, p in enumerate(panels):
            for k in ("title", "key", "series"):
                if k not in p:
                    from analysis.base import PlotValidationError
                    raise PlotValidationError(
                        f"{self.name}: panels[{i}] missing required key '{k}'")
            for j, s in enumerate(p["series"]):
                for k in ("label", "time", "value"):
                    if k not in s:
                        from analysis.base import PlotValidationError
                        raise PlotValidationError(
                            f"{self.name}: panels[{i}].series[{j}] missing '{k}'")

    def render(self, data: Mapping[str, Any], config: Dict[str, Any]):
        import math as _math
        paths = []
        for panel in data["panels"]:
            key, title = panel["key"], panel["title"]
            fig, ax = plt.subplots(figsize=tuple(config.get("figsize", (8.5, 5.0))))
            last_y = None
            for s in panel["series"]:
                t = np.asarray(s["time"], dtype=float)
                y = np.asarray(s["value"], dtype=float)
                ax.plot(t, y, marker="o", lw=1.6, ms=3, label=str(s["label"]))
                last_y = y
            ax.set_title(title)
            ax.set_xlabel("Time [code units]")
            ax.set_ylabel(key)
            thresholds = {
                "ca_r5": (0.75, "provisional guide < 0.75"),
                "z_rms_over_R_rms_r5": (0.55, "provisional guide < 0.55"),
                "vrot_over_sigma_r5": (0.15, "provisional guide > 0.15"),
            }
            if key in thresholds:
                threshold, note = thresholds[key]
                ax.axhline(threshold, color="0.25", ls="--", lw=1.1)
                ax.text(0.99, threshold, note, transform=ax.get_yaxis_transform(),
                        ha="right", va="bottom", fontsize=7, color="0.25",
                        bbox=dict(facecolor="white", alpha=0.75,
                                  edgecolor="none", pad=1.5))
                all_values = np.concatenate([
                    np.asarray(s["value"], dtype=float) for s in panel["series"]])
                finite = all_values[np.isfinite(all_values)]
                default_top = 0.45 if key == "vrot_over_sigma_r5" else 1.05
                ymax = max(default_top,
                           float(np.max(finite)) * 1.05 if finite.size else 0.0)
                ax.set_ylim(0.0, ymax)
            if key in {"ninteractions_total", "rho_core_r2"} and last_y is not None \
                    and any(_math.isfinite(v) and v > 0 for v in np.ravel(last_y)):
                ax.set_yscale("log")
            ax.grid(True, alpha=0.3)
            ax.legend(frameon=False, fontsize=7.5, loc="upper left",
                      bbox_to_anchor=(1.02, 1.0), borderaxespad=0.0)
            fig.subplots_adjust(left=0.11, right=0.73, top=0.90, bottom=0.12)
            fname = str(config.get("filename", "shape_panel_{key}.png")).format(key=key)
            paths.append(self.settings.save_figure(fig, fname, dpi=config.get("dpi")))
            plt.close(fig)
        return paths

@register
class ContactSheetPlot(BasePlot):
    name = "contact_sheet"
    block = "prerun"
    summary = "Contact-sheet серии: face-on/edge-on кадры по снапшотам"
    data_source = "prepare_series_frames"
    inputs = ("run",)
    runner = "runners/make_prerun_plots.py"
    description = (
        "Contact-sheet analyze_series.py: сетка кадров downsample-частиц "
        "(face-on x-y или edge-on x-z, LogNorm, лимит по 98-му перцентилю) "
        "с подписью номера снапшота. Два вызова — faceon и edgeon."
    )
    data_contract = {
        "frames": F(("F",), dtype="any"),
        "plane": F((), dtype="str", required=False),
    }
    default_config = {
        "title": "Contact sheet",
        "plane": "xy",
        "bins": 160,
        "percentile": 98,
        "min_lim": 2.0,
        "cmap": "inferno",
        "dpi": 150,
        "filename": "contact_{plane}.png",
    }

    def validate_data(self, data):
        frames = data.get("frames")
        if not isinstance(frames, (list, tuple)) or not frames:
            from analysis.base import PlotValidationError
            raise PlotValidationError(
                f"{self.name}: data['frames'] must be a non-empty list")
        for i, fr in enumerate(frames):
            for k in ("xy", "xz", "snapshot"):
                if k not in fr:
                    from analysis.base import PlotValidationError
                    raise PlotValidationError(
                        f"{self.name}: frames[{i}] missing required key '{k}'")

    def render(self, data: Mapping[str, Any], config: Dict[str, Any]):
        plane = str(config.get("plane",
                               data.get("plane", "xy")) or "xy").lower()
        key = "xy" if plane.startswith("xy") else "xz"
        frames = list(data["frames"])
        n = len(frames)
        ncols = int(np.ceil(np.sqrt(n)))
        nrows = int(np.ceil(n / ncols))
        all_pts = np.vstack([np.asarray(fr[key], dtype=float) for fr in frames])
        rr = np.linalg.norm(all_pts, axis=1)
        lim = max(float(np.percentile(rr[rr > 0], config.get("percentile", 98))),
                  float(config.get("min_lim", 2.0)))
        fig, axes = plt.subplots(nrows, ncols,
                                 figsize=(3.2 * ncols, 3.0 * nrows),
                                 squeeze=False)
        for i, ax in enumerate(axes.flat):
            if i >= n:
                ax.axis("off")
                continue
            pts = np.asarray(frames[i][key], dtype=float)
            ax.hist2d(pts[:, 0], pts[:, 1], bins=int(config.get("bins", 160)),
                      range=[[-lim, lim], [-lim, lim]],
                      norm=LogNorm(), cmap=config.get("cmap", "inferno"))
            ax.set_xlim(-lim, lim)
            ax.set_ylim(-lim, lim)
            ax.set_aspect("equal")
            ax.set_title(f"snap {frames[i]['snapshot']}", fontsize=9)
            ax.set_xticks([])
            ax.set_yticks([])
        fig.suptitle(f"{config.get('title', '')} ({key})")
        fig.tight_layout()
        fname = str(config.get("filename", "contact_{plane}.png")).format(plane=key)
        path = self.settings.save_figure(fig, fname, dpi=config.get("dpi"))
        plt.close(fig)
        return path
