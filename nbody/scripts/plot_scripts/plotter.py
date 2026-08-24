#!/usr/bin/env python3
"""
plotter.py — NbodyPlotter: оркестратор plotting-инфраструктуры.

NbodyPlotter НЕ читает snapshots, НЕ считает density/sigma, НЕ центрирует halo
и не содержит кода отрисовки конкретных графиков. Он только:

- хранит PlotSettings и выбранный renderer;
- ведёт registry concrete plots (BasePlot-реализаций);
- делает deep-merge default_config + пользовательский config (без мутаций);
- валидирует данные по data_contract;
- вызывает render и возвращает созданные файлы;
- предоставляет introspection: available_plots() / describe().

Стандартные коллекции имён (просто списки, без type-hierarchy):
    ANALYSIS_PLOTS, ANIMATION_PLOTS, ALL_PLOTS
"""

from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Union

import matplotlib
matplotlib.use("Agg")

from base import BasePlot, format_contract


# ──────────────────────────────── Ошибки ────────────────────────────────────

class UnknownPlotError(KeyError):
    pass


class DuplicatePlotError(ValueError):
    pass


class UnsupportedRendererError(ValueError):
    pass


SUPPORTED_RENDERERS = ("matplotlib",)


# ─────────────────────── Стандартные коллекции plots ────────────────────────

ANALYSIS_PLOTS = ["density", "log_slope", "sigma_v", "interactions_radial"]
COMPARE_PLOTS = ["density_compare", "log_slope_compare", "sigma_v_compare",
                 "core_density_vs_sigma"]
ANIMATION_PLOTS = ["particles_2d", "particles_3d"]
ALL_PLOTS = ANALYSIS_PLOTS + COMPARE_PLOTS + ANIMATION_PLOTS


# ───────────────────────────────── helpers ──────────────────────────────────

def deep_merge(base: Mapping[str, Any], update: Optional[Mapping[str, Any]]) -> Dict[str, Any]:
    """Deep-merge без мутации входных словарей. update имеет приоритет."""
    out = copy.deepcopy(dict(base))
    if not update:
        return out
    for key, value in update.items():
        if isinstance(value, Mapping) and isinstance(out.get(key), dict):
            out[key] = deep_merge(out[key], value)
        else:
            out[key] = copy.deepcopy(value)
    return out

# ─────────────────────────────── NbodyPlotter ───────────────────────────────

