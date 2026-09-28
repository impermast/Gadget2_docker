#!/usr/bin/env python3
"""
analysis_plots.py — стандартные статические analysis-графики одного run.

Все plots получают УЖЕ рассчитанные radial-профили (см. loaders.py).
Математика подготовки данных не менялась: профили считаются ровно как в
analyze_final_snapshot.py (shrinkage centering, лог-биннинг, slope-окно
0.25 dex, порог >=3 бинов / >=5 частиц).
"""

from __future__ import annotations

from typing import Any, Dict, Mapping

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.colors import LogNorm, TwoSlopeNorm

from base import BasePlot, F, PlotValidationError, validate_fields


# ──────────────────────────── общие helpers ─────────────────────────────────

def _line_plot(settings, data_x, data_y, cfg):
    """Обычная однолинейная отрисовка в глобальном стиле проекта."""
    fig, ax = plt.subplots(figsize=settings.figsize(cfg["figsize_key"]))
    ax.plot(data_x, data_y,
            color=settings.palette[cfg["color_index"]],
            lw=cfg.get("line_width") or settings.line_width_main)
    settings.style_axis(
        ax,
        title=cfg.get("title"),
        xlabel=cfg.get("xlabel"),
        ylabel=cfg.get("ylabel"),
        xscale=cfg.get("xscale"),
        yscale=cfg.get("yscale"),
        xlim=cfg.get("xlim"),
        ylim=cfg.get("ylim"),
        grid=True,
    )
    fig.tight_layout()
    path = settings.save_figure(fig, cfg["filename"], dpi=cfg.get("dpi"))
    plt.close(fig)
    return path


# ───────────────────────────── concrete plots ───────────────────────────────

class DensityPlot(BasePlot):
    name = "density"
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
    }
    default_config = {
        "title": "Radial density profile",
        "xlabel": "r [kpc]",
        "ylabel": r"$\rho(r)$",
        "xscale": "log",
        "yscale": "log",
        "xlim": None,
        "ylim": None,
        "color_index": 0,
        "line_width": None,
        "figsize_key": "page",
        "dpi": None,
        "filename": "01_density_profile.png",
    }

    def render(self, data: Mapping[str, Any], config: Dict[str, Any]):
        return _line_plot(self.settings, data["r"], data["rho"], config)


class LogSlopePlot(BasePlot):
    name = "log_slope"
    description = (
        "Локальный наклон d log rho / d log r по радиусу (ядро vs cusp). Один HDF5 "
        "snapshot; slope считается на этапе подготовки данных (loaders), окно "
        "0.25 dex, минимум 3 бина. Опорная линия -1 (NFW) рисуется автоматически."
    )
    data_contract = {
        "r": F(("R",)),
        "slope": F(("R",)),
    }
    default_config = {
        "title": None,
        "xlabel": "r [kpc]",
        "ylabel": r"$d\log\rho/d\log r$",
        "xscale": "log",
        "yscale": "linear",
        "xlim": None,
        "ylim": (-3.5, -0.4),
        "reference_line": -1.0,
        "color_index": 1,
        "line_width": None,
        "figsize_key": "page",
        "dpi": None,
        "filename": "02_log_slope.png",
    }

    def render(self, data: Mapping[str, Any], config: Dict[str, Any]):
        fig, ax = plt.subplots(figsize=self.settings.figsize(config["figsize_key"]))
        ax.plot(data["r"], data["slope"],
                color=self.settings.palette[config["color_index"]],
                lw=config.get("line_width") or self.settings.line_width_main)
        ref = config.get("reference_line")
        if ref is not None:
            ax.axhline(ref, ls=":", color="0.4", lw=0.8)
        self.settings.style_axis(
            ax, title=config.get("title"), xlabel=config.get("xlabel"),
            ylabel=config.get("ylabel"), xscale=config.get("xscale"),
            yscale=config.get("yscale"), xlim=config.get("xlim"),
            ylim=config.get("ylim"), grid=True)
        fig.tight_layout()
        path = self.settings.save_figure(fig, config["filename"],
                                         dpi=config.get("dpi"))
        plt.close(fig)
        return path


class SigmaVPlot(BasePlot):
    name = "sigma_v"
    description = (
        "Профиль 1D velocity dispersion sigma_1D(r). Один HDF5 snapshot; "
        "считается по PartType3/Velocities в радиальных бинах на этапе "
        "подготовки данных (loaders)."
    )
    data_contract = {
        "r": F(("R",)),
        "sigma_v": F(("R",)),
    }
    default_config = {
        "title": "1D velocity dispersion profile",
        "xlabel": "r [kpc]",
        "ylabel": r"$\sigma_{1D}(r)$ [km/s]",
        "xscale": "log",
        "yscale": "linear",
        "xlim": None,
        "ylim": None,
        "color_index": 0,
        "line_width": None,
        "figsize_key": "page",
        "dpi": None,
        "filename": "03_sigma_v.png",
    }

    def render(self, data: Mapping[str, Any], config: Dict[str, Any]):
        return _line_plot(self.settings, data["r"], data["sigma_v"], config)


