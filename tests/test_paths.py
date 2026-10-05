"""Пути анализа (маркер `math`): блоки, сегменты, containment, env-root."""
import os

import pytest

pytestmark = pytest.mark.math

from analysis.paths import AnalysisPaths, BLOCK_NAMES, default_analysis_root


def test_artifact_dir_layout(tmp_path, monkeypatch):
    monkeypatch.setenv("NBODY_ANALYSIS_ROOT", str(tmp_path / "analysis"))
    ap = AnalysisPaths()
    assert ap.run_dir("myrun") == tmp_path / "analysis" / "core" / "myrun"
    assert ap.campaign_dir("c", member="m") == tmp_path / "analysis" / "campaigns" / "c" / "m"
    assert ap.ic_dir("ic1").parent.name == "ic"


def test_bad_block_raises_with_hint(tmp_path, monkeypatch):
    monkeypatch.setenv("NBODY_ANALYSIS_ROOT", str(tmp_path))
    ap = AnalysisPaths()
    with pytest.raises(KeyError, match="core"):
        ap.artifact_dir("nope", "x")


def test_bad_segments_rejected(tmp_path, monkeypatch):
    monkeypatch.setenv("NBODY_ANALYSIS_ROOT", str(tmp_path))
    ap = AnalysisPaths()
    for evil in ["../runs/x", "a/b", "", ".hidden", ".."]:
        with pytest.raises(ValueError):
            ap.artifact_dir("core", evil)
        with pytest.raises(ValueError):
            ap.artifact_dir("core", "ok", group=evil)


def test_env_root_overrides(tmp_path, monkeypatch):
    monkeypatch.setenv("NBODY_ANALYSIS_ROOT", str(tmp_path / "custom"))
    assert default_analysis_root() == tmp_path / "custom"
