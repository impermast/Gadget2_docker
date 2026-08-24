#!/usr/bin/env python3
"""
settings.py — ЕДИНЫЙ модуль визуальной политики проекта.

Поглотил бывший plot_config.py. Здесь теперь всё, что относится к оформлению:

1. Стиль-данные и matplotlib-механика: COLORS, SIZES, STYLE, setup(),
   apply(ax, ...), save(fig, path) — бывшее содержимое plot_config.py.
2. RunPaths        — пути конкретного simulation run (данные симуляции).
3. SimulationInfo  — базовая информация о симуляции (метаданные).
4. PlotSettings    — публичный фасад глобальной визуальной политики:
     логические настройки (font_size, grid_enabled, view_3d, ...) ->
     централизованно в rcParams через setup(). NbodyPlotter применяет
     PlotSettings один раз при создании; concrete plots используют
     settings.style_axis()/settings.save_figure().

Никаких других модулей стиля в проекте нет: все оформление — здесь
(прямые импорты COLORS/SIZES/apply/save из settings.py допустимы для
разовых скриптов, но новый plotting должен идти через PlotSettings).
"""

from __future__ import annotations

import glob
import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Optional, Tuple

import matplotlib as mpl
import matplotlib.pyplot as plt
from cycler import cycler


# ══════════════════════════ Стиль-данные (ex plot_config) ══════════════════

class AttrDict(dict):
    """Словарь, который поддерживает и SIZES['page'], и SIZES.page."""
    def __getattr__(self, name):
        try:
            return self[name]
        except KeyError as exc:
            raise AttributeError(name) from exc


def _deep_update(base, update):
    for key, value in update.items():
        if isinstance(value, dict) and isinstance(base.get(key), dict):
            _deep_update(base[key], value)
        else:
            base[key] = value
    return base


class COLORS:
    """Палитры: COLORS.palette[0..9], .pastel, .sequential, .diverging, .mono."""

    palette = [
        "#E41A1C",  # red
        "#377EB8",  # blue
        "#4DAF4A",  # green
        "#984EA3",  # purple
        "#FF7F00",  # orange
        "#A65628",  # brown
        "#F781BF",  # pink
        "#66C2A5",  # teal
        "#999999",  # grey
        "#000000",  # black
    ]
    pastel = [
        "#FBB4AE", "#B3CDE3", "#CCEBC5", "#DECBE4", "#FED9A6",
        "#FFFFCC", "#E5D8BD", "#FDDAEC", "#F2F2F2",
    ]
    sequential = [
        "#F7FCFD", "#C6DBEF", "#6BAED6", "#3182BD", "#08519C",
    ]
    diverging = [
        "#B2182B", "#D6604D", "#F4A582", "#FDDBC7", "#F7F7F7",
        "#D1E5F0", "#92C5DE", "#4393C3", "#2166AC",
    ]
    mono = [
        "#000000", "#222222", "#444444", "#666666",
        "#888888", "#AAAAAA", "#CCCCCC", "#EEEEEE",
    ]


SIZES = AttrDict({
    "tiny":         (2.5, 2.0),
    "column":       (3.5, 2.5),
    "page":         (7.0, 5.0),
    "page_tall":    (7.0, 6.0),
    "wide":         (8.0, 4.5),
    "square":       (5.0, 5.0),
    "presentation": (10.0, 6.0),
})

LINE_STYLES = ["-", "--", "-.", ":", (0, (3, 1, 1, 1))]
MARKERS = ["o", "s", "^", "D", "v", "p", "*", "h"]

