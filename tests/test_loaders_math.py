"""Level 1: unit tests of loaders.py math on synthetic snapshots.

Every test uses analytic or exactly known expectations (see tests/synth_snap).
Fast, deterministic, no simulations involved.

Group marker: 'math' (run alone via `pytest tests/ -m math`).
"""

from __future__ import annotations

import numpy as np
import pytest

import synth_snap
from synth_snap import (CENTER, MTOT, NI_COUNT, NI_TOTAL, N_PARTICLES,
                        PARTICLE_MASS, RADIUS, SIGMA, TIME)

pytestmark = pytest.mark.math

TOL_CENTER = 3.5  # shrink_center is statistical: cut keeps only 10% of
                  # particles, compounding noise gives ~1-2.5 kpc scatter at
                  # N=2000 (measured over seeds 42/7/123/999/2026); exact
                  # reproduction is covered by test_golden.py instead


# ────────────────────────── read_snapshot: headers ──────────────────────────

def test_read_sigma_from_header(snap_full, loaders_mod):
    d = loaders_mod.read_snapshot(snap_full)
    assert d["sigma"] == pytest.approx(SIGMA)


def test_read_time_from_header(snap_full, loaders_mod):
    d = loaders_mod.read_snapshot(snap_full)
    assert d["time"] == pytest.approx(TIME)


def test_missing_sigma_attr_falls_back_to_zero(snap_no_sigma, loaders_mod):
    d = loaders_mod.read_snapshot(snap_no_sigma)
    assert d["sigma"] == 0.0


def test_missing_mass_and_ni_datasets_give_none(snap_no_mass_no_ni,
                                                loaders_mod):
    d = loaders_mod.read_snapshot(snap_no_mass_no_ni)
    assert d["mass"] is None
    assert d["ni"] is None


def test_shapes_of_read_fields(snap_full, loaders_mod):
    d = loaders_mod.read_snapshot(snap_full)
    n = N_PARTICLES
    assert d["pos"].shape == (n, 3)
    assert d["vel"].shape == (n, 3)
    assert d["mass"].shape == (n,)
    assert d["ni"].shape == (n,)


# ─────────────────────────────── shrink_center ───────────────────────────────

def test_shrink_center_recovers_shifted_center(snap_full, loaders_mod):
    d = loaders_mod.read_snapshot(snap_full)
    c = loaders_mod.shrink_center(d["pos"], d["mass"])
    # uniform ball with NO escapees: must find the true center tightly
    assert c == pytest.approx(np.asarray(CENTER), abs=TOL_CENTER)


def test_shrink_center_is_translation_invariant(snap_full, loaders_mod):
    d = loaders_mod.read_snapshot(snap_full)
    shift = np.array([-7.0, 3.5, 11.0])
    c1 = loaders_mod.shrink_center(d["pos"], d["mass"])
    c2 = loaders_mod.shrink_center(d["pos"] + shift, d["mass"])
    assert c2 == pytest.approx(c1 + shift, abs=1e-8)


# ─────────────────────────── inner_log_slope (exact) ─────────────────────────

def test_inner_log_slope_exact_power_law(loaders_mod):
    """Perfect rho ~ r^-3 data -> slope exactly -3."""
    r = np.logspace(-2.0, 2.0, 60)
    rho = r ** (-3.0)
    slope = np.full_like(r, -3.0)
    assert loaders_mod.inner_log_slope(slope, rho, r) == pytest.approx(-3.0)


def test_inner_log_slope_flat_profile(loaders_mod):
    """Perfect constant density -> slope exactly 0."""
    r = np.logspace(-2.0, 2.0, 60)
    rho = np.full_like(r, 1.234)
    slope = np.zeros_like(r)
    assert loaders_mod.inner_log_slope(slope, rho, r) == pytest.approx(
        0.0, abs=1e-12)


def test_inner_log_slope_all_invalid_returns_nan(loaders_mod):
    bad = np.array([np.nan, np.nan])
    result = loaders_mod.inner_log_slope(bad, bad.copy(), np.array([1.0, 2.0]))
    assert np.isnan(result)


# ─────────────────── prepare_profile_data: structural checks ─────────────────

@pytest.fixture(scope="module")
def profile(snap_full, loaders_mod):
    return loaders_mod.prepare_profile_data(snap_full)