class InteractionsRadialPlot(BasePlot):
    name = "interactions_radial"
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
        "figsize": (11.0, 4.2),
        "dpi": 200,
        "filename": "04_ninteractions_radial.png",
    }

    def render(self, data: Mapping[str, Any], config: Dict[str, Any]):
        import numpy as np

        r = np.asarray(data["r_ni"])
        ni_mean = np.asarray(data["ni_mean"], dtype=float)
        ni_frac = np.asarray(data["ni_frac"], dtype=float)

        fig, axs = plt.subplots(1, 2, figsize=tuple(config["figsize"]))
        m = np.isfinite(ni_mean) & (ni_mean > 0)
        if m.any():
            axs[0].plot(r[m], ni_mean[m],
                        color=self.settings.palette[0],
                        lw=self.settings.line_width_main)
        self.settings.style_axis(axs[0], xlabel=config["xlabel"],
                                 ylabel=config["mean_ylabel"],
                                 xscale=config["xscale"],
                                 yscale=config["mean_yscale"],
                                 xlim=config.get("xlim"),
                                 ylim=config.get("mean_ylim"), grid=True)

        f = np.isfinite(ni_frac) & (ni_frac > 0)
        if f.any():
            axs[1].plot(r[f], ni_frac[f],
                        color=self.settings.palette[1],
                        lw=self.settings.line_width_main)
        self.settings.style_axis(axs[1], xlabel=config["xlabel"],
                                 ylabel=config["frac_ylabel"],
                                 xscale=config["xscale"],
                                 yscale=config["frac_yscale"],
                                 xlim=config.get("xlim"),
                                 ylim=config.get("frac_ylim"), grid=True)

        fig.tight_layout()
        path = self.settings.save_figure(fig, config["filename"], dpi=config["dpi"])
        plt.close(fig)
        return path


class DiskEdgeOnPlot(BasePlot):
    name = "disk_edgeon"
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


class _MultiSeriesPlot(BasePlot):
    """
    Общая логика отрисовки нескольких серий на одних осях. Это НЕ уровень
    иерархии plot'ов — только shared helper-код; все compare-plots остаются
    самостоятельными concrete plots с собственными контрактами.
    """

    inner_contract: dict = {}

    def validate_data(self, data):
        _validate_series_list(self.name, data, self.inner_contract)

    def _render_series(self, data, config, y_field):
        import numpy as np

        fig, ax = plt.subplots(figsize=self.settings.figsize(config["figsize_key"]))
        for i, s in enumerate(data["series"]):
            label = str(s.get("label", f"series_{i}"))
            ax.plot(np.asarray(s["r"]), np.asarray(s[y_field]),
                    color=self.settings.palette[i % len(self.settings.palette)],
                    lw=self.settings.line_width_main, label=label)
        self.settings.style_axis(
            ax, title=config.get("title"), xlabel=config.get("xlabel"),
            ylabel=config.get("ylabel"), xscale=config.get("xscale"),
            yscale=config.get("yscale"), xlim=config.get("xlim"),
            ylim=config.get("ylim"), grid=True, legend=True)
        fig.tight_layout()
        path = self.settings.save_figure(fig, config["filename"],
                                         dpi=config.get("dpi"))
        plt.close(fig)
        return path


class DensityComparePlot(_MultiSeriesPlot):
    name = "density_compare"
    description = (
        "Сравнение radial density profiles нескольких прогонов (CDM vs SIDM и "
        "т.п.) на одних осях. Данные — список серий из prepare_profile_data() "
        "каждого run; label задаёт подпись легенды."
    )
    inner_contract = {"r": F(("R",)), "rho": F(("R",)),
                      "label": F((), dtype="str", required=False)}
    data_contract = _series_list_contract()
    default_config = {
        "title": "Radial density profiles",
        "xlabel": "r [kpc]",
        "ylabel": r"$\rho(r)$",
        "xscale": "log",
        "yscale": "log",
        "xlim": None,
        "ylim": None,
        "figsize_key": "page",
        "dpi": None,
        "filename": "density_compare.png",
    }

    def render(self, data, config):
        return self._render_series(data, config, "rho")


class LogSlopeComparePlot(_MultiSeriesPlot):
    name = "log_slope_compare"
    description = (
        "Сравнение локальных наклонов d log rho / d log r нескольких прогонов. "
        "Список серий из prepare_profile_data() (r, slope, label)."
    )
    inner_contract = {"r": F(("R",)), "slope": F(("R",)),
                      "label": F((), dtype="str", required=False)}
    data_contract = _series_list_contract()
    default_config = {
        "title": None,
        "xlabel": "r [kpc]",
        "ylabel": r"$d\log\rho/d\log r$",
        "xscale": "log",
        "yscale": "linear",
        "xlim": None,
        "ylim": (-3.5, -0.4),
        "figsize_key": "page",
        "dpi": None,
        "filename": "log_slope_compare.png",
    }

    def render(self, data, config):
        return self._render_series(data, config, "slope")


class SigmaVComparePlot(_MultiSeriesPlot):
    name = "sigma_v_compare"
    description = (
        "Сравнение профилей 1D velocity dispersion нескольких прогонов. "
        "Список серий из prepare_profile_data() (r, sigma_v, label)."
    )
    inner_contract = {"r": F(("R",)), "sigma_v": F(("R",)),
                      "label": F((), dtype="str", required=False)}
    data_contract = _series_list_contract()
    default_config = {
        "title": "1D velocity dispersion profiles",
        "xlabel": "r [kpc]",
        "ylabel": r"$\sigma_{1D}(r)$ [km/s]",
        "xscale": "log",
        "yscale": "linear",
        "xlim": None,
        "ylim": None,
        "figsize_key": "page",
        "dpi": None,
        "filename": "sigma_v_compare.png",
    }

    def render(self, data, config):
        return self._render_series(data, config, "sigma_v")