# Глобальный STYLE-словарь (низкоуровневые параметры оформления).
STYLE = {
    "font": {
        "family": "sans-serif",
        "sans_serif": ["DejaVu Sans", "Arial", "Helvetica"],
        "size": 10,
        "labelsize": 12,
        "titlesize": 13,
        "ticksize": 11,
        "legendsize": 10,
        "mathtext": "dejavusans",
    },
    "axes": {
        "linewidth": 1.0,
        "labelpad": 5,
        "titlepad": 6,
        "facecolor": "white",
        "axisbelow": True,
    },
    "ticks": {
        "direction": "in",
        "top": True,
        "right": True,
        "major_size": 5.5,
        "minor_size": 3.0,
        "major_width": 0.95,
        "minor_width": 0.75,
        "minor_visible": True,
    },
    "lines": {
        "linewidth": 1.6,
        "linewidth_main": 2.0,
        "linewidth_fit": 1.9,
        "markersize": 4.5,
    },
    "legend": {
        "frameon": False,
        "edgecolor": "none",
        "fancybox": False,
        "handlelength": 2.4,
        "handletextpad": 0.7,
        "borderaxespad": 0.4,
        "labelspacing": 0.45,
    },
    "grid": {
        "enabled": True,
        "which": "major",
        "axis": "both",
        "color": "0.86",
        "linewidth": 0.55,
        "alpha": 0.45,
        "minor_enabled": False,
        "minor_color": "0.92",
        "minor_linewidth": 0.35,
        "minor_alpha": 0.25,
    },
    "savefig": {
        "dpi": 300,
        "format": "png",
        "bbox_inches": "tight",
        "pad_inches": 0.045,
    },
}


# ═══════════════════ rcParams-механика и helpers (ex plot_config) ═══════════

def _make_rc():
    return {
        # Шрифты
        "font.family": STYLE["font"]["family"],
        "font.sans-serif": STYLE["font"]["sans_serif"],
        "font.size": STYLE["font"]["size"],
        "axes.labelsize": STYLE["font"]["labelsize"],
        "axes.titlesize": STYLE["font"]["titlesize"],
        "xtick.labelsize": STYLE["font"]["ticksize"],
        "ytick.labelsize": STYLE["font"]["ticksize"],
        "legend.fontsize": STYLE["font"]["legendsize"],
        "mathtext.fontset": STYLE["font"]["mathtext"],
        # Оси
        "axes.linewidth": STYLE["axes"]["linewidth"],
        "axes.labelpad": STYLE["axes"]["labelpad"],
        "axes.titlepad": STYLE["axes"]["titlepad"],
        "axes.facecolor": STYLE["axes"]["facecolor"],
        "axes.axisbelow": STYLE["axes"]["axisbelow"],
        # Тики
        "xtick.direction": STYLE["ticks"]["direction"],
        "ytick.direction": STYLE["ticks"]["direction"],
        "xtick.top": STYLE["ticks"]["top"],
        "ytick.right": STYLE["ticks"]["right"],
        "xtick.major.size": STYLE["ticks"]["major_size"],
        "ytick.major.size": STYLE["ticks"]["major_size"],
        "xtick.minor.size": STYLE["ticks"]["minor_size"],
        "ytick.minor.size": STYLE["ticks"]["minor_size"],
        "xtick.major.width": STYLE["ticks"]["major_width"],
        "ytick.major.width": STYLE["ticks"]["major_width"],
        "xtick.minor.width": STYLE["ticks"]["minor_width"],
        "ytick.minor.width": STYLE["ticks"]["minor_width"],
        # Линии
        "lines.linewidth": STYLE["lines"]["linewidth"],
        "lines.markersize": STYLE["lines"]["markersize"],
        "axes.prop_cycle": cycler(color=COLORS.palette),
        # Легенда
        "legend.frameon": STYLE["legend"]["frameon"],
        "legend.edgecolor": STYLE["legend"]["edgecolor"],
        "legend.fancybox": STYLE["legend"]["fancybox"],
        # Сетку управляет apply(), не rcParams
        "axes.grid": False,
        # Сохранение
        "savefig.dpi": STYLE["savefig"]["dpi"],
        "savefig.format": STYLE["savefig"]["format"],
        "savefig.bbox": STYLE["savefig"]["bbox_inches"],
        "savefig.pad_inches": STYLE["savefig"]["pad_inches"],
    }


DEFAULT_RC = _make_rc()
_initialized = False


def setup(overrides=None, style_overrides=None):
    """
    Применить стиль к matplotlib.

    overrides : dict — прямые переопределения rcParams.
    style_overrides : dict — переопределения STYLE, напр.
        {"grid": {"enabled": False}, "font": {"size": 12}}
    """
    global _initialized, DEFAULT_RC

    if style_overrides:
        _deep_update(STYLE, style_overrides)

    rc = _make_rc()
    if overrides:
        rc.update(overrides)

    mpl.rcParams.update(rc)
    DEFAULT_RC = dict(rc)
    _initialized = True