def test_profile_bin_structure(profile):
    # 60 log-edges -> 59 centers, strictly increasing, inside [0.05, rmax]
    r = profile["r"]
    assert len(r) == 59
    assert np.all(np.diff(r) > 0)
    assert r.min() >= 0.05
    assert len(profile["rho"]) == len(profile["slope"]) == \
        len(profile["sigma_v"]) == len(r)


def test_profile_header_values_propagate(profile):
    assert profile["time"] == pytest.approx(TIME)
    assert profile["cross_section"] == pytest.approx(SIGMA)
    assert profile["core_radius"] == pytest.approx(2.0)


def test_profile_rho_core_uniform_sphere(profile):
    # Uniform sphere: expected core density = mass fraction within r<2 / volume.
    f = (2.0 / RADIUS) ** 3                      # 0.008
    expected = f * N_PARTICLES * PARTICLE_MASS / (4 / 3 * np.pi * 2.0 ** 3)
    # Poisson noise in particle counts -> generous 40% tolerance
    assert profile["rho_core"] == pytest.approx(expected, rel=0.4)


def test_profile_rho_positive_only_where_counts(profile):
    rho = profile["rho"]
    finite = np.isfinite(rho)
    assert np.all(rho[finite] > 0)
    # inner log-bins (r << mean interparticle distance) stay empty (nan):
    # measured ~26/59 populated for the uniform sphere at N=2000
    assert finite.sum() > 20


def test_profile_slope_near_zero_for_uniform_sphere(profile, loaders_mod):
    inner = loaders_mod.inner_log_slope(profile["slope"], profile["rho"],
                                        profile["r"])
    # noisy but flat: median inner slope must stay small
    assert not np.isnan(inner)
    assert abs(inner) < 0.5


def test_profile_ni_bins_structure(profile):
    assert "ni_mean" in profile and "ni_frac" in profile
    nb = len(profile["ni_mean"])
    assert nb == 12 == len(profile["ni_frac"])
    valid = np.isfinite(profile["ni_frac"])
    assert valid.any()
    # fractions are percentages in [0, 100]
    assert np.all(profile["ni_frac"][valid] >= 0)
    assert np.all(profile["ni_frac"][valid] <= 100)


# ─────────────────────────── NInteractions exact stats ───────────────────────

def test_ni_exact_statistics(snap_full, loaders_mod):
    d = loaders_mod.read_snapshot(snap_full)
    ni = d["ni"]
    tot = int(ni.sum())
    nz = int((ni > 0).sum())
    assert tot == NI_TOTAL                    # 5050
    assert nz == NI_COUNT                     # 100
    frac = 100.0 * nz / len(ni)
    assert frac == pytest.approx(100.0 * NI_COUNT / N_PARTICLES)  # 5.00%
    nn = ni[ni > 0].astype(float)
    assert float(nn.max()) == float(NI_COUNT)
    assert float(np.median(nn)) == pytest.approx(NI_COUNT / 2 + 0.5)


# ─────────────────────────────── write_summary ───────────────────────────────

def test_write_summary_contents(snap_full, tmp_path, loaders_mod):
    out_file = tmp_path / "summary.txt"
    txt = loaders_mod.write_summary(snap_full, out_file)
    assert out_file.exists()
    assert f"Particles: {N_PARTICLES}" in txt
    assert f"Mtot={MTOT:.4e}" in txt
    assert "CrossSection: 20.0" in txt
    assert f"NInteractions TOTAL: {NI_TOTAL}" in txt
    assert "Particles interacted: 100/2000 (5.00%)" in txt
    assert "NOT IN SNAPSHOT" not in txt


def test_write_summary_without_ni_reports_absence(snap_minimal, tmp_path,
                                                  loaders_mod):
    txt = loaders_mod.write_summary(snap_minimal, tmp_path / "s.txt")
    assert "NInteractions: NOT IN SNAPSHOT" in txt


# ─────────────────────────────── list_snapshots ─────────────────────────────

def test_list_snapshots_sorted_by_number(tmp_path, loaders_mod):
    d = synth_snap.make_series(tmp_path / "series", count=11, n=50)
    files = loaders_mod.list_snapshots(d)
    assert len(files) == 11
    numbers = [int(f.rsplit("_", 1)[1].split(".")[0]) for f in files]
    assert numbers == sorted(numbers)
    assert numbers[0] == 0 and numbers[-1] == 10


def test_list_snapshots_empty_dir_raises(tmp_path, loaders_mod):
    with pytest.raises(FileNotFoundError):
        loaders_mod.list_snapshots(tmp_path)

