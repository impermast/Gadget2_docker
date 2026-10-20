#!/usr/bin/env python3
"""plots/campaigns — переезд из plot_scripts (математика дословно, см. этап 1).
Сравнение группы прогонов и диагностика кампаний (блок campaigns).
"""
from __future__ import annotations

from typing import Any, Dict, Mapping, Optional

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.colors import LogNorm, TwoSlopeNorm

from analysis.base import (
    BasePlot,
    FieldSpec as F,
    PlotValidationError,
    format_contract,
    validate_fields,
)
from analysis.registry import register

from analysis.style import resolve_xlim, shade_unresolved

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
        from analysis.style import resolve_xlim, shade_unresolved

        fig, ax = plt.subplots(figsize=self.settings.figsize(config["figsize_key"]))
        for i, s in enumerate(data["series"]):
            label = str(s.get("label", f"series_{i}"))
            ax.plot(np.asarray(s["r"]), np.asarray(s[y_field]),
                    color=self.settings.palette[i % len(self.settings.palette)],
                    lw=self.settings.line_width_main, label=label)
        rmax = _series_unresolved_r(data["series"], config)
        shade_unresolved(ax, rmax, label=config.get("unresolved_label") or None)
        self.settings.style_axis(
            ax, title=config.get("title"), xlabel=config.get("xlabel"),
            ylabel=config.get("ylabel"), xscale=config.get("xscale"),
            yscale=config.get("yscale"),
            xlim=resolve_xlim(config.get("xlim"), rmax),
            ylim=config.get("ylim"), grid=True, legend=True)
        fig.tight_layout()
        path = self.settings.save_figure(fig, config["filename"],
                                         dpi=config.get("dpi"))
        plt.close(fig)
        return path




@register
class DensityComparePlot(_MultiSeriesPlot):
    name = "density_compare"
    block = "campaigns"
    summary = "Сравнение rho(r) группы прогонов на одних осях"
    data_source = "series"
    inputs = ('runs',)
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




@register
class LogSlopeComparePlot(_MultiSeriesPlot):
    name = "log_slope_compare"
    block = "campaigns"
    summary = "Сравнение наклона dlnrho/dlnr группы прогонов"
    data_source = "series"
    inputs = ('runs',)
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




@register
class SigmaVComparePlot(_MultiSeriesPlot):
    name = "sigma_v_compare"
    block = "campaigns"
    summary = "Сравнение sigma_v(r) группы прогонов"
    data_source = "series"
    inputs = ('runs',)
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
        rmax = _series_unresolved_r(series, config)
        from analysis.style import resolve_xlim, shade_unresolved

        shade_unresolved(ax_top, rmax, label=config.get("unresolved_label") or None)
        shade_unresolved(ax_diff, rmax, label=None)
        self.settings.style_axis(
            ax_top, title=config.get("title"),
            ylabel=config.get("top_ylabel"),
            yscale=config.get("top_yscale"), grid=True)
        self.settings.style_axis(
            ax_diff, xlabel=config.get("xlabel"),
            ylabel=config.get("diff_ylabel"),
            xscale=config.get("xscale"),
            xlim=resolve_xlim(config.get("xlim"), rmax), grid=True)
        if config.get("legend"):
            ax_top.legend(frameon=False,
                          fontsize=self.settings.legend_font_size)
        fig.tight_layout()
        path = self.settings.save_figure(fig, config["filename"],
                                         dpi=config.get("dpi"))
        plt.close(fig)
        return path




@register
class LogRhoComparePlot(_DeltaComparePlot):
    name = "log_rho_compare"
    block = "campaigns"
    summary = "Верх: rho(r); низ: Delta log rho vs CDM-референс"
    data_source = "series"
    inputs = ('runs',)
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
        "title": "Density profiles and residuals relative to CDM",
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




@register
class RotCurveComparePlot(_DeltaComparePlot):
    name = "rot_curve_compare"
    block = "campaigns"
    summary = "Верх: v_circ(r); низ: Delta v vs CDM-референс"
    data_source = "series"
    inputs = ('runs',)
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
        "title": "Circular-speed profiles and residuals relative to CDM",
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