def _apply_limits(ax, xlim=None, ylim=None):
    if xlim is not None:
        ax.set_xlim(*xlim)
    if ylim is not None:
        ax.set_ylim(*ylim)


def _apply_grid(ax, grid=None):
    """grid: None -> из STYLE; bool; dict -> локальное переопределение."""
    g = dict(STYLE["grid"])
    if isinstance(grid, dict):
        g.update(grid)
        enabled = True
    elif grid is None:
        enabled = g["enabled"]
    else:
        enabled = bool(grid)

    ax.grid(False, which="both")
    if not enabled:
        return

    ax.set_axisbelow(STYLE["axes"]["axisbelow"])
    ax.grid(True, which=g["which"], axis=g["axis"], color=g["color"],
            linewidth=g["linewidth"], alpha=g["alpha"])
    if g["minor_enabled"]:
        ax.grid(True, which="minor", axis=g["axis"], color=g["minor_color"],
                linewidth=g["minor_linewidth"], alpha=g["minor_alpha"])


def apply(ax, title=None, xlabel=None, ylabel=None, xscale=None, yscale=None,
          xlim=None, ylim=None, grid=None, legend=False):
    """Оформить axes: заголовок, подписи, масштабы, лимиты, сетка, легенда."""
    if title is not None:
        ax.set_title(title)
    if xlabel is not None:
        ax.set_xlabel(xlabel)
    if ylabel is not None:
        ax.set_ylabel(ylabel)
    if xscale is not None:
        ax.set_xscale(xscale)
    if yscale is not None:
        ax.set_yscale(yscale)

    _apply_limits(ax, xlim=xlim, ylim=ylim)

    if STYLE["ticks"]["minor_visible"]:
        ax.minorticks_on()

    _apply_grid(ax, grid=grid)

    if legend:
        legend_kwargs = dict(STYLE["legend"])
        if isinstance(legend, dict):
            legend_kwargs.update(legend)
        ax.legend(**legend_kwargs)


