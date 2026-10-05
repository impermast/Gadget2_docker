#!/usr/bin/env python3
"""plots/core — переезд из plot_scripts (математика дословно, см. этап 1).
Профили одного прогона (блок core реестра).
"""
from __future__ import annotations

from typing import Any, Dict, Mapping, Optional

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from analysis.base import (
    BasePlot,
    FieldSpec as F,
    PlotValidationError,
    format_contract,
    validate_fields,
)
from analysis.registry import register

from analysis.style import resolve_xlim, shade_unresolved

@register
class DensityPlot(BasePlot):
    name = "density"
    block = "core"
    summary = "Профиль плотности rho(r) одного прогона (unresolved-зона заштрихована)"
    data_source = "prepare_profile_data"
    inputs = ('run',)
    description = (
        "Radial density profile rho(r) финального halo. Обычно строится по ОДНОМУ "
        "Gadget HDF5 snapshot (PartType3/Coordinates + Masses; центрирование "
        "shrinkage). В render() передаётся уже рассчитанный профиль (r, rho) — "
        "подготовка через loaders.prepare_profile_data()."
    )
    data_contract = {
        "r": F(("R",)),
        "rho": F(("R",)),
        "time": F((), required=False),
        "cross_section": F((), required=False),
        "unresolved_r_max": F((), required=False),
    }
    default_config = {
        "title": "Radial density profile",
        "xlabel": "r [kpc]",
        "ylabel": r"$\rho(r)$",
        "xscale": "log",
        "yscale": "log",
        "xlim": None,
        "ylim": None,
        "unresolved_r_max": None,
        "unresolved_label": "below resolution",
        "color_index": 0,
        "line_width": None,
        "figsize_key": "page",
        "dpi": None,
        "filename": "01_density_profile.png",
    }

    def render(self, data: Mapping[str, Any], config: Dict[str, Any]):
        from analysis.style import resolve_xlim, shade_unresolved

        rmax = config.get("unresolved_r_max", None)
        if rmax is None:
            rmax = data.get("unresolved_r_max", None)
        fig, ax = plt.subplots(figsize=self.settings.figsize(config["figsize_key"]))
        ax.plot(data["r"], data["rho"],
                color=self.settings.palette[config["color_index"]],
                lw=config.get("line_width") or self.settings.line_width_main)
        shade_unresolved(ax, rmax, label=config.get("unresolved_label") or None)
        self.settings.style_axis(
            ax, title=config.get("title"), xlabel=config.get("xlabel"),
            ylabel=config.get("ylabel"), xscale=config.get("xscale"),
            yscale=config.get("yscale"),
            xlim=resolve_xlim(config.get("xlim"), rmax),
            ylim=config.get("ylim"), grid=True)
        fig.tight_layout()
        path = self.settings.save_figure(fig, config["filename"],
                                         dpi=config.get("dpi"))
        plt.close(fig)
        return path




@register
class LogSlopePlot(BasePlot):
    name = "log_slope"
    block = "core"
    summary = "Локальный наклон dlnrho/dlnr одного прогона, опора NFW -1"
    data_source = "prepare_profile_data"
    inputs = ('run',)
    description = (
        "Локальный наклон d log rho / d log r по радиусу (ядро vs cusp). Один HDF5 "
        "snapshot; slope считается на этапе подготовки данных (loaders), окно "
        "0.25 dex, минимум 3 бина. Опорная линия -1 (NFW) рисуется автоматически."
    )
    data_contract = {
        "r": F(("R",)),
        "slope": F(("R",)),
        "unresolved_r_max": F((), required=False),
    }
    default_config = {
        "title": None,
        "xlabel": "r [kpc]",
        "ylabel": r"$d\log\rho/d\log r$",
        "xscale": "log",
        "yscale": "linear",
        "xlim": None,
        "ylim": (-3.5, -0.4),
        "unresolved_r_max": None,
        "unresolved_label": "below resolution",
        "reference_line": -1.0,
        "color_index": 1,
        "line_width": None,
        "figsize_key": "page",
        "dpi": None,
        "filename": "02_log_slope.png",
    }

    def render(self, data: Mapping[str, Any], config: Dict[str, Any]):
        from analysis.style import resolve_xlim, shade_unresolved

        rmax = config.get("unresolved_r_max", None)
        if rmax is None:
            rmax = data.get("unresolved_r_max", None)
        fig, ax = plt.subplots(figsize=self.settings.figsize(config["figsize_key"]))
        ax.plot(data["r"], data["slope"],
                color=self.settings.palette[config["color_index"]],
                lw=config.get("line_width") or self.settings.line_width_main)
        ref = config.get("reference_line")
        if ref is not None:
            ax.axhline(ref, ls=":", color="0.4", lw=0.8)
        shade_unresolved(ax, rmax, label=config.get("unresolved_label") or None)
        self.settings.style_axis(
            ax, title=config.get("title"), xlabel=config.get("xlabel"),
            ylabel=config.get("ylabel"), xscale=config.get("xscale"),
            yscale=config.get("yscale"),
            xlim=resolve_xlim(config.get("xlim"), rmax),
            ylim=config.get("ylim"), grid=True)
        fig.tight_layout()
        path = self.settings.save_figure(fig, config["filename"],
                                         dpi=config.get("dpi"))
        plt.close(fig)
        return path