class _DeltaComparePlot(BasePlot):
    """
    Compare-график с нижним сабплотом разностей Δ относительно базовой серии
    (по умолчанию первая, обычно CDM; либо config['baseline_label']).
    Верхний сабплот — значения, нижний — Δ (для log-шкалы в dex).
    Общая ось X = r. Shared helper: НЕ уровень иерархии,
    конкретные plots остаются самостоятельными (BasePlot -> Concrete).
    """

    value_field: str = ""
    diff_in_log: bool = False   # True: низ = log10(y) - log10(base)

    def validate_data(self, data):
        contract = dict(self.inner_contract)
        contract[self.value_field] = F(("R",))
        _validate_series_list(self.name, data, contract)

    def _render_delta(self, data, config):
        import numpy as np

        series = data["series"]
        baseline_label = config.get("baseline_label")
        base_idx = 0
        if baseline_label is not None:
            for i, s in enumerate(series):
                if s.get("label") == baseline_label:
                    base_idx = i
                    break

        base = series[base_idx]
        ref_r = np.asarray(base["r"], dtype=float)
        base_y = np.asarray(base[self.value_field], dtype=float)
        grid = (ref_r > 0) & np.isfinite(base_y)
        log_ref = np.log10(ref_r)

        fig, (ax_top, ax_diff) = plt.subplots(
            2, 1, sharex=True,
            figsize=self.settings.figsize(config["figsize_key"]))

        for i, s in enumerate(series):
            r_s = np.asarray(s["r"], dtype=float)
            y_s = np.asarray(s[self.value_field], dtype=float)
            label = str(s.get("label", f"series_{i}"))
            sel = (r_s > 0) & np.isfinite(y_s)
            if not np.any(sel):
                continue
            y_grid = np.interp(log_ref[grid], np.log10(r_s[sel]),
                               y_s[sel], left=np.nan, right=np.nan)
            color = self.settings.palette[i % len(self.settings.palette)]
            if self.diff_in_log:
                y_plot = np.where(y_grid > 0, y_grid, np.nan)
                ax_top.plot(ref_r[grid], y_plot, color=color,
                            lw=self.settings.line_width_main, label=label)
                delta = np.log10(y_plot) - np.log10(base_y[grid])
            else:
                y_plot = y_grid
                ax_top.plot(ref_r[grid], y_plot, color=color,
                            lw=self.settings.line_width_main, label=label)
                delta = y_grid - base_y[grid]
            if i != base_idx:
                ax_diff.plot(ref_r[grid], delta, color=color,
                             lw=self.settings.line_width, label=label)

        ax_diff.axhline(0.0, ls=":", color="0.4", lw=0.9)
        self.settings.style_axis(
            ax_top, title=config.get("title"),
            ylabel=config.get("top_ylabel"),
            yscale=config.get("top_yscale"), grid=True)
        self.settings.style_axis(
            ax_diff, xlabel=config.get("xlabel"),
            ylabel=config.get("diff_ylabel"),
            xscale=config.get("xscale"), grid=True)
        if config.get("legend"):
            ax_top.legend(frameon=False,
                          fontsize=self.settings.legend_font_size)
        fig.tight_layout()
        path = self.settings.save_figure(fig, config["filename"],
                                         dpi=config.get("dpi"))
        plt.close(fig)
        return path


class LogRhoComparePlot(_DeltaComparePlot):
    name = "log_rho_compare"
    description = (
        "Сравнение radial density profiles (log rho vs r) нескольких прогонов "
        "с нижним сабплотом разностей Δlog10(rho) относительно CDM. "
        "Серии из prepare_profile_data() (r, rho, label); базовый CDM — "
        "первая серия либо config['baseline_label']."
    )
    value_field = "rho"
    diff_in_log = True
    inner_contract = {"r": F(("R",)), "rho": F(("R",)),
                      "label": F((), dtype="str", required=False)}
    data_contract = _series_list_contract()
    default_config = {
        "title": "Log density profiles: CDM vs SIDM",
        "top_ylabel": r"$\rho(r)$",
        "diff_ylabel": r"$\Delta\log_{10}\rho$ vs CDM",
        "xlabel": "r [kpc]",
        "xscale": "log",
        "top_yscale": "log",
        "legend": True,
        "baseline_label": None,
        "figsize_key": "page_tall",
        "dpi": None,
        "filename": "log_rho_compare.png",
    }

    def render(self, data, config):
        return self._render_delta(data, config)