class NbodyPlotter:
    """
    Оркестратор. Не привязан к конкретному run: render() получает plot-ready
    данные, output_dir передаётся интеграционным слоем.
    """

    def __init__(self, settings=None, renderer: str = "matplotlib",
                 output_dir: Union[str, Path, None] = None):
        # settings — PlotSettings (ленивый импорт против циклических зависимостей)
        if settings is None:
            from settings import PlotSettings
            settings = PlotSettings()
        if renderer not in SUPPORTED_RENDERERS:
            raise UnsupportedRendererError(
                f"renderer '{renderer}' is not supported. "
                f"Available renderers: {SUPPORTED_RENDERERS}")
        self.renderer = renderer
        self.settings = settings
        self.output_dir = Path(output_dir) if output_dir else None
        self._registry: Dict[str, BasePlot] = {}
        # Глобальная визуальная политика применяется централизованно один раз.
        self.settings.apply()

    # ─────────────────────────────── registry ───────────────────────────────

    def register(self, plot: Union[type, BasePlot], name: Optional[str] = None) -> BasePlot:
        """
        Зарегистрировать concrete plot (класс или готовый экземпляр).
        Класс будет инстанцирован с текущими PlotSettings.
        """
        if isinstance(plot, type) and issubclass(plot, BasePlot):
            instance = plot(self.settings)
        elif isinstance(plot, BasePlot):
            instance = plot
        else:
            raise TypeError(
                f"register() expects a BasePlot class/instance, got {type(plot)}")
        key = name or instance.name
        if not key:
            raise ValueError("Plot has empty name and no explicit name given")
        if key in self._registry:
            raise DuplicatePlotError(
                f"Plot '{key}' is already registered "
                f"({type(self._registry[key]).__name__})")
        self._registry[key] = instance
        return instance

    def register_defaults(self) -> "NbodyPlotter":
        """Зарегистрировать все стандартные production-plots проекта."""
        from analysis_plots import ANALYSIS_PLOT_CLASSES, COMPARE_PLOT_CLASSES
        from animation_plots import ANIMATION_PLOT_CLASSES
        for cls in (ANALYSIS_PLOT_CLASSES + COMPARE_PLOT_CLASSES
                    + ANIMATION_PLOT_CLASSES):
            self.register(cls)
        return self

    def get(self, name: str) -> BasePlot:
        try:
            return self._registry[name]
        except KeyError:
            raise UnknownPlotError(
                f"Unknown plot '{name}'. Available plots: {self.available_plots()}")

    def available_plots(self) -> List[str]:
        return sorted(self._registry.keys())

    # ────────────────────────────── introspection ──────────────────────────

    def describe(self, name: Optional[str] = None) -> str:
        """
        Человекочитаемое описание plot'а: что рисует, какие данные ждёт
        (data_contract), стандартный config. Для AI и людей.
        """
        if name is None:
            names = self.available_plots()
            header = (f"NbodyPlotter registry ({len(names)} plots, "
                      f"renderer='{self.renderer}'):\n  " +
                      "\n  ".join(f"- {n}" for n in names))
            blocks = [self.describe(n) for n in names]
            return header + "\n\n" + "\n\n".join(blocks)

        plot = self.get(name)
        cfg_str = json.dumps(plot.default_config, indent=2,
                             ensure_ascii=False, default=str)
        return (
            f"[{plot.name}]  ({type(plot).__name__})\n"
            f"Description:\n  {plot.description}\n"
            f"Data contract:\n{format_contract(plot.data_contract)}\n"
            f"Default config:\n{cfg_str}"
        )

    # ─────────────────────────────── execution ─────────────────────────────

    def make_plot(self, name: str, data: Mapping[str, Any],
                  config: Optional[Mapping[str, Any]] = None,
                  output_dir: Union[str, Path, None] = None) -> List[Path]:
        """
        Построить один plot:
          1. resolve config = deep_merge(default_config, config) без мутаций;
          2. определить итоговый путь файла (filename/output_dir);
          3. validate_data(data) по data_contract;
          4. render(data, resolved_config).
        Возвращает список созданных файлов.
        """
        plot = self.get(name)
        resolved = deep_merge(plot.default_config, config)

        outdir = Path(output_dir or resolved.get("output_dir")
                      or self.output_dir or ".")
        filename = Path(resolved.get("filename") or f"{name}.{self.settings.save_format}")
        save_path = filename if filename.is_absolute() else outdir / filename
        resolved["filename"] = str(save_path)
        save_path.parent.mkdir(parents=True, exist_ok=True)

        plot.validate_data(data)
        result = plot.render(data, resolved)

        if isinstance(result, (list, tuple)):
            return [Path(p) for p in result]
        return [Path(result)]

    def make_plots(self, jobs: Mapping[str, Mapping[str, Any]],
                   output_dir: Union[str, Path, None] = None) -> Dict[str, List[Path]]:
        """
        Batch-запуск нескольких plots.
        jobs = {plot_name: {"data": {...}, "config": {...} | None}, ...}
        """
        results: Dict[str, List[Path]] = {}
        for name, job in jobs.items():
            results[name] = self.make_plot(
                name, job.get("data"), job.get("config"), output_dir=output_dir)
        return results


def create_plotter(settings=None, output_dir=None) -> NbodyPlotter:
    """Удобная фабрика: NbodyPlotter со всеми стандартными plots."""
    plotter = NbodyPlotter(settings=settings, renderer="matplotlib",
                           output_dir=output_dir)
    plotter.register_defaults()
    return plotter

