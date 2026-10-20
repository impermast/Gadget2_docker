"""Пути анализа (маркер `math`): блоки, сегменты, containment, env-root."""
import os

import pytest

pytestmark = pytest.mark.math

from analysis.paths import AnalysisPaths, BLOCK_NAMES, default_analysis_root
from analysis.loaders import resolve_metrics_path


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


def test_resolve_metrics_path_uses_canonical_prerun_output(tmp_path, monkeypatch):
    analysis_root = tmp_path / "analysis"
    monkeypatch.setenv("NBODY_ANALYSIS_ROOT", str(analysis_root))
    run_root = tmp_path / "runs" / "example_run"
    run_root.mkdir(parents=True)
    expected = AnalysisPaths().prerun_dir("example_run") / "metrics_series.csv"
    expected.write_text("time\n0.0\n", encoding="utf-8")

    assert resolve_metrics_path(
        run_root, "partial_analysis/metrics_series.csv") == expected