class RotCurveComparePlot(_DeltaComparePlot):
    name = "rot_curve_compare"
    description = (
        "Кривые вращения v_circ(r) нескольких прогонов (v_circ из "
        "prepare_profile_data, sqrt(G M(<r)/r)) с нижним сабплотом разностей "
        "Δv = v_sigma - v_CDM. Общая ось X = r."
    )
    value_field = "v_circ"
    diff_in_log = False
    inner_contract = {"r": F(("R",)), "v_circ": F(("R",)),
                      "label": F((), dtype="str", required=False)}
    data_contract = _series_list_contract()
    default_config = {
        "title": "Rotation curves: CDM vs SIDM",
        "top_ylabel": r"$v_{\rm circ}(r)$ [km/s]",
        "diff_ylabel": r"$\Delta v_{\rm circ}$ [km/s]",
        "xlabel": "r [kpc]",
        "xscale": "log",
        "top_yscale": "linear",
        "legend": True,
        "baseline_label": None,
        "figsize_key": "page_tall",
        "dpi": None,
        "filename": "rot_curve_compare.png",
    }

    def render(self, data, config):
        return self._render_delta(data, config)


class CoreDensityVsSigmaPlot(BasePlot):
    name = "core_density_vs_sigma"
    description = (
        "Core density (в фиксированном радиусе) как функция SIDM cross-section "
        "по нескольким прогонам. Данные готовит compare_runs.py: sigma из "
        "заголовков снапшотов, rho_core из prepare_profile_data()."
    )
    data_contract = {
        "sigma": F(("S",)),
        "rho_core": F(("S",)),
        "labels": F(("S",), dtype="str", required=False),
    }
    default_config = {
        "title": "Core density vs SIDM cross-section",
        "xlabel": r"$\sigma_{\rm SIDM}$ [cm$^2$/g]",
        "ylabel": r"$\rho_{\rm core}$",
        "xscale": "log",
        "yscale": "log",
        "xlim": None,
        "ylim": None,
        "marker": "o",
        "figsize_key": "page",
        "dpi": None,
        "filename": "core_density_vs_sigma.png",
    }

    def render(self, data, config):
        import numpy as np

        sigma = np.asarray(data["sigma"], dtype=float)
        rho_core = np.asarray(data["rho_core"], dtype=float)
        fig, ax = plt.subplots(figsize=self.settings.figsize(config["figsize_key"]))
        ax.plot(sigma, rho_core, config["marker"],
                color=self.settings.palette[0],
                ms=self.settings.marker_size + 2,
                lw=self.settings.line_width_main)
        labels = data.get("labels")
        if labels is not None:
            for x, y, lab in zip(sigma, rho_core, labels):
                ax.annotate(str(lab), (x, y), textcoords="offset points",
                            xytext=(6, 4), fontsize=self.settings.font_size)
        self.settings.style_axis(
            ax, title=config.get("title"), xlabel=config.get("xlabel"),
            ylabel=config.get("ylabel"), xscale=config.get("xscale"),
            yscale=config.get("yscale"), xlim=config.get("xlim"),
            ylim=config.get("ylim"), grid=True)
        fig.tight_layout()
        path = self.settings.save_figure(fig, config["filename"],
                                         dpi=config.get("dpi"))
        plt.close(fig)
        return path


class VisualMorphologyMontagePlot(BasePlot):
    name = "visual_morphology_montage"
    description = (
        "Presentation-quality face-on/edge-on surface-density montage for a run "
        "group. Data are precomputed projection histograms; render() never reads HDF5."
    )
    data_contract = {"labels": F(("S",), dtype="str"), "faceon": F(("S", "B", "B")), "edgeon": F(("S", "B", "B")), "times": F(("S",), required=False)}
    default_config = {"title": "Projected dark-matter morphology", "lim": 12.0, "cmap": "magma", "floor": 1e-12, "dpi": 190, "filename": "01_surface_density_montage_final.png"}

    def render(self, data, config):
        labels = list(data["labels"])
        face = np.asarray(data["faceon"], dtype=float)
        edge = np.asarray(data["edgeon"], dtype=float)
        times = np.asarray(data.get("times", np.full(len(labels), np.nan)), dtype=float)
        vals = np.concatenate([face.ravel(), edge.ravel()])
        pos = vals[np.isfinite(vals) & (vals > 0)]
        vmin = max(float(np.percentile(pos, 1)), config["floor"]) if len(pos) else config["floor"]
        vmax = float(np.percentile(pos, 99.7)) if len(pos) else 1.0
        norm = LogNorm(vmin=vmin, vmax=max(vmax, vmin * 10.0))
        n = len(labels)
        fig, axs = plt.subplots(n, 2, figsize=(8.8, max(2.0 * n, 3.2)), squeeze=False, constrained_layout=True)
        extent = [-config["lim"], config["lim"], -config["lim"], config["lim"]]
        last = None
        for i, label in enumerate(labels):
            panels = [(face[i], "face-on  x-y", "y [kpc]"), (edge[i], "edge-on  x-z", "z [kpc]")]
            for j, (img, subtitle, ylabel) in enumerate(panels):
                ax = axs[i, j]
                last = ax.imshow(img, origin="lower", extent=extent, norm=norm, cmap=config["cmap"], interpolation="nearest", aspect="equal")
                ax.set_xlabel("x [kpc]")
                ax.set_ylabel(ylabel)
                ax.set_title(subtitle if i == 0 else None)
                ax.text(0.03, 0.94, label, transform=ax.transAxes, ha="left", va="top", color="white", fontsize=9, weight="bold", bbox=dict(facecolor="black", alpha=0.45, edgecolor="none", pad=2.5))
                if np.isfinite(times[i]):
                    ax.text(0.97, 0.05, f"t={times[i]:.2f}", transform=ax.transAxes, ha="right", va="bottom", color="white", fontsize=8, bbox=dict(facecolor="black", alpha=0.35, edgecolor="none", pad=2.0))
                ax.tick_params(labelsize=8)
        fig.suptitle(config.get("title"), fontsize=13, weight="bold")
        if last is not None:
            cbar = fig.colorbar(last, ax=axs.ravel().tolist(), shrink=0.86, pad=0.015)
            cbar.set_label("projected mass per pixel")
        path = self.settings.save_figure(fig, config["filename"], dpi=config.get("dpi"))
        plt.close(fig)
        return path


