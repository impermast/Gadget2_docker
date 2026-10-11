"""Targeted tests for the independent dSIDM dissipation reference model."""

from __future__ import annotations

import csv
import hashlib
import math

import numpy as np
import pytest

from conference.dissipation_check import (
    RECORDED_BINARY_HASH,
    RECORDED_CONFIG_HASH,
    RECORDED_CONFIG_SH_HASH,
    RECORDED_FLAGS,
    RECORDED_OBJECT_HASH,
    RECORDED_SOURCE_HASH,
    build_validation_rows,
    calculate_interact_kick,
    default_output_path,
    pairwise_collision,
    source_audit_evidence,
    theoretical_loss_fraction,
    write_validation_csv,
)


pytestmark = pytest.mark.math


@pytest.mark.parametrize("d", [0.0, 0.1, 0.25, 0.5, 0.75, 1.0])
def test_zero_kick_matches_2d_minus_d2(d):
    measured = theoretical_loss_fraction([1.0, 0.0, 0.0], d, 0.0)
    assert measured == pytest.approx(2.0 * d - d * d, abs=2e-15)


def test_nonzero_kick_uses_full_formula_and_can_heat():
    # |v_rel|=1, D=.25 gives 2D-D^2=.4375; v0=.75 adds .5625 and therefore
    # makes the relative-energy loss negative.
    loss = theoretical_loss_fraction([1.0, 0.0, 0.0], 0.25, 0.75)
    assert loss == pytest.approx(0.4375 - 0.75**2)
    assert loss < 0.0
    assert theoretical_loss_fraction([1.0, 0.0, 0.0], 0.5, 0.2) == pytest.approx(0.71)


def test_zero_initial_relative_speed_is_undefined():
    assert math.isnan(theoretical_loss_fraction([0.0, 0.0, 0.0], 0.5, 0.0))


def test_unequal_mass_pair_conserves_momentum_with_scale_aware_tolerance():
    result = pairwise_collision(
        [1.5, -0.2, 0.4],
        [-0.25, 0.7, -0.1],
        2.0,
        5.0,
        0.5,
        0.0,
        direction=[0.0, 0.0, 1.0],
        position_1=[0.5, 0.0, 0.0],
        position_2=[-0.5, 0.0, 0.0],
    )
    scale = max(
        np.linalg.norm(result.momentum_before),
        (result.mass_1 + result.mass_2)
        * max(
            np.linalg.norm(result.velocity_1_before),
            np.linalg.norm(result.velocity_2_before),
            np.linalg.norm(result.velocity_1_after),
            np.linalg.norm(result.velocity_2_after),
        ),
        1.0,
    )
    assert result.momentum_residual <= 1e-13 + 1e-12 * scale
    assert np.allclose(result.relative_velocity_after[:2], [0.0, 0.0])
    assert result.relative_velocity_after[2] < 0.0
    assert np.linalg.norm(result.relative_velocity_after) == pytest.approx(
        0.5 * np.linalg.norm(result.relative_velocity_before)
    )


def test_kick_function_matches_source_sign_convention():
    kick, relative_after, direction = calculate_interact_kick(
        [1.0, 0.0, 0.0], 0.25, 0.75, direction=[0.0, 1.0, 0.0]
    )
    dmag = math.sqrt(0.75**2 + 0.75**2)
    assert np.allclose(direction, [0.0, 1.0, 0.0])
    assert np.allclose(kick, [0.5, 0.5 * dmag, 0.0])
    assert np.allclose(relative_after, [0.0, -dmag, 0.0])


def test_angular_momentum_measures_special_and_general_geometry():
    special = pairwise_collision(
        [0.5, 0.0, 0.0],
        [-0.5, 0.0, 0.0],
        1.0,
        1.0,
        0.5,
        direction=[1.0, 0.0, 0.0],
        position_1=[0.75, 0.0, 0.0],
        position_2=[-0.25, 0.0, 0.0],
    )
    general = pairwise_collision(
        [0.0, 0.5, 0.0],
        [0.0, -0.5, 0.0],
        1.0,
        1.0,
        0.5,
        direction=[0.0, 1.0, 0.0],
        position_1=[0.75, 0.0, 0.0],
        position_2=[-0.25, 0.0, 0.0],
    )
    # Collinear separation/impulse is a valid zero residual special case.
    assert special.angular_momentum_change == pytest.approx(0.0, abs=1e-15)
    assert general.angular_momentum_change > 0.0
    # The model reports the change; it does not impose a non-zero assertion.
    assert np.allclose(
        general.angular_momentum_after - general.angular_momentum_before,
        general.angular_momentum_change_vector,
    )


def test_seed_and_csv_output_are_deterministic(tmp_path):
    rows_a = build_validation_rows(seed=1234, n_trials=5)
    rows_b = build_validation_rows(seed=1234, n_trials=5)
    assert rows_a == rows_b
    first = tmp_path / "a.csv"
    second = tmp_path / "b.csv"
    write_validation_csv(first, rows_a)
    write_validation_csv(second, rows_b)
    assert first.read_bytes() == second.read_bytes()
    with first.open(newline="", encoding="utf-8") as handle:
        data = list(csv.DictReader(handle))
    assert {row["validation_level"] for row in data} == {
        "analytic",
        "python_reference",
        "source_audit",
    }
    assert data[-1]["solver_experiment"] == "not_validated"
    assert data[-1]["source_binary_identity"] == "not_proven"


def test_source_audit_keeps_hashes_and_limitations_explicit():
    audit = source_audit_evidence()
    assert audit["source_hash"] == RECORDED_SOURCE_HASH
    assert audit["binary_hash"] == RECORDED_BINARY_HASH
    assert "DM_SIDM=8" in audit["active_flags"]
    assert audit["source_binary_identity"] == "not_proven"
    assert audit["solver_experiment"] == "not_validated"
    assert "no solver experiment" in audit["limitations"]


@pytest.mark.parametrize(
    "keyword",
    ["source_path", "binary_path", "object_path", "config_path", "binary_config_path"],
)
def test_source_audit_rejects_missing_explicit_paths(tmp_path, keyword):
    missing = tmp_path / keyword
    with pytest.raises(FileNotFoundError, match=keyword):
        source_audit_evidence(**{keyword: missing})


def test_source_audit_partial_live_override_does_not_probe_default_opt_paths(tmp_path):
    source = tmp_path / "sidm_core.c"
    source.write_bytes(b"synthetic source evidence\n")
    audit = source_audit_evidence(source_path=source)
    expected_source_hash = hashlib.sha256(source.read_bytes()).hexdigest()
    assert audit["source_hash"] == expected_source_hash
    assert audit["source_path"] == str(source)
    assert audit["binary_hash"] == RECORDED_BINARY_HASH
    assert audit["object_hash"] == RECORDED_OBJECT_HASH
    assert audit["config_hash"] == RECORDED_CONFIG_SH_HASH
    assert audit["binary_config_hash"] == RECORDED_CONFIG_HASH
    assert audit["binary_path"] == "/opt/gizmo-public/GIZMO"
    assert audit["active_flags"] == RECORDED_FLAGS
    assert audit["evidence_origin"] == "live_paths"


def test_default_output_stays_in_conference_validation_package():
    assert default_output_path().as_posix().endswith(
        "nbody/analysis/presentations/conference_2026/validation/dissipation_check.csv"
    )
