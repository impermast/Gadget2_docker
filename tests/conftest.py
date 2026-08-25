"""Shared pytest fixtures for loaders tests.

Makes ``nbody/scripts/plot_scripts`` importable (loaders.py has no package
wrapper) and provides deterministic synthetic snapshots from tests/synth_snap.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
PLOT_SCRIPTS_DIR = REPO_ROOT / "nbody" / "scripts" / "plot_scripts"
if str(PLOT_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(PLOT_SCRIPTS_DIR))

import loaders  # noqa: E402  (needs sys.path patch above)

TESTS_DIR = Path(__file__).resolve().parent
if str(TESTS_DIR) not in sys.path:
    sys.path.insert(0, str(TESTS_DIR))

import synth_snap  # noqa: E402


@pytest.fixture(scope="session")
def snap_full(tmp_path_factory):
    """Snapshot with Masses + NInteractions, sigma=20, uniform sphere."""
    d = tmp_path_factory.mktemp("full")
    return synth_snap.make_snapshot(d / "snapshot_final.hdf5")


@pytest.fixture(scope="session")
def snap_minimal(tmp_path_factory):
    """Snapshot WITHOUT NInteractions dataset (Masses kept: write_summary
    requires them; the missing-Masses read path is covered separately
    by test_missing_mass_and_ni_datasets_give_none via its own fixture)."""
    d = tmp_path_factory.mktemp("minimal")
    return synth_snap.make_snapshot(d / "snapshot_final.hdf5",
                                    with_masses=True, with_ni=False)


@pytest.fixture(scope="session")
def snap_no_mass_no_ni(tmp_path_factory):
    """Snapshot WITHOUT both Masses and NInteractions datasets."""
    d = tmp_path_factory.mktemp("nomass")
    return synth_snap.make_snapshot(d / "snapshot_final.hdf5",
                                    with_masses=False, with_ni=False)


@pytest.fixture(scope="session")
def snap_no_sigma(tmp_path_factory):
    """Snapshot without DM_InteractionCrossSection header attribute."""
    d = tmp_path_factory.mktemp("nosigma")
    return synth_snap.make_snapshot_no_sigma_attr(d / "snapshot_final.hdf5")


@pytest.fixture(scope="session")
def loaders_mod():
    return loaders