class SurfaceDensityResidualsPlot(BasePlot):
    name = "surface_density_residuals"
    description = "Residual maps log10 Sigma_model - log10 Sigma_baseline for face-on and edge-on projections."
    data_contract = {"labels": F(("S",), dtype="str"), "faceon": F(("S", "B", "B")), "edgeon": F(("S", "B", "B"))}
    default_config = {"title": "Surface-density residuals vs CDM", "baseline_index": 0, "lim": 12.0, "eps": 1e-12, "cmap": "RdBu_r", "vmax": 1.0, "dpi": 190, "filename": "02_surface_density_residual_vs_cdm_final.png"}

    def render(self, data, config):
        labels = list(data["labels"])
        face = np.asarray(data["faceon"], dtype=float)
        edge = np.asarray(data["edgeon"], dtype=float)
        base = int(config.get("baseline_index", 0))
        rows = [i for i in range(len(labels)) if i != base]
        if not rows:
            rows = [base]
        fig, axs = plt.subplots(len(rows), 2, figsize=(8.8, max(2.0 * len(rows), 3.0)), squeeze=False, constrained_layout=True)
        extent = [-config["lim"], config["lim"], -config["lim"], config["lim"]]
        norm = TwoSlopeNorm(vmin=-config["vmax"], vcenter=0.0, vmax=config["vmax"])
        last = None
        for rr, i in enumerate(rows):
            for j, (arr, brr, title, ylabel) in enumerate([(face[i], face[base], "face-on residual", "y [kpc]"), (edge[i], edge[base], "edge-on residual", "z [kpc]")]):
                resid = np.log10(arr + config["eps"]) - np.log10(brr + config["eps"])
                ax = axs[rr, j]
                last = ax.imshow(resid, origin="lower", extent=extent, norm=norm, cmap=config["cmap"], interpolation="nearest", aspect="equal")
                ax.set_xlabel("x [kpc]"); ax.set_ylabel(ylabel)
                ax.set_title(title if rr == 0 else None)
                ax.text(0.03, 0.94, f"{labels[i]} − {labels[base]}", transform=ax.transAxes, ha="left", va="top", color="black", fontsize=9, weight="bold", bbox=dict(facecolor="white", alpha=0.65, edgecolor="none", pad=2.5))
                ax.tick_params(labelsize=8)
        fig.suptitle(config.get("title"), fontsize=13, weight="bold")
        if last is not None:
            cbar = fig.colorbar(last, ax=axs.ravel().tolist(), shrink=0.86, pad=0.015)
            cbar.set_label(r"$\Delta \log_{10}\Sigma$")
        path = self.settings.save_figure(fig, config["filename"], dpi=config.get("dpi"))
        plt.close(fig)
        return path


class MorphologyProfilesComparePlot(BasePlot):
    name = "morphology_profiles_compare"
    description = "Final cumulative radial profiles: b/a, c/a, z_rms/R_rms and |vrot|/sigma for group comparison."
    data_contract = {"series": F(("S",), dtype="any")}
    default_config = {"title": "Radial morphology and rotation-support profiles", "dpi": 180, "filename": "03_shape_radial_profiles_final.png"}

    def validate_data(self, data):
        if "series" not in data or len(data["series"]) == 0:
            raise PlotValidationError(f"{self.name}: missing non-empty 'series'")
        for i, s in enumerate(data["series"]):
            validate_fields(f"{self.name}.series[{i}]", s, {"label": F((), dtype="str"), "radii": F(("R",)), "ba": F(("R",)), "ca": F(("R",)), "thickness": F(("R",)), "vrot_over_sigma": F(("R",))})

    def render(self, data, config):
        fig, axs = plt.subplots(2, 2, figsize=(9.6, 6.8), sharex=True, constrained_layout=True)
        specs = [("ba", "b/a (<r)", (0.0, 1.08)), ("ca", "c/a (<r)", (0.0, 1.08)), ("thickness", r"$z_{rms}/R_{rms}$ (<r)", (0.0, 1.1)), ("vrot_over_sigma", r"$|\langle v_\phi\rangle|/\sigma_{3D}$ (<r)", (0.0, None))]
        for si, s in enumerate(data["series"]):
            color = self.settings.palette[si % len(self.settings.palette)]
            for ax, (key, ylabel, ylim) in zip(axs.ravel(), specs):
                ax.plot(s["radii"], s[key], lw=1.8, color=color, label=s["label"])
                self.settings.style_axis(ax, xlabel="r [kpc]", ylabel=ylabel, xscale="log", ylim=ylim, grid=True)
        axs[0, 0].legend(frameon=False, fontsize=8)
        fig.suptitle(config.get("title"), fontsize=13, weight="bold")
        path = self.settings.save_figure(fig, config["filename"], dpi=config.get("dpi"))
        plt.close(fig)
        return path


