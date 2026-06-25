#!/usr/bin/env python3
"""
Научный стиль графиков.
Универсальный конфиг: цвета, шрифты, размеры, темы.
Не привязан к конкретному эксперименту.

Использование:
    from plot_config import setup, apply, save, COLORS, SIZES
    setup()
    fig, ax = plt.subplots(figsize=SIZES.page)
    ax.plot(x, y, color=COLORS.palette[0], lw=1.5)
    apply(ax, xlabel="r", ylabel=r"$\\rho$")
    save(fig, "plot.png")
"""

import matplotlib as mpl
import matplotlib.pyplot as plt
from pathlib import Path


# ─── rcParams по умолчанию (применяются setup()) ────────────────────────────

DEFAULT_RC = {
    # Шрифты
    "font.family":        "sans-serif",
    "font.sans-serif":   ["DejaVu Sans", "Arial", "Helvetica"],
    "font.size":         10,
    "axes.labelsize":    12,
    "axes.titlesize":    13,
    "xtick.labelsize":   10,
    "ytick.labelsize":   10,
    "legend.fontsize":   10,
    # Тики
    "xtick.direction":   "in",
    "ytick.direction":   "in",
    "xtick.top":         True,
    "ytick.right":       True,
    # Сетка
    "axes.grid":         False,
    # Сохранение
    "savefig.dpi":       300,
    "savefig.format":    "png",
    "savefig.bbox":      "tight",
    "savefig.pad_inches": 0.05,
}


# ─── Наборы цветов (не привязаны к моделям) ─────────────────────────────────

class COLORS:
    """
    Палитры для любых графиков. Без привязки к конкретной физике.

    COLORS.palette[0], COLORS.palette[1], …     — основной набор (10 цветов)
    COLORS.pastel[0], …                          — пастельные
    COLORS.sequential[0], …                      — последовательные
    COLORS.diverging[0], …                       — дивергентные
    COLORS.mono[0], …                            — оттенки серого
    """

    # Основная палитра (ColorBrewer Set1 + расширение)
    palette = [
        "#E41A1C", "#377EB8", "#4DAF4A", "#984EA3", "#FF7F00",
        "#FFFF33", "#A65628", "#F781BF", "#66C2A5", "#999999",
    ]

    # Пастельная
    pastel = [
        "#FBB4AE", "#B3CDE3", "#CCEBC5", "#DECBE4", "#FED9A6",
        "#FFFFCC", "#E5D8BD", "#FDDAEC", "#F2F2F2",
    ]

    # Последовательная (светлый → тёмный)
    sequential = [
        "#F7FCFD", "#C6DBEF", "#6BAED6", "#3182BD", "#08519C",
    ]

    # Дивергентная (RdBu)
    diverging = [
        "#B2182B", "#D6604D", "#F4A582", "#FDDBC7", "#F7F7F7",
        "#D1E5F0", "#92C5DE", "#4393C3", "#2166AC",
    ]

    # Оттенки серого
    mono = [
        "#000000", "#333333", "#666666", "#999999", "#BBBBBB",
        "#DDDDDD", "#EEEEEE", "#F5F5F5",
    ]


# ─── Типовые размеры фигур (дюймы) ──────────────────────────────────────────

SIZES = {
    "tiny":      (2.5,  2.0),
    "column":    (3.5,  2.5),
    "page":      (7.0,  5.0),
    "wide":      (8.0,  4.5),
    "square":    (5.0,  5.0),
    "presentation": (10.0, 6.0),
}


# ─── Стили линий и маркеров ─────────────────────────────────────────────────

LINE_STYLES = ["-", "--", "-.", ":", (0, (3, 1, 1, 1))]
MARKERS    = ["o", "s", "^", "D", "v", "p", "*", "h"]


# ─── Основные функции ───────────────────────────────────────────────────────

_initialized = False


def setup(overrides=None):
    """
    Применить научный стиль. Опционально — переопределить отдельные rcParams.

    Parameters
    ----------
    overrides : dict or None
        Словарь rcParams для переопределения, например:
        {"font.size": 12, "savefig.dpi": 600}
    """
    global _initialized
    rc = dict(DEFAULT_RC)
    if overrides:
        rc.update(overrides)
    mpl.rcParams.update(rc)
    _initialized = True


def apply(ax, title=None, xlabel=None, ylabel=None,
          xscale=None, yscale=None, xlim=None, ylim=None,
          grid=False, legend=False):
    """
    Применить базовое оформление к axes.
    """
    if title:
        ax.set_title(title)
    if xlabel:
        ax.set_xlabel(xlabel)
    if ylabel:
        ax.set_ylabel(ylabel)
    if xscale:
        ax.set_xscale(xscale)
    if yscale:
        ax.set_yscale(yscale)
    if xlim:
        ax.set_xlim(xlim)
    if ylim:
        ax.set_ylim(ylim)
    if grid:
        ax.grid(True, alpha=0.3)
    if legend:
        ax.legend() if legend is True else ax.legend(**legend)


def save(fig, path, formats=None, dpi=None):
    """
    Сохранить фигуру.

    Parameters
    ----------
    fig : Figure
    path : str or Path
    formats : list[str], optional
        ["png"], ["pdf"], ["png", "svg"]. По умолчанию из расширения path.
    dpi : int, optional
        По умолчанию из rcParams (300).
    """
    path = Path(path)
    if formats is None:
        formats = [path.suffix.lstrip(".") or "png"]
    for fmt in formats:
        out = path.with_suffix(f".{fmt}")
        fig.savefig(out, dpi=dpi)
        print(f"  → {out}")


# Авто-инициализация при импорте
setup()