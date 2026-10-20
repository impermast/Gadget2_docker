"""Smoke-рендер реестра (маркер `render`): каждый plot рисует на фикстуре."""
from __future__ import annotations

import os
import sys
import warnings
from pathlib import Path

import pytest

pytestmark = pytest.mark.render

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS_DIR = REPO_ROOT / "nbody" / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import synth_snap  # noqa: E402
from analysis import loaders  # noqa: E402
from analysis import plots as _plots  # noqa: E402 (триггерит @register)
from analysis.plotter import NbodyPlotter  # noqa: E402
from analysis.registry import by_block, registry  # noqa: E402
from analysis.style import PlotSettings  # noqa: E402


@pytest.fixture(scope="module")
def prof(snap_full):
    return loaders.prepare_profile_data(snap_full, rcore=2.0)


@pytest.fixture(scope="module")
def parts(snap_full):
    return loaders.prepare_particle_snapshot(snap_full)


def _render(name, data, tmp_path, config=None):
    os.environ["NBODY_ANALYSIS_ROOT"] = str(tmp_path / "analysis")
    plotter = NbodyPlotter(PlotSettings(), output_dir=tmp_path / "out")
    plotter.register_defaults()
    outs = plotter.make_plot(name, data, config=config or {})
    assert len(outs) == 1
    out = outs[0]
    assert out.exists() and out.stat().st_size > 1000, f"{name}: пустой выход"
    return out


def test_core_plots_render_on_fixture(prof, parts, tmp_path):
    """Блок core: каждый plot рисует на синтетическом профиле/частицах."""
    import numpy as np
    pats = dict(parts)
    pats["positions"] = np.asarray(pats["positions"])[None, :, :]
    pats["times"] = np.asarray([pats.get("time", 1.0)], dtype=float)
    if pats.get("masses") is not None:
        pats["masses"] = np.asarray(pats["masses"])[None, :]
    for spec in by_block("core"):
        if spec.name in ("particles_2d", "particles_3d"):
            data = pats
        elif spec.name == "disk_edgeon":
            data = parts
        else:
            data = prof
        _render(spec.name, data, tmp_path / spec.name)


def test_series_evolution_handles_zero_interactions(tmp_path):
    """CDM series with NI=0 remains explicit and warning-free."""
    import numpy as np

    data = {
        "time": np.asarray([0.0, 1.0, 2.0]),
        "rho_core_r2": np.asarray([0.0022, 0.0021, 0.0020]),
        "ca_r5": np.asarray([0.995, 0.994, 0.993]),
        "z_rms_over_R_rms_r5": np.asarray([0.705, 0.706, 0.707]),
        "mean_vphi_r5": np.asarray([8.0, 7.9, 7.8]),
        "ninteractions_total": np.zeros(3),
    }
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        _render("series_evolution", data, tmp_path)
    assert not any("no positive values" in str(w.message).lower() for w in caught)


def test_registry_describe_and_markdown_cover_all():
    """describe()/to_markdown() покрывают все имена (ИИ-путеводитель)."""
    from analysis.registry import describe, to_markdown
    md = to_markdown()
    for name in registry():
        assert name in md, f"{name} нет в REGISTRY.md"
        assert name in describe(name)


def _campaign_jobs(snap_full):
    """Данные для каждого campaigns-plot ровно по его контракту.

    Собирается ТЕМИ ЖЕ лоадерами, что и runner'ы (registry spec.data_source),
    поэтому расхождение контракта plot'а с реально поставляемыми данными падает
    здесь, а не в docker-прогоне.
    """
    import numpy as np
    prof = loaders.prepare_profile_data(snap_full, rcore=2.0)
    visual = loaders.prepare_visual_snapshot(snap_full)
    hxy, hxz = loaders.projection_histograms(visual, bins=48, lim=12.0)
    phase, extent = loaders.phase_space_histogram(visual, rlim=12.0,
                                                  bins_r=24, bins_v=24)
    radii = np.logspace(np.log10(0.5), np.log10(12.0), 10)
    rad = loaders.radial_morphology_profiles(visual, radii)
    rad["label"] = "A"
    rad_b = dict(rad, label="B")
    prof["label"] = "A"
    prof_b = dict(prof, label="B")
    labels = np.asarray(["A", "B"], dtype=object)
    t_snap = float(visual["time"])
    surface = {"labels": labels,
               "times": np.asarray([t_snap, t_snap]),
               "faceon": np.stack([hxy, hxy]),
               "edgeon": np.stack([hxz, hxz])}
    t = np.linspace(0.0, 1.0, 12)
    return {
        "density_compare": {"series": [prof, prof_b]},
        "log_slope_compare": {"series": [prof, prof_b]},
        "sigma_v_compare": {"series": [prof, prof_b]},
        "log_rho_compare": {"series": [prof, prof_b]},
        "rot_curve_compare": {"series": [prof, prof_b]},
        "core_density_vs_sigma": {"sigma": np.asarray([0.5, 2.0]),
                                  "rho_core": np.asarray([1.0, 0.5]),
                                  "labels": labels,
                                  "baseline_rho_core": 1.0,
                                  "baseline_label": "CDM"},
        "visual_morphology_montage": surface,
        "surface_density_residuals": surface,
        "morphology_profiles_compare": {"series": [rad, rad_b]},
        "phase_space_compare": {"labels": labels,
                                "phase": np.stack([phase, phase]),
                                "extent": np.asarray(extent)},
        "disk_dashboard": {"summary_labels": labels,
                           "ca_final": np.asarray([0.9, 0.7]),
                           "thickness_final": np.asarray([0.6, 0.4]),
                           "vrot_final": np.asarray([0.05, 0.30]),
                           "ninteractions_final": np.asarray([0.0, 1e3]),
                           "disk_score": np.asarray([0.0, 0.4])},
        "criteria_time_panel": {"series": [
            {"times": t, "ca": 0.9 - 0.1 * t, "thickness": 0.6 - 0.05 * t,
             "vrot_over_sigma": 0.05 + 0.1 * t, "label": "A"}]},
        "runaway_timestep_panel": {"series": [
            {"times": t, "ninteractions": np.arange(1.0, 13.0),
             "dt_min": 1e-4 / (1.0 + t), "label": "A"}]},
        "diag_eloss_vs_f": {"f_set": np.asarray([0.10, 0.25]),
                            "measured": np.asarray([0.19, 0.44]),
                            "labels": np.asarray(["D0.10", "D0.25"],
                                                 dtype=object)},
    }


def test_campaign_plots_render_on_fixture(snap_full, tmp_path):
    """Блок campaigns: каждый plot рисует по контракту (как в runner'ах)."""
    jobs = _campaign_jobs(snap_full)
    for spec in by_block("campaigns"):
        assert spec.name in jobs, f"{spec.name}: тест не готовит данные"
        _render(spec.name, jobs[spec.name], tmp_path / spec.name)