class PhaseSpaceComparePlot(BasePlot):
    name = "phase_space_compare"
    description = "Cylindrical phase-space panels: R vs v_phi mass-weighted histograms for disk/cold-branch search."
    data_contract = {"labels": F(("S",), dtype="str"), "phase": F(("S", "V", "R")), "extent": F((4,))}
    default_config = {"title": r"Phase space: $R$ vs $v_\phi$", "cmap": "viridis", "floor": 1e-12, "dpi": 190, "filename": "04_phase_space_R_vphi_final.png"}

    def render(self, data, config):
        labels = list(data["labels"])
        phase = np.asarray(data["phase"], dtype=float)
        extent = tuple(np.asarray(data["extent"], dtype=float))
        n = len(labels); cols = min(3, n); rows = int(np.ceil(n / cols))
        fig, axs = plt.subplots(rows, cols, figsize=(3.4 * cols, 2.8 * rows), squeeze=False, constrained_layout=True)
        vals = phase[np.isfinite(phase) & (phase > 0)]
        norm = LogNorm(vmin=max(np.percentile(vals, 1), config["floor"]) if len(vals) else config["floor"], vmax=np.percentile(vals, 99.7) if len(vals) else 1.0)
        last = None
        for i, ax in enumerate(axs.ravel()):
            if i >= n:
                ax.axis("off"); continue
            last = ax.imshow(phase[i], origin="lower", extent=extent, aspect="auto", norm=norm, cmap=config["cmap"], interpolation="nearest")
            ax.axhline(0.0, color="w", lw=0.8, ls=":", alpha=0.85)
            ax.set_title(labels[i], fontsize=10, weight="bold")
            ax.set_xlabel("R [kpc]"); ax.set_ylabel(r"$v_\phi$ [km/s]")
        fig.suptitle(config.get("title"), fontsize=13, weight="bold")
        if last is not None:
            cbar = fig.colorbar(last, ax=axs.ravel().tolist(), shrink=0.86, pad=0.015)
            cbar.set_label("projected mass")
        path = self.settings.save_figure(fig, config["filename"], dpi=config.get("dpi"))
        plt.close(fig)
        return path


class DiskDashboardPlot(BasePlot):
    name = "disk_dashboard"
    description = "Compact presentation dashboard combining final metric bars, morphology time-series and interaction/core evolution."
    data_contract = {"summary_labels": F(("S",), dtype="str"), "ca_final": F(("S",)), "thickness_final": F(("S",)), "vrot_final": F(("S",)), "ninteractions_final": F(("S",)), "disk_score": F(("S",)), "metric_series": F(("S",), dtype="any", required=False)}
    default_config = {"title": "Dark-disk candidate dashboard", "dpi": 190, "filename": "05_disk_dashboard.png"}

    def render(self, data, config):
        labels = [str(x) for x in data["summary_labels"]]
        x = np.arange(len(labels))
        fig, axs = plt.subplots(2, 2, figsize=(11.0, 6.8), constrained_layout=True)
        bar_specs = [("ca_final", "final c/a r<5", (0, 1.05)), ("thickness_final", r"final $z_{rms}/R_{rms}$ r<5", (0, 1.05)), ("vrot_final", r"final $|vrot|/\sigma$ r<5", (0, None)), ("disk_score", "heuristic disk score", (0, None))]
        for ax, (key, ylabel, ylim) in zip(axs.ravel(), bar_specs):
            vals = np.asarray(data[key], dtype=float)
            ax.bar(x, vals, color=[self.settings.palette[i % len(self.settings.palette)] for i in x], alpha=0.9)
            ax.set_xticks(x); ax.set_xticklabels(labels, rotation=28, ha="right", fontsize=8)
            self.settings.style_axis(ax, ylabel=ylabel, ylim=ylim, grid={"enabled": True, "axis": "y", "alpha": 0.25})
            if key in {"ca_final", "thickness_final", "vrot_final"}:
                ref = {"ca_final": 0.75, "thickness_final": 0.55, "vrot_final": 0.15}[key]
                ax.axhline(ref, color="0.25", lw=0.9, ls=":")
        fig.suptitle(config.get("title"), fontsize=13, weight="bold")
        path = self.settings.save_figure(fig, config["filename"], dpi=config.get("dpi"))
        plt.close(fig)
        return path


# ═══════════════════════════ presentation/diagnostic plots ══════════════════