@register
class SigmaVPlot(BasePlot):
    name = "sigma_v"
    block = "core"
    summary = "Профиль дисперсии скоростей sigma_v(r) одного прогона"
    data_source = "prepare_profile_data"
    inputs = ('run',)
    description = (
        "Профиль 1D velocity dispersion sigma_1D(r). Один HDF5 snapshot; "
        "считается по PartType3/Velocities в радиальных бинах на этапе "
        "подготовки данных (loaders)."
    )
    data_contract = {
        "r": F(("R",)),
        "sigma_v": F(("R",)),
        "unresolved_r_max": F((), required=False),
    }
    default_config = {
        "title": "1D velocity dispersion profile",
        "xlabel": "r [kpc]",
        "ylabel": r"$\sigma_{1D}(r)$ [km/s]",
        "xscale": "log",
        "yscale": "linear",
        "xlim": None,
        "ylim": None,
        "unresolved_r_max": None,
        "unresolved_label": "below resolution",
        "color_index": 0,
        "line_width": None,
        "figsize_key": "page",
        "dpi": None,
        "filename": "03_sigma_v.png",
    }

    def render(self, data: Mapping[str, Any], config: Dict[str, Any]):
        from analysis.style import resolve_xlim, shade_unresolved

        import matplotlib.pyplot as plt

        rmax = config.get("unresolved_r_max", None)
        if rmax is None:
            rmax = data.get("unresolved_r_max", None)
        fig, ax = plt.subplots(figsize=self.settings.figsize(config["figsize_key"]))
        ax.plot(data["r"], data["sigma_v"],
                color=self.settings.palette[config["color_index"]],
                lw=config.get("line_width") or self.settings.line_width_main)
        shade_unresolved(ax, rmax, label=config.get("unresolved_label") or None)
        self.settings.style_axis(
            ax, title=config.get("title"), xlabel=config.get("xlabel"),
            ylabel=config.get("ylabel"), xscale=config.get("xscale"),
            yscale=config.get("yscale"),
            xlim=resolve_xlim(config.get("xlim"), rmax),
            ylim=config.get("ylim"), grid=True)
        fig.tight_layout()
        path = self.settings.save_figure(fig, config["filename"],
                                         dpi=config.get("dpi"))
        plt.close(fig)
        return path




@register
class InteractionsRadialPlot(BasePlot):
    name = "interactions_radial"
    block = "core"
    summary = "Радиальный профиль NInteractions (только SIDM; у CDM пусто)"
    data_source = "prepare_profile_data"
    inputs = ('run',)
    description = (
        "Радиальный профиль SIDM-взаимодействий: mean NInteractions(r) и процент "
        "частиц, взаимодействовавших хотя бы раз. Один HDF5 snapshot с dataset "
        "PartType3/NInteractions (пишется при DM_SIDM-конфиге с патчем "
        "NInteractions). Две панели на одной фигуре."
    )
    data_contract = {
        "r_ni": F(("B",)),
        "ni_mean": F(("B",)),
        "ni_frac": F(("B",)),
        "unresolved_r_max": F((), required=False),
    }
    default_config = {
        "mean_ylabel": "mean NInteractions",
        "frac_ylabel": "% particles interacted",
        "xlabel": "r [kpc]",
        "xscale": "log",
        "mean_yscale": "log",
        "frac_yscale": "linear",
        "xlim": None,
        "mean_ylim": None,
        "frac_ylim": (0.0, 105.0),
        "unresolved_r_max": None,
        "unresolved_label": "below resolution",
        "figsize": (11.0, 4.2),
        "dpi": 200,
        "filename": "04_ninteractions_radial.png",
    }

    def render(self, data: Mapping[str, Any], config: Dict[str, Any]):
        import numpy as np

        from analysis.style import resolve_xlim, shade_unresolved

        r = np.asarray(data["r_ni"])
        ni_mean = np.asarray(data["ni_mean"], dtype=float)
        ni_frac = np.asarray(data["ni_frac"], dtype=float)
        rmax = config.get("unresolved_r_max", None)
        if rmax is None:
            rmax = data.get("unresolved_r_max", None)
        xlim = resolve_xlim(config.get("xlim"), rmax)
        label = config.get("unresolved_label") or None

        fig, axs = plt.subplots(1, 2, figsize=tuple(config["figsize"]))
        m = np.isfinite(ni_mean) & (ni_mean > 0)
        if m.any():
            axs[0].plot(r[m], ni_mean[m],
                        color=self.settings.palette[0],
                        lw=self.settings.line_width_main)
        shade_unresolved(axs[0], rmax, label=label)
        self.settings.style_axis(axs[0], xlabel=config["xlabel"],
                                 ylabel=config["mean_ylabel"],
                                 xscale=config["xscale"],
                                 yscale=config["mean_yscale"],
                                 xlim=xlim,
                                 ylim=config.get("mean_ylim"), grid=True)

        f = np.isfinite(ni_frac) & (ni_frac > 0)
        if f.any():
            axs[1].plot(r[f], ni_frac[f],
                        color=self.settings.palette[1],
                        lw=self.settings.line_width_main)
        shade_unresolved(axs[1], rmax, label=None)
        self.settings.style_axis(axs[1], xlabel=config["xlabel"],
                                 ylabel=config["frac_ylabel"],
                                 xscale=config["xscale"],
                                 yscale=config["frac_yscale"],
                                 xlim=xlim,
                                 ylim=config.get("frac_ylim"), grid=True)

        fig.tight_layout()
        path = self.settings.save_figure(fig, config["filename"], dpi=config["dpi"])
        plt.close(fig)
        return path




