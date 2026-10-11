"""Analytic tests for the series Jz/mass/frame contract."""

from __future__ import annotations

import csv
import math
from dataclasses import fields
from pathlib import Path

import h5py
import numpy as np
import pytest

from analysis import loaders


pytestmark = pytest.mark.math


def test_angular_momentum_rigid_ring_uses_unequal_masses_and_sign():
    radius = 2.0
    omega = 3.5
    theta = np.linspace(0.0, 2.0 * np.pi, 8, endpoint=False)
    pos = np.column_stack((radius * np.cos(theta), radius * np.sin(theta),
                           np.zeros_like(theta)))
    mass = np.arange(1.0, len(pos) + 1.0)
    vel = omega * np.column_stack((-pos[:, 1], pos[:, 0], pos[:, 2]))

    jz, enclosed_mass, specific = loaders.angular_momentum_stats(
        pos, vel, mass, radius=2.5)

    expected = omega * np.sum(mass * radius**2)
    assert jz == pytest.approx(expected)
    assert enclosed_mass == pytest.approx(np.sum(mass))
    assert specific == pytest.approx(expected / np.sum(mass))

    jz_neg, _, _ = loaders.angular_momentum_stats(pos, -vel, mass, 2.5)
    assert jz_neg == pytest.approx(-expected)


def test_angular_momentum_empty_aperture_is_zero_mass_nan_specific():
    pos = np.array([[2.0, 0.0, 0.0], [0.0, 2.0, 0.0]])
    vel = np.array([[0.0, 1.0, 0.0], [-1.0, 0.0, 0.0]])
    result = loaders.angular_momentum_stats(pos, vel, np.array([2.0, 4.0]), 1.0)
    assert result[0] == pytest.approx(0.0)
    assert result[1] == pytest.approx(0.0)
    assert math.isnan(result[2])


def _write_snapshot(path: Path, pos: np.ndarray, vel: np.ndarray,
                    *, mass: np.ndarray | None = None,
                    mass_table: np.ndarray | None = None,
                    time: float = 0.0) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    with h5py.File(path, "w") as f:
        header = f.create_group("Header")
        header.attrs["Time"] = time
        if mass_table is not None:
            header.attrs["MassTable"] = np.asarray(mass_table, dtype=float)
        g = f.create_group("PartType3")
        g.create_dataset("Coordinates", data=np.asarray(pos, dtype=float))
        g.create_dataset("Velocities", data=np.asarray(vel, dtype=float))
        if mass is not None:
            g.create_dataset("Masses", data=np.asarray(mass, dtype=float))
    return path


def _ring(n: int = 32, radius: float = 2.0, omega: float = 1.25):
    theta = np.linspace(0.0, 2.0 * np.pi, n, endpoint=False)
    pos = np.column_stack((radius * np.cos(theta), radius * np.sin(theta),
                           np.zeros_like(theta)))
    vel = omega * np.column_stack((-pos[:, 1], pos[:, 0], pos[:, 2]))
    return pos, vel


def test_series_reader_uses_mass_weighted_bulk_and_is_common_velocity_invariant(tmp_path):
    pos, rel_vel = _ring()
    # Equal masses keep the ring's shrinkage center exactly at the geometric
    # origin; unequal-mass weighting is covered analytically above.
    mass = np.ones(len(pos))
    shift = np.array([7.0, -3.0, 4.5])
    bulk = np.array([11.0, -8.0, 2.0])
    first = _write_snapshot(tmp_path / "snapshot_000.hdf5", pos, rel_vel,
                            mass=mass)
    shifted = _write_snapshot(tmp_path / "snapshot_001.hdf5", pos + shift,
                              rel_vel + bulk, mass=mass, time=0.1)

    a = loaders.read_series_metric(first, 3, [])
    b = loaders.read_series_metric(shifted, 3, [])
    expected = 1.25 * np.sum(mass * 2.0**2)
    assert a.jz_total_r5 == pytest.approx(expected, rel=1e-10, abs=1e-10)
    assert a.jz_mass_r5 == pytest.approx(np.sum(mass))
    assert a.jz_per_mass_r5 == pytest.approx(expected / np.sum(mass))
    assert b.jz_total_r5 == pytest.approx(a.jz_total_r5, rel=1e-10, abs=1e-10)
    assert b.jz_mass_r5 == pytest.approx(a.jz_mass_r5)
    # Rotation columns are explicitly in the same bulk-velocity frame too.
    assert b.mean_vphi_r5 == pytest.approx(a.mean_vphi_r5, rel=1e-10, abs=1e-10)


def test_series_reader_mass_table_fallback_and_missing_mass_invalid(tmp_path):
    pos, vel = _ring()
    table = np.zeros(6)
    table[3] = 2.5
    table_path = _write_snapshot(tmp_path / "snapshot_000.hdf5", pos, vel,
                                 mass_table=table)
    resolved = loaders.read_snapshot(table_path)
    assert np.all(resolved["mass"] == pytest.approx(2.5))
    metric = loaders.read_series_metric(table_path, 3, [])
    assert metric.jz_mass_r5 == pytest.approx(2.5 * len(pos))

    no_mass = _write_snapshot(tmp_path / "snapshot_001.hdf5", pos, vel)
    invalid = loaders.read_series_metric(no_mass, 3, [])
    assert math.isnan(invalid.jz_total_r5)
    assert math.isnan(invalid.jz_mass_r5)
    assert math.isnan(invalid.jz_per_mass_r5)


def test_one_snapshot_reader_does_not_compute_jz_and_empty_csv_has_stable_header(tmp_path):
    pos, vel = _ring(n=4)
    snap = _write_snapshot(tmp_path / "snapshot_000.hdf5", pos, vel,
                           mass=np.ones(len(pos)))
    loaded = loaders.read_snapshot(snap)
    assert not any(name.startswith("jz") for name in loaded)

    out = tmp_path / "empty" / "metrics_series.csv"
    loaders.write_metrics_csv([], out)
    with out.open(newline="") as fh:
        reader = csv.DictReader(fh)
        assert reader.fieldnames == [field.name for field in fields(loaders.SeriesMetric)]
        assert reader.fieldnames[-3:] == ["jz_total_r5", "jz_mass_r5", "jz_per_mass_r5"]
        assert list(reader) == []