class EnergyLossVsFPlot(BasePlot):
    name = "diag_eloss_vs_f"
    description = (
        "Диагностика dSIDM dissipation: по оси X заданная диссипация f/D "
        "(DM_DissipationFactor), по оси Y измеренная относительная потеря "
        "кинетической энергии рассеявшихся частиц ΔE/E. Точки + линия y=x — "
        "если измеренная потеря совпадает с заданной диссипацией. По "
        "определению dSIDM энергия падает как (1-D)^2, то есть ΔE/E=2D-D^2 "
        "(пунктирная кривая). Данные готовит loader `interacted_kinetic_energy()`."
    )
    data_contract = {
        "f_set": F(("S",)),
        "measured": F(("S",)),
        "labels": F(("S",), dtype="str", required=False),
    }
    default_config = {
        "title": None,
        "xlabel": r"prescribed $f = D$ (DM_DissipationFactor)",
        "ylabel": r"measured $\Delta E / E$",
        "xlim": (0.0, 1.0),
        "ylim": (0.0, 1.15),
        "marker": "o",
        "color_index": 0,
        "show_yx_line": False,
        "show_theory_curve": True,
        "legend_loc": "lower right",
        "figsize_key": "page",
        "dpi": None,
        "filename": "diag_eloss_vs_f.png",
    }

    def render(self, data, config):
        f_set = np.asarray(data["f_set"], dtype=float)
        measured = np.asarray(data["measured"], dtype=float)
        labels = data.get("labels")

        fig, ax = plt.subplots(figsize=self.settings.figsize(config["figsize_key"]))
        ax.scatter(f_set, measured, marker=config["marker"],
                   color=self.settings.palette[config["color_index"]],
                   s=self.settings.marker_size * self.settings.marker_size + 20,
                   zorder=5, label="measured")
        if labels is not None:
            for xv, yv, lab in zip(f_set, measured, labels):
                ax.annotate(str(lab), (xv, yv), textcoords="offset points",
                            xytext=(7, 5), fontsize=self.settings.font_size - 1)
        # Точки вне ylim (например runaway: dE/E взрывается) — пометить у края.
        ylim = config.get("ylim")
        if ylim:
            ylo, yhi = float(ylim[0]), float(ylim[1])
            labels_arr = labels if labels is not None else []
            for xv, yv, lab in zip(f_set, measured, labels_arr):
                if not np.isfinite(yv) or yv < ylo or yv > yhi:
                    edge_y = ylo if yv <= ylo or not np.isfinite(yv) else yhi
                    ax.annotate(
                        f"{lab}: {yv:.2e} (off-scale)",
                        (xv, edge_y), textcoords="offset points", xytext=(0, 6),
                        ha="center", fontsize=self.settings.font_size - 2,
                        color="0.35", style="italic")
        if config.get("show_theory_curve"):
            xg = np.linspace(0.0, 1.0, 200)
            ax.plot(xg, 2.0 * xg - xg * xg, ls="--", lw=self.settings.line_width_fit,
                    color="0.35", zorder=3,
                    label=r"theory: $\Delta E/E = 2D - D^2$")
        self.settings.style_axis(
            ax, title=config.get("title"), xlabel=config.get("xlabel"),
            ylabel=config.get("ylabel"), xlim=config.get("xlim"),
            ylim=config.get("ylim"), grid=True,
            legend=(dict(loc=config["legend_loc"])
                    if config.get("legend_loc") else True))
        fig.tight_layout()
        path = self.settings.save_figure(fig, config["filename"], dpi=config.get("dpi"))
        plt.close(fig)
        return path


class CriteriaTimePanelPlot(BasePlot):
    name = "criteria_time_panel"
    description = (
        "Объединённая панель критериев диска: три вертикальные панели c/a(t), "
        "z_rms/R_rms(t), |Vrot|/sigma(t). Данные — 'series': список per-run "
        "словарей {times, ca, thickness, vrot_over_sigma, label, color}. "
        "Один run = один цвет во всех панелях; одна общая легенда справа; "
        "горизонтальные пороги диска (0.75, 0.55, 0.15) серым dashed."
    )
    inner_contract = {
        "times": F(("T",)),
        "ca": F(("T",)),
        "thickness": F(("T",)),
        "vrot_over_sigma": F(("T",)),
        "label": F((), dtype="str", required=False),
        "color": F((), dtype="str", required=False),
    }
    data_contract = {"series": F(("S",), dtype="any")}

    def validate_data(self, data):
        _validate_series_list(self.name, data, self.inner_contract)

    default_config = {
        "title": None,
        "xlabel": "t [code time]",
        "threshold_ca": 0.75,
        "threshold_thickness": 0.55,
        "threshold_vrot": 0.15,
        "criteria_labels": [r"$c/a$ (r<5)",
                            r"$z_{\rm rms}/R_{\rm rms}$ (r<5)",
                            r"$|V_{\rm rot}|/\sigma$ (r<5)"],
        "ylim_ca": (0.70, 1.00),
        "ylim_thickness": (0.40, 0.80),
        "ylim_vrot": (0.0, 0.45),
        "xlim": (0.0, 2.0),
        "figsize": (8.2, 9.0),
        "legend_font_size": None,
        "dpi": 200,
        "filename": "diag_criteria_time_panel.png",
    }

    def render(self, data, config):
        clabels = config.get("criteria_labels") or [r"$c/a$", r"$z_{\rm rms}/R_{\rm rms}$",
                                                    r"$|V_{\rm rot}|/\sigma$"]
        specs = [
            ("ca", config["threshold_ca"], config.get("ylim_ca"), clabels[0]),
            ("thickness", config["threshold_thickness"],
             config.get("ylim_thickness"), clabels[1]),
            ("vrot_over_sigma", config["threshold_vrot"],
             config.get("ylim_vrot"), clabels[2]),
        ]

        fig, axs = plt.subplots(3, 1, figsize=tuple(config["figsize"]), sharex=True)
        for ax, (key, thr, ylim, ylab) in zip(axs, specs):
            for i, s in enumerate(data["series"]):
                color = s.get("color") or self.settings.palette[i % len(self.settings.palette)]
                ax.plot(np.asarray(s["times"], dtype=float),
                        np.asarray(s[key], dtype=float),
                        color=color, lw=2.2, label=s.get("label"))
            ax.axhline(thr, ls="--", lw=1.4, color="0.35", zorder=2)
            self.settings.style_axis(ax, ylabel=ylab, xlim=config.get("xlim"),
                                     ylim=ylim, grid=True)
        axs[-1].set_xlabel(config["xlabel"])

        handles, labels = axs[0].get_legend_handles_labels()
        fs = config.get("legend_font_size") or self.settings.legend_font_size
        # Легенда в свободной верхней зоне нижней панели (|Vrot|/sigma мал).
        fig.legend(handles, labels, loc="upper right",
                   bbox_to_anchor=(0.995, 0.335), fontsize=fs,
                   frameon=True, framealpha=0.92, borderaxespad=0.4)
        if config.get("title"):
            fig.suptitle(config["title"], fontsize=self.settings.title_size,
                         weight="bold")
        fig.tight_layout(rect=(0.0, 0.0, 1.0, 0.99))
        path = self.settings.save_figure(fig, config["filename"], dpi=config.get("dpi"))
        plt.close(fig)
        return path