def save(fig, path, formats=None, dpi=None):
    """Сохранить фигуру. formats: ["png"], ["pdf"], ...; по умолчанию из path."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)

    if formats is None:
        suffix = path.suffix.lstrip(".")
        formats = [suffix if suffix else STYLE["savefig"]["format"]]

    for fmt in formats:
        out = path.with_suffix(f".{fmt}")
        fig.savefig(
            out,
            dpi=dpi or STYLE["savefig"]["dpi"],
            bbox_inches=STYLE["savefig"]["bbox_inches"],
            pad_inches=STYLE["savefig"]["pad_inches"],
        )
        print(f"  → {out}")


# ═══════════════════════════════ RunPaths ═══════════════════════════════════

@dataclass
class RunPaths:
    """
    Пути конкретного run. Относится к ДАННЫМ СИМУЛЯЦИИ, а не к графикам.

    Стандартная раскладка run-каталога:
        <root>/output/   — HDF5 snapshots
        <root>/plots/    — результаты plotting/анализа
        <root>/configs/  — копии параметров запуска
    """

    root: Path
    snapshot_subdir: str = "output"
    plots_subdir: str = "plots"
    configs_subdir: str = "configs"

    def __post_init__(self):
        self.root = Path(self.root)

    @property
    def output(self) -> Path:
        return self.root / self.snapshot_subdir

    @property
    def plots(self) -> Path:
        return self.root / self.plots_subdir

    @property
    def configs(self) -> Path:
        return self.root / self.configs_subdir

    def list_snapshots(self) -> list:
        files = sorted(glob.glob(str(self.output / "snapshot*.hdf5")))
        if not files:
            raise FileNotFoundError(f"No HDF5 snapshots found in {self.output}")
        return files

    def latest_snapshot(self) -> Path:
        def number(p: str) -> int:
            m = re.search(r"snapshot_?(\d+)\.hdf5$", os.path.basename(p))
            return int(m.group(1)) if m else -1

        return Path(sorted(self.list_snapshots(), key=number)[-1])

    def snapshot(self, number: int) -> Path:
        return self.output / f"snapshot_{number:03d}.hdf5"


# ═══════════════════════════ SimulationInfo ═════════════════════════════════

@dataclass
class SimulationInfo:
    """Базовая информация о симуляции. Не runtime-state, только метаданные."""

    name: str
    model: str = "unknown"                 # "CDM" | "SIDM" | ...
    n_particles: Optional[int] = None
    particle_type: int = 3
    cross_section: Optional[float] = None  # SIDM sigma [cm^2/g]
    time: Optional[float] = None           # кодовые единицы времени
    units: Dict[str, str] = field(default_factory=lambda: {
        "length": "kpc",
        "velocity": "km/s",
        "time_to_Gyr": "0.9777923542981722",
    })
    metadata: Dict[str, object] = field(default_factory=dict)

    @classmethod
    def from_snapshot(cls, snapshot_path, name: Optional[str] = None,
                      model: Optional[str] = None,
                      particle_type: int = 3) -> "SimulationInfo":
        """Прочитать базовую информацию прямо из заголовка snapshot."""
        import h5py

        snapshot_path = Path(snapshot_path)
        with h5py.File(snapshot_path, "r") as f:
            head = f["Header"].attrs
            time = float(head.get("Time", 0.0))
            sigma = float(head.get("DM_InteractionCrossSection", 0.0))
            gname = f"PartType{particle_type}"
            n = int(f[gname]["Coordinates"].shape[0]) if gname in f else None

        if model is None:
            model = "SIDM" if sigma and sigma > 0 else "CDM"
        if name is None:
            name = snapshot_path.parent.parent.name
        return cls(
            name=name,
            model=model,
            n_particles=n,
            particle_type=particle_type,
            cross_section=sigma if sigma > 0 else None,
            time=time,
        )


# ═════════════════════════════ PlotSettings ═════════════════════════════════

@dataclass
class PlotSettings:
    """
    Глобальная визуальная политика проекта (публичный фасад).

    Один объект задаёт то, что обычно одинаково для многих графиков.
    Настройки КОНКРЕТНОГО графика живут в его собственном default_config
    (см. BasePlot). Логические ключи (font_size, grid_enabled, view_3d, ...)
    переводятся в matplotlib-специфику только внутри apply().
    """

    # Шрифты
    font_family: str = STYLE["font"]["family"]
    font_family_list: Tuple[str, ...] = tuple(STYLE["font"]["sans_serif"])
    font_size: int = STYLE["font"]["size"]
    label_size: int = STYLE["font"]["labelsize"]
    title_size: int = STYLE["font"]["titlesize"]
    tick_label_size: int = STYLE["font"]["ticksize"]
    legend_font_size: int = STYLE["font"]["legendsize"]
    mathtext_fontset: str = STYLE["font"]["mathtext"]

    # Палитры
    palette: Tuple[str, ...] = tuple(COLORS.palette)
    sequential_colors: Tuple[str, ...] = tuple(COLORS.sequential)
    diverging_colors: Tuple[str, ...] = tuple(COLORS.diverging)
    mono_colors: Tuple[str, ...] = tuple(COLORS.mono)
    line_styles: Tuple[str, ...] = tuple(LINE_STYLES)
    markers: Tuple[str, ...] = tuple(MARKERS)

    # Линии / маркеры
    line_width: float = STYLE["lines"]["linewidth"]
    line_width_main: float = STYLE["lines"]["linewidth_main"]
    line_width_fit: float = STYLE["lines"]["linewidth_fit"]
    marker_size: float = STYLE["lines"]["markersize"]

    # Оси
    axes_linewidth: float = STYLE["axes"]["linewidth"]
    label_pad: float = STYLE["axes"]["labelpad"]
    title_pad: float = STYLE["axes"]["titlepad"]
    axis_below: bool = STYLE["axes"]["axisbelow"]

    # Тики
    tick_direction: str = STYLE["ticks"]["direction"]
    ticks_on_top: bool = STYLE["ticks"]["top"]
    ticks_on_right: bool = STYLE["ticks"]["right"]
    major_tick_size: float = STYLE["ticks"]["major_size"]
    minor_tick_size: float = STYLE["ticks"]["minor_size"]
    major_tick_width: float = STYLE["ticks"]["major_width"]
    minor_tick_width: float = STYLE["ticks"]["minor_width"]
    minor_ticks_visible: bool = STYLE["ticks"]["minor_visible"]

    # Сетка
    grid_enabled: bool = STYLE["grid"]["enabled"]
    grid_which: str = STYLE["grid"]["which"]
    grid_axis: str = STYLE["grid"]["axis"]
    grid_color: str = STYLE["grid"]["color"]
    grid_line_width: float = STYLE["grid"]["linewidth"]
    grid_alpha: float = STYLE["grid"]["alpha"]

    # Легенда
    legend_frame_on: bool = STYLE["legend"]["frameon"]
    legend_handle_length: float = STYLE["legend"]["handlelength"]

    # Размеры фигур (логические пресеты)
    figure_sizes: Dict[str, Tuple[float, float]] = field(
        default_factory=lambda: dict(SIZES))

    # Сохранение
    save_dpi: int = STYLE["savefig"]["dpi"]
    save_format: str = STYLE["savefig"]["format"]
    save_bounding_box: str = STYLE["savefig"]["bbox_inches"]
    save_pad_inches: float = STYLE["savefig"]["pad_inches"]

    # Общие 3D defaults (камера/фон; детали — в default_config конкретных 3D plots)
    view_3d: Dict[str, float] = field(default_factory=lambda: {"elev": 30, "azim": -42})
    figure_size_3d: Tuple[float, float] = (8, 8)
    dpi_3d: int = 150
    background_3d: str = "#050507"

    # ───────────────────────── применение к backend ────────────────────────

    def apply(self) -> None:
        """
        Применить глобальную политику к текущему backend'у (matplotlib):
        централизованно через rcParams (setup из этого же модуля).
        """
        style_overrides = {
            "font": {
                "family": self.font_family,
                "sans_serif": list(self.font_family_list),
                "size": self.font_size,
                "labelsize": self.label_size,
                "titlesize": self.title_size,
                "ticksize": self.tick_label_size,
                "legendsize": self.legend_font_size,
                "mathtext": self.mathtext_fontset,
            },
            "axes": {
                "linewidth": self.axes_linewidth,
                "labelpad": self.label_pad,
                "titlepad": self.title_pad,
                "axisbelow": self.axis_below,
            },
            "ticks": {
                "direction": self.tick_direction,
                "top": self.ticks_on_top,
                "right": self.ticks_on_right,
                "major_size": self.major_tick_size,
                "minor_size": self.minor_tick_size,
                "major_width": self.major_tick_width,
                "minor_width": self.minor_tick_width,
                "minor_visible": self.minor_ticks_visible,
            },
            "lines": {
                "linewidth": self.line_width,
                "linewidth_main": self.line_width_main,
                "linewidth_fit": self.line_width_fit,
                "markersize": self.marker_size,
            },
            "legend": {
                "frameon": self.legend_frame_on,
                "handlelength": self.legend_handle_length,
            },
            "grid": {
                "enabled": self.grid_enabled,
                "which": self.grid_which,
                "axis": self.grid_axis,
                "color": self.grid_color,
                "linewidth": self.grid_line_width,
                "alpha": self.grid_alpha,
            },
            "savefig": {
                "dpi": self.save_dpi,
                "format": self.save_format,
                "bbox_inches": self.save_bounding_box,
                "pad_inches": self.save_pad_inches,
            },
        }
        overrides = None
        if list(self.palette) != list(COLORS.palette):
            overrides = {"axes.prop_cycle": cycler(color=list(self.palette))}
        setup(overrides=overrides, style_overrides=style_overrides)

    # ─────────────────────────── общие helpers 2D ──────────────────────────

    def style_axis(self, ax, **kwargs) -> None:
        """Оформить axes согласно глобальной политике (обёртка apply())."""
        apply(ax, **kwargs)

    def save_figure(self, fig, path, formats=None, dpi=None) -> Path:
        """Сохранить фигуру согласно политике сохранения (обёртка save())."""
        save(fig, path, formats=formats, dpi=dpi)
        return Path(path)

    def figsize(self, key: str) -> Tuple[float, float]:
        try:
            return tuple(self.figure_sizes[key])
        except KeyError:
            raise KeyError(
                f"Unknown figsize preset '{key}'. Available: {sorted(self.figure_sizes)}")