@register
class DiskEdgeOnPlot(BasePlot):
    name = "disk_edgeon"
    block = "core"
    summary = "Проекция плотности edge-on одного прогона"
    data_source = "prepare_particle_snapshot"
    inputs = ('run',)
    description = (
        "Edge-on карта поверхностной плотности (x-z проекция) финального "
        "снапшота — главный график для демонстрации формирования диска: "
        "сплюснутая структура в x-y-плоскости видна как горизонтальная полоса. "
        "Данные: particles из prepare_particle_snapshot() (positions уже "
        "shrinkage-центрированы)."
    )
    data_contract = {
        "positions": F(("N", 3)),
        "masses": F(("N",), required=False),
        "time": F((), required=False),
        "cross_section": F((), required=False),
    }
    default_config = {
        "title": None,
        "xlabel": "x [kpc]",
        "ylabel": "z [kpc]",
        "bins": 220,
        "lim": None,
        "min_lim": 2.0,
        "percentile": 98,
        "cmap": "inferno",
        "dpi": 150,
        "figsize_key": "square",
        "filename": "disk_edgeon.png",
    }

    def render(self, data, config):
        from matplotlib.colors import LogNorm

        pos = np.asarray(data["positions"], dtype=np.float64)
        masses = data.get("masses")
        w = (np.asarray(masses, dtype=np.float64)
             if masses is not None else np.ones(len(pos)))

        lim = config.get("lim")
        if lim is None:
            r = np.linalg.norm(pos[:, :2], axis=1)  # x-y радиус
            lim = max(float(np.percentile(r[r > 0], config["percentile"])),
                      float(config["min_lim"]))

        fig, ax = plt.subplots(figsize=self.settings.figsize(config["figsize_key"]))
        hh = ax.hist2d(pos[:, 0], pos[:, 2], bins=config["bins"],
                       range=[[-lim, lim], [-lim, lim]],
                       weights=w, norm=LogNorm(), cmap=config["cmap"])
        ax.set_aspect("equal")
        self.settings.style_axis(ax, title=config.get("title"),
                                 xlabel=config.get("xlabel"),
                                 ylabel=config.get("ylabel"))
        cb = fig.colorbar(hh[3], ax=ax, fraction=0.046)
        cb.set_label("mass per pixel")
        fig.tight_layout()
        path = self.settings.save_figure(fig, config["filename"],
                                         dpi=config["dpi"])
        plt.close(fig)
        return path


ANALYSIS_PLOT_CLASSES = [DensityPlot, LogSlopePlot, SigmaVPlot, InteractionsRadialPlot,
                         DiskEdgeOnPlot]


# ═══════════════════════ multi-run comparison plots ═════════════════════════

def _validate_series_list(plot_name, data, inner_contract, min_series=1):
    """
    Валидация данных compare-plots: data["series"] — список dict'ов, каждый
    соответствует inner_contract. Ошибка называет plot, индекс серии и поле.
    """
    if not isinstance(data, Mapping) or "series" not in data:
        raise PlotValidationError(
            f"{plot_name}: data must be a mapping with required key 'series' "
            f"(list of per-run dicts)")
    series = data["series"]
    if not isinstance(series, (list, tuple)) or len(series) < min_series:
        raise PlotValidationError(
            f"{plot_name}: 'series' must be a list of at least {min_series} "
            f"per-run dicts, got {type(series).__name__}")
    for i, item in enumerate(series):
        if not isinstance(item, Mapping):
            raise PlotValidationError(
                f"{plot_name}: series[{i}] must be a dict, got {type(item).__name__}")
        try:
            validate_fields(f"{plot_name}.series[{i}]", item, inner_contract)
        except PlotValidationError as e:
            raise PlotValidationError(str(e)) from e


def _series_list_contract() -> dict:
    """Внешний контракт compare-plots: 'series' — список per-run dict'ов."""
    return {"series": F(("S",), dtype="any")}


def _series_unresolved_r(series, config) -> Optional[float]:
    """Максимальный unresolved_r_max по сериям (или значение из config)."""
    if config.get("unresolved_r_max") is not None:
        return float(config["unresolved_r_max"])
    vals = [float(s["unresolved_r_max"]) for s in series
            if isinstance(s, Mapping) and s.get("unresolved_r_max")]
    return max(vals) if vals else None