class RunawayTimestepPanelPlot(BasePlot):
    name = "runaway_timestep_panel"
    description = (
        "Диагностика runaway: две вертикальные панели с общей осью времени. "
        "Верх — interaction rate (N_interactions на снапшот, diff от "
        "cumulative ninteractions_total; при доступности только двух точек "
        "fallback на cumulative). Низ — минимальный timestep (systemstep) "
        "с колонапсом. Данные — 'series' из load_metrics_series() "
        "(ninteractions_total, nearest_systemstep). Log-шкалы на обеих осях Y."
    )
    inner_contract = {
        "times": F(("T",)),
        "ninteractions": F(("T",)),
        "dt_min": F(("T",)),
        "label": F((), dtype="str", required=False),
        "color": F((), dtype="str", required=False),
    }
    data_contract = {"series": F(("S",), dtype="any")}

    def validate_data(self, data):
        _validate_series_list(self.name, data, self.inner_contract)

    default_config = {
        "title": None,
        "xlabel": "t [code time]",
        "ni_ylabel": "interactions / snapshot",
        "dt_ylabel": r"$\min dt$ [code t]",
        "ni_yscale": "log",
        "dt_yscale": "log",
        "xlim": None,
        "figsize": (8.6, 7.2),
        "dpi": 200,
        "filename": "diag_runaway_timestep_panel.png",
    }

    def render(self, data, config):
        fig, (ax_ni, ax_dt) = plt.subplots(
            2, 1, figsize=tuple(config["figsize"]), sharex=True)

        handles = []
        for i, s in enumerate(data["series"]):
            times = np.asarray(s["times"], dtype=float)
            ni = np.asarray(s["ninteractions"], dtype=float)
            dt = np.asarray(s["dt_min"], dtype=float)
            color = s.get("color") or self.settings.palette[i % len(self.settings.palette)]
            label = s.get("label")

            # rate per snapshot: diff of cumulative; fallback cumulative
            rate = np.diff(ni)
            mid_t = 0.5 * (times[1:] + times[:-1]) if len(times) > 1 else times
            ok = np.isfinite(rate) & (rate > 0)
            if ok.any():
                ln, = ax_ni.plot(mid_t[ok], rate[ok], color=color, lw=2.2,
                                 label=label)
                handles.append(ln)
            else:
                ln, = ax_ni.plot(times, ni, color=color, lw=2.2, label=label)
                handles.append(ln)

            okdt = np.isfinite(dt) & (dt > 0)
            ax_dt.plot(times[okdt], dt[okdt], color=color, lw=2.2,
                       label=label if i == 0 else None)

        self.settings.style_axis(ax_ni, ylabel=config["ni_ylabel"],
                                 yscale=config["ni_yscale"], grid=True)
        self.settings.style_axis(ax_dt, ylabel=config["dt_ylabel"],
                                 yscale=config["dt_yscale"], grid=True)
        ax_dt.set_xlabel(config["xlabel"])
        if config.get("xlim"):
            for ax in (ax_ni, ax_dt):
                ax.set_xlim(*config["xlim"])
        if handles:
            fig.legend(handles, [h.get_label() for h in handles],
                       loc="upper right", fontsize=self.settings.legend_font_size,
                       frameon=True, framealpha=0.92)
        fig.tight_layout()
        path = self.settings.save_figure(fig, config["filename"], dpi=config.get("dpi"))
        plt.close(fig)
        return path


DIAG_PLOT_CLASSES = [EnergyLossVsFPlot, CriteriaTimePanelPlot, RunawayTimestepPanelPlot]


COMPARE_PLOT_CLASSES = [DensityComparePlot, LogSlopeComparePlot,
                        SigmaVComparePlot, LogRhoComparePlot,
                        RotCurveComparePlot, CoreDensityVsSigmaPlot,
                        VisualMorphologyMontagePlot, SurfaceDensityResidualsPlot,
                        MorphologyProfilesComparePlot, PhaseSpaceComparePlot,
                        DiskDashboardPlot]


