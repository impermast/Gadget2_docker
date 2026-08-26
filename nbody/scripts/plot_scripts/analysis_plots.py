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
                                 yscale=config["mean_yscale"], grid=True)

        f = np.isfinite(ni_frac) & (ni_frac > 0)
        if f.any():
            axs[1].plot(r[f], ni_frac[f],
                        color=self.settings.palette[1],
                        lw=self.settings.line_width_main)
        self.settings.style_axis(axs[1], xlabel=config["xlabel"],
                                 ylabel=config["frac_ylabel"],
                                 xscale=config["xscale"],
                                 yscale=config["frac_yscale"], grid=True)

        fig.tight_layout()
        path = self.settings.save_figure(fig, config["filename"], dpi=config["dpi"])
        plt.close(fig)
        return path


ANALYSIS_PLOT_CLASSES = [DensityPlot, LogSlopePlot, SigmaVPlot, InteractionsRadialPlot]


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


COMPARE_PLOT_CLASSES = [DensityComparePlot, LogSlopeComparePlot,
                        SigmaVComparePlot, LogRhoComparePlot,
                        RotCurveComparePlot, CoreDensityVsSigmaPlot]


