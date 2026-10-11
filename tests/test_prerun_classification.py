"""Regression tests for partial-series classification."""

from types import SimpleNamespace

import pytest

from analysis.loaders.prerun import classify_series


pytestmark = pytest.mark.math


def _metric(time, step, *, ca=0.8, thickness=0.7, support=0.2):
    return SimpleNamespace(
        time=time,
        ca_r5=ca,
        z_rms_over_R_rms_r5=thickness,
        vrot_over_sigma_r5=support,
        rho_core_r2=1.0,
        nearest_systemstep=step,
    )


def test_zero_initial_step_is_ignored_for_pathology_classification():
    verdict, notes = classify_series([
        _metric(0.0, 0.0),
        _metric(1.0, 0.0012207),
        _metric(2.0, 0.002),
    ])

    assert verdict == "ambiguous-partial-series"
    assert any("min=0.00122" in note for note in notes)


def test_positive_sub_microstep_still_marks_pathology():
    verdict, notes = classify_series([
        _metric(0.0, 0.001),
        _metric(1.0, 0.0000005),
        _metric(2.0, 0.0000008),
    ])

    assert verdict == "no-disk-before-pathology"
    assert any("min=5e-07" in note for note in notes)
