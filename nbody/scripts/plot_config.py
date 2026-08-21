#!/usr/bin/env python3
"""
Научный стиль графиков.
Универсальный конфиг: цвета, шрифты, размеры, сетка, сохранение.

Использование:
    from plot_config import setup, apply, save, COLORS, SIZES
    setup()

    fig, ax = plt.subplots(figsize=SIZES["page"])
    ax.plot(x, y, color=COLORS.palette[0])
    apply(ax, xlabel="r", ylabel=r"$\\rho$", xscale="log", yscale="log")
    save(fig, "plot.png")
"""

import matplotlib as mpl
import matplotlib.pyplot as plt
from pathlib import Path
from cycler import cycler


# ─────────────────────────────── Вспомогательное ───────────────────────────

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


# ─────────────────────────────── Цвета ─────────────────────────────────────

class COLORS:
    """
    Палитры для любых графиков.

    COLORS.palette[0], COLORS.palette[1], ...
    COLORS.pastel[0], ...
    COLORS.sequential[0], ...
    COLORS.diverging[0], ...
    COLORS.mono[0], ...
    """

    # Основная палитра. Первые пять хорошо подходят под CDM/SIDM:
    # red, blue, green, purple, orange.
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


# ─────────────────────────────── Размеры фигур ─────────────────────────────

SIZES = AttrDict({
    "tiny":         (2.5, 2.0),
    "column":       (3.5, 2.5),
    "page":         (7.0, 5.0),
    "page_tall":    (7.0, 6.0),
    "wide":         (8.0, 4.5),
    "square":       (5.0, 5.0),
    "presentation": (10.0, 6.0),
})


# ─────────────────────────────── 3D Graph ──────────────────────────────────

GRAPH3D = {
    "figsize": (8, 8),
    "dpi": 150,
    "facecolor": "#050507",
    "background": "#050507",
    "pane_color": "#050507",
    "pane_alpha": 0.0,
    "scatter": {
        "cmap": "inferno",
        "s": 2.2,
        "alpha": 0.82,
        "edgecolors": "none",
    },
    "wireframe": {
        "color": "#D0D0D0",
        "linewidth": 1.1,
        "alpha": 0.22,
    },
    "labels": {
        "color": "#FFFFFF",
        "fontsize": 28,
        "weight": "bold",
    },
    "time_label": {
        "color": "#F2F2F2",
        "fontsize": 22,
    },
    "scale_bar": {
        "color": "#FFFFFF",
        "linewidth": 3.5,
        "alpha": 0.9,
        "tick_length": 3.5,
        "tick_linewidth": 2.0,
        "tick_alpha": 0.9,
        "label_fontsize": 18,
    },
    "view": {
        "elev": 30,
        "azim": -42,
    },
    "limits": {
        "percentile": 99,
        "factor": 1.02,
        "min_lim": 35,
    },
}


# ─────────────────────────────── Глобальный стиль ──────────────────────────

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

    # Главное: сетка стала слабой и управляемой.
    # Она помогает читать график, но не конкурирует с линиями.
    "grid": {
        "enabled": True,

        # Для научных графиков обычно лучше только major grid.
        # Minor grid на log-графиках часто создаёт визуальный шум.
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


LINE_STYLES = ["-", "--", "-.", ":", (0, (3, 1, 1, 1))]
MARKERS = ["o", "s", "^", "D", "v", "p", "*", "h"]


# ─────────────────────────────── rcParams ──────────────────────────────────

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

        # Сетку не включаем через rcParams.
        # Ей управляет apply(), иначе сложнее контролировать разные axes.
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
    Применить стиль.

    Parameters
    ----------
    overrides : dict or None
        Прямые переопределения matplotlib rcParams.

    style_overrides : dict or None
        Переопределения STYLE, например:
        {
            "grid": {"enabled": False},
            "font": {"size": 12}
        }
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


# ─────────────────────────────── Оформление axes ───────────────────────────

def _apply_limits(ax, xlim=None, ylim=None):
    if xlim is not None:
        ax.set_xlim(*xlim)
    if ylim is not None:
        ax.set_ylim(*ylim)


def _apply_grid(ax, grid=None):
    """
    grid:
        None  -> использовать STYLE["grid"]["enabled"]
        False -> выключить сетку
        True  -> включить сетку по STYLE["grid"]
        dict  -> локально переопределить STYLE["grid"]
    """
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

    ax.grid(
        True,
        which=g["which"],
        axis=g["axis"],
        color=g["color"],
        linewidth=g["linewidth"],
        alpha=g["alpha"],
    )

    if g["minor_enabled"]:
        ax.grid(
            True,
            which="minor",
            axis=g["axis"],
            color=g["minor_color"],
            linewidth=g["minor_linewidth"],
            alpha=g["minor_alpha"],
        )


def apply(
    ax,
    title=None,
    xlabel=None,
    ylabel=None,
    xscale=None,
    yscale=None,
    xlim=None,
    ylim=None,
    grid=None,
    legend=False,
):
    """
    Применить базовое оформление к axes.

    grid:
        None  -> использовать настройку из STYLE["grid"]["enabled"]
        False -> без сетки
        True  -> сетка из STYLE["grid"]
        dict  -> локальная настройка сетки

    legend:
        False -> не рисовать легенду
        True  -> легенда со STYLE["legend"]
        dict  -> легенда со STYLE["legend"] + локальные параметры
    """
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


# ─────────────────────────────── Сохранение ────────────────────────────────

def save(fig, path, formats=None, dpi=None):
    """
    Сохранить фигуру.

    Parameters
    ----------
    fig : Figure
    path : str or Path
    formats : list[str], optional
        Например ["png"], ["pdf"], ["png", "svg"].
        По умолчанию берётся расширение из path.
    dpi : int, optional
        По умолчанию STYLE["savefig"]["dpi"].
    """
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


# Авто-инициализация при импорте
setup()