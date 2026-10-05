"""Контракт plotter'а и реестра (маркер `math`): отказы на плохих входных данных.

Покрытие перенесено из удалённого plot_scripts/run_full_test.py (фазы A/B):
неподдерживаемый renderer, неизвестный plot, дубликат регистрации и негативные
проверки data contract (ошибка обязана называть имя plot'а).
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

pytestmark = pytest.mark.math

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS_DIR = REPO_ROOT / "nbody" / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from analysis import plots as _plots  # noqa: E402,F401 (триггерит @register)
from analysis.base import PlotValidationError  # noqa: E402
from analysis.plotter import (  # noqa: E402
    DuplicatePlotError,
    NbodyPlotter,
    UnknownPlotError,
    UnsupportedRendererError,
)
from analysis.registry import registry  # noqa: E402
from analysis.style import PlotSettings  # noqa: E402

BAD_CASES = [
    ("density", {"r": [[1.0, 2.0]] * 100, "rho": [1.0] * 100},
     "форма (N,2) вместо (R,)"),
    ("density", {"r": [1.0, 2.0]}, "нет обязательного поля 'rho'"),
    ("particles_3d", {"positions": [[[1.0, 2.0]]], "times": [0.0]},
     "последняя ось positions 2 вместо 3"),
    ("sigma_v", {"r": [1.0], "sigma_v": ["a"]}, "нечисловой dtype"),
]


def test_unsupported_renderer_rejected():
    with pytest.raises(UnsupportedRendererError):
        NbodyPlotter(renderer="plotly")


def test_unknown_plot_rejected():
    plotter = NbodyPlotter(PlotSettings())
    plotter.register_defaults()
    with pytest.raises(UnknownPlotError):
        plotter.get("no_such_plot")


def test_duplicate_registration_rejected():
    from analysis.plots.core import DensityPlot
    plotter = NbodyPlotter(PlotSettings())
    plotter.register_defaults()
    with pytest.raises(DuplicatePlotError):
        plotter.register(DensityPlot(PlotSettings()))


def test_registry_names_are_unique():
    names = [s.name for s in registry().values()]
    assert len(names) == len(set(names))


@pytest.mark.parametrize("plot_name,data,why", BAD_CASES)
def test_bad_data_fails_validation_and_names_plot(plot_name, data, why, tmp_path):
    plotter = NbodyPlotter(PlotSettings(), output_dir=tmp_path)
    plotter.register_defaults()
    with pytest.raises(PlotValidationError) as exc:
        plotter.make_plot(plot_name, data,
                          config={"filename": "_must_not_exist.png"},
                          output_dir=tmp_path)
    assert plot_name in str(exc.value), f"{why}: ошибка не называет plot"
    assert not (tmp_path / "_must_not_exist.png").exists()