@register
class CoreDensityVsSigmaPlot(BasePlot):
    name = "core_density_vs_sigma"
    block = "campaigns"
    summary = "Относительное изменение rho_core к CDM при изменении sigma/m"
    data_source = "series"
    inputs = ('runs',)
    description = (
        "Изменение core density относительно CDM в фиксированном радиусе как "
        "функция SIDM cross-section. Если CDM reference не передан, показывает "
        "абсолютную rho_core. Данные берет compare_runs.py из snapshot headers "
        "и prepare_profile_data()."
    )
    data_contract = {
        "sigma": F(("S",)),
        "rho_core": F(("S",)),
        "labels": F(("S",), dtype="str", required=False),
        "baseline_rho_core": F((), required=False),
        "baseline_label": F((), dtype="str", required=False),
    }
    default_config = {
        "title": "Core-density change vs CDM",
        "fractional_title": "T=1 core-density shift relative to CDM",
        "fractional_ylabel": r"$\Delta\rho_{\rm core}/\rho_{\rm CDM}$ [%]",
        "baseline_label": "CDM reference",
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
        labels = data.get("labels")
        baseline = data.get("baseline_rho_core")
        fig, ax = plt.subplots(figsize=self.settings.figsize(config["figsize_key"]))
        ylim = config.get("ylim")
        if baseline is not None and float(baseline) > 0:
            change_pct = 100.0 * (rho_core / float(baseline) - 1.0)
            order = np.argsort(sigma)
            ax.plot(sigma[order], change_pct[order], config["marker"],
                    color=self.settings.palette[0],
                    ms=self.settings.marker_size + 2,
                    lw=self.settings.line_width_main)
            ax.axhline(0.0, color="0.25", linestyle="--", linewidth=1.0)
            for j, i in enumerate(order):
                label = str(labels[i]) if labels is not None else f"sigma={sigma[i]:g}"
                is_rightmost = j == len(order) - 1
                ax.annotate(f"{label}\n{change_pct[i]:+.2f}%",
                            (sigma[i], change_pct[i]), textcoords="offset points",
                            xytext=(-8, 7) if is_rightmost else (8, 7),
                            ha="right" if is_rightmost else "left",
                            fontsize=self.settings.font_size - 1)
            limit = max(1.0, float(np.nanmax(np.abs(change_pct))) * 1.35)
            if ylim is None:
                ylim = (-limit, limit)
            title = config.get("fractional_title", config.get("title"))
            ylabel = config.get("fractional_ylabel")
            yscale = "linear"
            baseline_label = data.get("baseline_label", "CDM reference")
            ax.text(0.02, 0.98,
                    f"Reference: {baseline_label}; rho_core={float(baseline):.4e}",
                    transform=ax.transAxes, ha="left", va="top",
                    fontsize=self.settings.font_size - 1)
        else:
            for i, (x, y) in enumerate(zip(sigma, rho_core)):
                label = str(labels[i]) if labels is not None else f"run {i + 1}"
                ax.plot([x], [y], config["marker"],
                        color=self.settings.palette[i % len(self.settings.palette)],
                        ms=self.settings.marker_size + 2,
                        label=f"{label}: $\\rho$={y:.4e}")
            if ylim is None and rho_core.size and np.all(rho_core > 0):
                ylim = (float(np.min(rho_core)) * 0.5,
                        float(np.max(rho_core)) * 2.0)
            title = config.get("title")
            ylabel = config.get("ylabel")
            yscale = config.get("yscale")
            if labels is not None:
                ax.legend(frameon=False, loc="best", fontsize=self.settings.font_size - 1)
        self.settings.style_axis(
            ax, title=title, xlabel=config.get("xlabel"), ylabel=ylabel,
            xscale=config.get("xscale"), yscale=yscale, xlim=config.get("xlim"),
            ylim=ylim, grid=True)
        fig.tight_layout()
        path = self.settings.save_figure(fig, config["filename"],
                                         dpi=config.get("dpi"))
        plt.close(fig)
        return path




@register
class VisualMorphologyMontagePlot(BasePlot):
    name = "visual_morphology_montage"
    block = "campaigns"
    runner = "runners/make_campaign_morphology_plots.py"
    summary = "Монтаж карт поверхностной плотности группы прогонов"
    data_source = "prepare_visual_snapshot"
    inputs = ('runs',)
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
        fig, axs = plt.subplots(
            n, 2, figsize=(7.5, max(2.45 * n + 1.0, 4.0)), squeeze=False)
        fig.subplots_adjust(left=0.075, right=0.90, top=0.96, bottom=0.035,
                            wspace=0.12, hspace=0.25)
        extent = [-config["lim"], config["lim"], -config["lim"], config["lim"]]
        last = None
        for i, label in enumerate(labels):
            for j, (img, ylabel) in enumerate(((face[i], "y [kpc]"),
                                                (edge[i], "z [kpc]"))):
                ax = axs[i, j]
                last = ax.imshow(img, origin="lower", extent=extent, norm=norm,
                                 cmap=config["cmap"], interpolation="nearest",
                                 aspect="equal")
                ax.set_ylabel(ylabel if j == 0 else "")
                ax.set_xlabel("x [kpc]" if i == n - 1 else "")
                if i == 0:
                    ax.set_title("Face-on (x-y)" if j == 0 else "Edge-on (x-z)",
                                 fontsize=10, pad=5)
                if j == 0:
                    ax.text(0.035, 0.94, label, transform=ax.transAxes,
                            ha="left", va="top", color="white", fontsize=8,
                            weight="bold", bbox=dict(facecolor="black", alpha=0.5,
                            edgecolor="none", pad=2.2))
                if j == 1 and np.isfinite(times[i]):
                    ax.text(0.96, 0.05, f"t={times[i]:.2f}", transform=ax.transAxes,
                            ha="right", va="bottom", color="white", fontsize=8,
                            bbox=dict(facecolor="black", alpha=0.4,
                            edgecolor="none", pad=2.0))
                ax.set_xticks([-10, 0, 10])
                ax.set_yticks([-10, 0, 10])
                ax.tick_params(labelsize=7, pad=2,
                               labelleft=(j == 0), labelbottom=(i == n - 1))
        fig.suptitle(config.get("title"), fontsize=13, weight="bold", y=0.995)
        if last is not None:
            cax = fig.add_axes([0.925, 0.12, 0.016, 0.76])
            cbar = fig.colorbar(last, cax=cax)
            cbar.set_label("projected mass per pixel", fontsize=9)
            cbar.ax.tick_params(labelsize=8)
        path = self.settings.save_figure(fig, config["filename"], dpi=config.get("dpi"))
        plt.close(fig)
        return path




def _box_smooth2d(values: np.ndarray, radius: int) -> np.ndarray:
    """Separable box smoothing without an extra SciPy dependency."""
    arr = np.asarray(values, dtype=float)
    if radius <= 0:
        return arr
    width = 2 * radius + 1
    padded = np.pad(arr, ((radius, radius), (0, 0)), mode="edge")
    cumulative = np.pad(np.cumsum(padded, axis=0), ((1, 0), (0, 0)))
    vertical = (cumulative[width:] - cumulative[:-width]) / width
    padded = np.pad(vertical, ((0, 0), (radius, radius)), mode="edge")
    cumulative = np.pad(np.cumsum(padded, axis=1), ((0, 0), (1, 0)))
    return (cumulative[:, width:] - cumulative[:, :-width]) / width


@register
class SurfaceDensityResidualsPlot(BasePlot):
    name = "surface_density_residuals"
    block = "campaigns"
    runner = "runners/make_campaign_morphology_plots.py"
    summary = "Остатки поверхностной плотности vs CDM-база"
    data_source = "prepare_visual_snapshot"
    inputs = ('runs',)
    description = "Box-smoothed log10 Sigma residuals for face-on and edge-on projections; identical zero-residual controls are omitted."
    data_contract = {"labels": F(("S",), dtype="str"), "faceon": F(("S", "B", "B")), "edgeon": F(("S", "B", "B"))}
    default_config = {"title": "Smoothed surface-density residuals vs CDM", "baseline_index": 0, "lim": 12.0, "eps": 1e-12, "smooth_radius": 3, "cmap": "RdBu_r", "vmax": None, "vmax_floor": 0.05, "vmax_cap": 1.0, "color_quantile": 99.0, "dpi": 190, "filename": "02_surface_density_residual_vs_cdm_final.png"}

    def render(self, data, config):
        labels = list(data["labels"])
        face = np.asarray(data["faceon"], dtype=float)
        edge = np.asarray(data["edgeon"], dtype=float)
        base = int(config.get("baseline_index", 0))
        eps = float(config.get("eps", 1e-12))
        radius = int(config.get("smooth_radius", 2))
        base_face = _box_smooth2d(face[base], radius)
        base_edge = _box_smooth2d(edge[base], radius)
        residuals, omitted_identical = {}, []
        for i in range(len(labels)):
            if i == base:
                continue
            face_delta = np.log10(_box_smooth2d(face[i], radius) + eps) \
                - np.log10(base_face + eps)
            edge_delta = np.log10(_box_smooth2d(edge[i], radius) + eps) \
                - np.log10(base_edge + eps)
            if (np.nanmax(np.abs(face_delta)) <= 1e-12
                    and np.nanmax(np.abs(edge_delta)) <= 1e-12):
                omitted_identical.append(labels[i])
            else:
                residuals[i] = (face_delta, edge_delta)
        rows = list(residuals)
        if not rows:
            rows = [base]
            residuals[base] = (np.zeros_like(base_face), np.zeros_like(base_edge))
        all_abs = np.concatenate([np.abs(delta).ravel()
                                  for pair in residuals.values() for delta in pair])
        configured_vmax = config.get("vmax")
        if configured_vmax is None:
            finite_abs = all_abs[np.isfinite(all_abs)]
            robust_vmax = (float(np.percentile(finite_abs,
                                               float(config.get("color_quantile", 99.0))))
                           if finite_abs.size else float(config["vmax_floor"]))
            vmax = min(float(config["vmax_cap"]),
                       max(float(config["vmax_floor"]), robust_vmax))
        else:
            vmax = float(configured_vmax)
        nrows = len(rows)
        fig, axs = plt.subplots(
            nrows, 2, figsize=(7.5, max(2.45 * nrows + 1.0, 4.0)), squeeze=False)
        fig.subplots_adjust(left=0.075, right=0.90, top=0.88,
                            bottom=0.08 if omitted_identical else 0.07,
                            wspace=0.12, hspace=0.25)
        extent = [-config["lim"], config["lim"], -config["lim"], config["lim"]]
        norm = TwoSlopeNorm(vmin=-vmax, vcenter=0.0, vmax=vmax)
        last = None
        for rr, i in enumerate(rows):
            face_delta, edge_delta = residuals[i]
            for j, (resid, ylabel) in enumerate(((face_delta, "y [kpc]"),
                                                 (edge_delta, "z [kpc]"))):
                ax = axs[rr, j]
                last = ax.imshow(resid, origin="lower", extent=extent, norm=norm,
                                 cmap=config["cmap"], interpolation="nearest",
                                 aspect="equal")
                ax.set_ylabel(ylabel if j == 0 else "")
                ax.set_xlabel("x [kpc]" if rr == nrows - 1 else "")
                if rr == 0:
                    ax.set_title("Face-on residual" if j == 0 else "Edge-on residual",
                                 fontsize=10, pad=5)
                if j == 0:
                    ax.text(0.035, 0.94, f"{labels[i]} − {labels[base]}",
                            transform=ax.transAxes, ha="left", va="top",
                            color="black", fontsize=8, weight="bold",
                            bbox=dict(facecolor="white", alpha=0.7,
                                      edgecolor="none", pad=2.2))
                ax.set_xticks([-10, 0, 10])
                ax.set_yticks([-10, 0, 10])
                ax.tick_params(labelsize=7, pad=2,
                               labelleft=(j == 0), labelbottom=(rr == nrows - 1))
        fig.suptitle(config.get("title"), fontsize=13, weight="bold", y=0.995)
        if last is not None:
            cax = fig.add_axes([0.925, 0.12, 0.016, 0.76])
            cbar = fig.colorbar(last, cax=cax)
            cbar.set_label(
                rf"{2 * radius + 1}×{2 * radius + 1}-px smoothed "
                r"$\Delta \log_{10}\Sigma$", fontsize=9)
            cbar.ax.tick_params(labelsize=8)
        path = self.settings.save_figure(fig, config["filename"], dpi=config.get("dpi"))
        plt.close(fig)
        return path




@register
class MorphologyProfilesComparePlot(BasePlot):
    name = "morphology_profiles_compare"
    block = "campaigns"
    runner = "runners/make_campaign_morphology_plots.py"
    summary = "Радиальные морфологические профили группы (c/a, вращение)"
    data_source = "series"
    inputs = ('runs',)
    description = "Final cumulative radial profiles: b/a, c/a, z_rms/R_rms and |vrot|/sigma for group comparison."
    data_contract = {"series": F(("S",), dtype="any")}
    default_config = {"title": "Radial morphology and rotation-support profiles", "dpi": 180, "filename": "03_shape_radial_profiles_final.png"}

    def validate_data(self, data):
        if "series" not in data or len(data["series"]) == 0:
            raise PlotValidationError(f"{self.name}: missing non-empty 'series'")
        for i, s in enumerate(data["series"]):
            validate_fields(f"{self.name}.series[{i}]", s, {"label": F((), dtype="str"), "radii": F(("R",)), "ba": F(("R",)), "ca": F(("R",)), "thickness": F(("R",)), "vrot_over_sigma": F(("R",))})

    def render(self, data, config):
        fig, axs = plt.subplots(2, 2, figsize=(10.5, 7.5), sharex=True)
        specs = [("ba", "b/a (<r)", (0.0, 1.08)), ("ca", "c/a (<r)", (0.0, 1.08)), ("thickness", r"$z_{rms}/R_{rms}$ (<r)", (0.0, 1.1)), ("vrot_over_sigma", r"$|\langle v_\phi\rangle|/\sigma_{3D}$ (<r)", (0.0, None))]
        for si, s in enumerate(data["series"]):
            color = self.settings.palette[si % len(self.settings.palette)]
            for ax, (key, ylabel, ylim) in zip(axs.ravel(), specs):
                ax.plot(s["radii"], s[key], lw=1.8, color=color, label=s["label"])
                self.settings.style_axis(ax, xlabel="r [kpc]", ylabel=ylabel,
                                         xscale="log", ylim=ylim, grid=True)
        handles, labels = axs[0, 0].get_legend_handles_labels()
        fig.legend(handles, labels, loc="lower center", bbox_to_anchor=(0.5, 0.01),
                   ncol=min(3, max(1, len(labels))), frameon=False, fontsize=8,
                   columnspacing=1.0, handlelength=2.0)
        fig.suptitle(config.get("title"), fontsize=13, weight="bold")
        fig.subplots_adjust(left=0.09, right=0.98, top=0.90, bottom=0.20,
                            wspace=0.32, hspace=0.25)
        path = self.settings.save_figure(fig, config["filename"], dpi=config.get("dpi"))
        plt.close(fig)
        return path




@register
class PhaseSpaceComparePlot(BasePlot):
    name = "phase_space_compare"
    block = "campaigns"
    runner = "runners/make_campaign_morphology_plots.py"
    summary = "Фазовое пространство R-vphi группы прогонов"
    data_source = "phase_space_histogram"
    inputs = ('runs',)
    description = "Cylindrical phase-space panels: R vs v_phi mass-weighted histograms for disk/cold-branch search."
    data_contract = {"labels": F(("S",), dtype="str"), "phase": F(("S", "V", "R")), "extent": F((4,))}
    default_config = {"title": r"Phase space: $R$ vs $v_\phi$", "cmap": "viridis", "floor": 1e-12, "dpi": 190, "filename": "04_phase_space_R_vphi_final.png"}

    def render(self, data, config):
        labels = list(data["labels"])
        phase = np.asarray(data["phase"], dtype=float)
        extent = tuple(np.asarray(data["extent"], dtype=float))
        n = len(labels); cols = min(3, n); rows = int(np.ceil(n / cols))
        fig, axs = plt.subplots(rows, cols,
                                figsize=(4.0 * cols + 1.0, 3.25 * rows),
                                squeeze=False)
        fig.subplots_adjust(left=0.075, right=0.90, top=0.88, bottom=0.07,
                            wspace=0.25, hspace=0.30)
        vals = phase[np.isfinite(phase) & (phase > 0)]
        norm = LogNorm(vmin=max(np.percentile(vals, 1), config["floor"]) if len(vals) else config["floor"], vmax=np.percentile(vals, 99.7) if len(vals) else 1.0)
        last = None
        for i, ax in enumerate(axs.ravel()):
            if i >= n:
                ax.axis("off"); continue
            last = ax.imshow(phase[i], origin="lower", extent=extent, aspect="auto",
                             norm=norm, cmap=config["cmap"], interpolation="nearest")
            ax.axhline(0.0, color="w", lw=0.8, ls=":", alpha=0.85)
            ax.set_title(labels[i], fontsize=9, weight="bold", pad=4)
            ax.set_xlabel("R [kpc]", fontsize=9)
            ax.set_ylabel(r"$v_\phi$ [km/s]", fontsize=9)
            ax.tick_params(labelsize=8)
        fig.suptitle(config.get("title"), fontsize=13, weight="bold", y=0.99)
        if last is not None:
            cax = fig.add_axes([0.925, 0.14, 0.016, 0.72])
            cbar = fig.colorbar(last, cax=cax)
            cbar.set_label("projected mass", fontsize=9)
            cbar.ax.tick_params(labelsize=8)
        path = self.settings.save_figure(fig, config["filename"], dpi=config.get("dpi"))
        plt.close(fig)
        return path




@register
class DiskDashboardPlot(BasePlot):
    name = "disk_dashboard"
    block = "campaigns"
    runner = "runners/make_campaign_morphology_plots.py"
    summary = "Дашборд дисковых диагностик группы прогонов"
    data_source = "series"
    inputs = ('runs',)
    description = "Compact presentation dashboard combining final metric bars, morphology time-series and interaction/core evolution."
    data_contract = {"summary_labels": F(("S",), dtype="str"), "ca_final": F(("S",)), "thickness_final": F(("S",)), "vrot_final": F(("S",)), "ninteractions_final": F(("S",)), "disk_score": F(("S",)), "metric_series": F(("S",), dtype="any", required=False)}
    default_config = {"title": "Final-snapshot morphology and interaction diagnostics", "dpi": 190, "filename": "05_disk_dashboard.png"}

    def render(self, data, config):
        labels = [str(x) for x in data["summary_labels"]]
        y = np.arange(len(labels))
        fig, axs = plt.subplots(2, 2, figsize=(12.0, 8.0))
        bar_specs = [("ca_final", "final c/a (r<5)", (0, 1.05)),
                     ("thickness_final", r"final $z_{rms}/R_{rms}$ (r<5)", (0, 1.05)),
                     ("vrot_final", r"final $|v_{rot}|/\sigma$ (r<5)", None),
                     ("ninteractions_final", "cumulative interactions (final snapshot)", None)]
        for ax, (key, xlabel, xlim) in zip(axs.ravel(), bar_specs):
            vals = np.asarray(data[key], dtype=float)
            ax.barh(y, vals,
                    color=[self.settings.palette[i % len(self.settings.palette)] for i in y],
                    alpha=0.9, height=0.72)
            ax.set_yticks(y)
            ax.set_yticklabels(labels, fontsize=8)
            ax.invert_yaxis()
            if xlim is not None:
                ax.set_xlim(*xlim)
            self.settings.style_axis(ax, xlabel=xlabel,
                                     grid={"enabled": True, "axis": "x", "alpha": 0.25})
            if key in {"ca_final", "thickness_final", "vrot_final"}:
                ref = {"ca_final": 0.75, "thickness_final": 0.55,
                       "vrot_final": 0.15}[key]
                ax.axvline(ref, color="0.25", lw=0.9, ls=":")
        fig.suptitle(config.get("title"), fontsize=13, weight="bold")
        fig.text(0.5, 0.025,
                 "Dotted cuts are provisional guides, not calibrated for this IC or a disk classification.",
                 ha="center", va="bottom", fontsize=8, color="0.3")
        fig.subplots_adjust(left=0.16, right=0.98, top=0.91, bottom=0.13,
                            wspace=0.35, hspace=0.35)
        path = self.settings.save_figure(fig, config["filename"], dpi=config.get("dpi"))
        plt.close(fig)
        return path


# ═══════════════════════════ presentation/diagnostic plots ══════════════════



@register
class EnergyLossVsFPlot(BasePlot):
    name = "diag_eloss_vs_f"
    block = "campaigns"
    runner = "runners/make_campaign_diag_plots.py"
    summary = "Потери энергии vs фактор диссипации (dSIDM-серия)"
    data_source = "load_metrics_series"
    inputs = ('runs',)
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




@register
class CriteriaTimePanelPlot(BasePlot):
    name = "criteria_time_panel"
    block = "campaigns"
    runner = "runners/make_campaign_diag_plots.py"
    summary = "Панель временных критериев disk-transition (dSIDM-серия)"
    data_source = "load_metrics_series"
    inputs = ('runs',)
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
        "title": "Morphology criteria over time (exploratory)",
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
        "xlim": None,
        "figsize": (11.2, 9.0),
        "legend_font_size": 7.5,
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
            ax.text(0.99, thr, f"provisional guide: {thr:g}",
                    transform=ax.get_yaxis_transform(), ha="right", va="bottom",
                    fontsize=7, color="0.25",
                    bbox=dict(facecolor="white", alpha=0.75,
                              edgecolor="none", pad=1.5))
            self.settings.style_axis(ax, ylabel=ylab, xlim=config.get("xlim"),
                                     ylim=ylim, grid=True)
        axs[-1].set_xlabel(config["xlabel"])

        handles, labels = axs[0].get_legend_handles_labels()
        fs = config.get("legend_font_size") or self.settings.legend_font_size
        fig.legend(handles, labels, loc="center left",
                   bbox_to_anchor=(0.76, 0.5), fontsize=fs,
                   frameon=False, borderaxespad=0.0)
        if config.get("title"):
            fig.suptitle(config["title"], fontsize=self.settings.title_size,
                         weight="bold")
        fig.subplots_adjust(left=0.12, right=0.74, bottom=0.08, top=0.88,
                            hspace=0.08)
        path = self.settings.save_figure(fig, config["filename"], dpi=config.get("dpi"))
        plt.close(fig)
        return path




@register
class RunawayTimestepPanelPlot(BasePlot):
    name = "runaway_timestep_panel"
    block = "campaigns"
    runner = "runners/make_campaign_diag_plots.py"
    summary = "Панель dt-runaway диагностики серии прогонов"
    data_source = "load_metrics_series"
    inputs = ('runs',)
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
        "title": "Interaction rate and timestep over time",
        "xlabel": "t [code time]",
        "ni_ylabel": "interactions / snapshot",
        "dt_ylabel": r"$\min dt$ [code t]",
        "ni_yscale": "log",
        "dt_yscale": "log",
        "xlim": None,
        "figsize": (11.2, 7.2),
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

            # Rate per snapshot: diff of cumulative; exclude zero-duration
            # duplicate terminal samples from the per-snapshot series.
            rate = np.diff(ni)
            delta_t = np.diff(times)
            mid_t = 0.5 * (times[1:] + times[:-1]) if len(times) > 1 else times
            ok = (np.isfinite(rate) & (rate > 0) & np.isfinite(delta_t)
                  & (delta_t > 1e-8))
            has_cumulative = np.isfinite(ni) & (ni > 0)
            if ok.any():
                ln, = ax_ni.plot(mid_t[ok], rate[ok], color=color, lw=2.2,
                                 label=label)
            elif has_cumulative.any():
                ln, = ax_ni.plot(times, ni, color=color, lw=2.2, label=label)
            else:
                # A zero-interaction control has no visible trace on a log axis;
                # retain it in the legend instead of implying data are missing.
                ln, = ax_ni.plot([], [], color=color, lw=2.2,
                                 label=f"{label} (no interactions)")
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
                       loc="center left", bbox_to_anchor=(0.76, 0.5),
                       fontsize=7.5, frameon=False)
        if config.get("title"):
            fig.suptitle(config["title"], fontsize=self.settings.title_size,
                         weight="bold")
        fig.subplots_adjust(left=0.12, right=0.74, bottom=0.10, top=0.88,
                            hspace=0.08)
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


