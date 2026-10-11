"""Synthetic bounded-memory tests for the canonical series log scan."""

from __future__ import annotations

import json
import math
from pathlib import Path

import pytest

from analysis import loaders
from analysis.paths import AnalysisPaths
from analysis.runners import make_prerun_plots as runner


pytestmark = pytest.mark.math


def _write_log(path: Path, text: str) -> Path:
    path.write_text(text, encoding="utf-8")
    return path


def test_real_sync_spelling_variants_and_chunk_boundary(tmp_path):
    log = _write_log(
        tmp_path / "run.log",
        "noise\n"
        "Sync-Point 1, Time: 0.0, Systemstep: 0.0\n"
        "SYNC POINT 2, time = 2.0, SYSTEM-STEP = -4\n"
        "Sync_Point 3, TIME: 1.0, System step: 0.25\n",
    )

    result = loaders.scan_sync_points(log, [1.0, 2.0], chunk_size=11)

    assert result.status == "ok"
    assert result.parsed_sync_count == 3
    assert result.full_log_min_positive_systemstep == pytest.approx(0.25)
    assert [p.sync if p else None for p in result.nearest_points] == [3, 2]


def test_unsorted_repeated_targets_and_deterministic_tie_policy(tmp_path):
    log = _write_log(
        tmp_path / "run.log",
        "Sync-Point 7, Time: 0.5, Systemstep: 0.5\n"
        "Sync-Point 2, Time: 1.5, Systemstep: 0.2\n"
        "Sync-Point 3, Time: 2.5, Systemstep: 0.1\n",
    )

    # 1.0 is equidistant from 0.5 and 1.5: the documented tie policy picks
    # the earlier sync time, independently of target/log ordering.
    result = loaders.scan_sync_points(log, [2.0, 1.0, 2.0, 1.0], chunk_size=5)

    assert [p.sync if p else None for p in result.nearest_points] == [2, 7, 2, 7]
    assert result.no_match_count == 0


def test_global_min_ignores_zero_negative_and_malformed_rows(tmp_path):
    log = _write_log(
        tmp_path / "run.log",
        "Sync-Point 1, Time: 0, Systemstep: 0\n"
        "Sync-Point 2, Time: 1, Systemstep: -1\n"
        "Sync-Point 3, Time: 2, Systemstep: 0.125\n"
        "Sync-Point malformed, Time: broken, Systemstep: 0.01\n",
    )

    result = loaders.scan_sync_points(log, [2.0], chunk_size=1)

    assert result.full_log_min_positive_systemstep == pytest.approx(0.125)
    assert result.parsed_sync_count == 3
    assert result.malformed_count == 1
    assert result.status == "malformed"


def test_missing_empty_and_no_match_are_explicit(tmp_path):
    missing = loaders.scan_sync_points(tmp_path / "missing.log", [0.0])
    assert missing.status == "missing"
    assert missing.nearest_points == (None,)

    empty_path = _write_log(tmp_path / "empty.log", "not a sync row\n")
    empty = loaders.scan_sync_points(empty_path, [0.0])
    assert empty.status == "no-match"
    assert empty.parsed_sync_count == 0
    assert empty.no_match_count == 1


def test_result_retains_only_target_sized_nearest_points(tmp_path):
    lines = [f"Sync-Point {i}, Time: {i / 10:g}, Systemstep: 1\n"
             for i in range(2000)]
    log = _write_log(tmp_path / "large-synthetic.log", "".join(lines))
    targets = [0.1, 17.25, 199.9]

    result = loaders.scan_sync_points(log, targets, chunk_size=17)

    assert result.parsed_sync_count == len(lines)
    assert len(result.nearest_points) == len(targets)
    assert not hasattr(result, "all_points")
    assert not hasattr(result, "points")


def test_series_metadata_is_schema_checked_and_deterministic(tmp_path):
    log = _write_log(tmp_path / "run.log",
                     "Sync-Point 1, Time: 0, Systemstep: 0.5\n")
    scan = loaders.scan_sync_points(log, [0.0])
    metadata = loaders.build_series_metadata(
        run_root=tmp_path / "group" / "run",
        artifact_identity="group-run-v1",
        ptype=3,
        snapshot_times=[0.0, 1.0],
        scan=scan,
        command="runner --run-root /nbody/runs/group/run --plots=,",
    )
    first = tmp_path / "series_metadata.json"
    second = tmp_path / "series_metadata_copy.json"
    loaders.write_series_metadata(metadata, first)
    loaders.write_series_metadata(metadata, second)

    assert first.read_text(encoding="utf-8") == second.read_text(encoding="utf-8")
    loaded = json.loads(first.read_text(encoding="utf-8"))
    assert loaded["schema"] == "series-metadata-v1"
    assert loaded["analysis_schema_version"] == "series-jz-v2"
    assert loaded["artifact_identity"] == "group-run-v1"
    assert loaded["aperture_r"] == 5.0
    assert loaded["fixed_axis"] == "z"
    assert loaded["velocity_frame"]["method"] == "mass_weighted_bulk_velocity"
    assert loaded["full_log_min_positive_systemstep"] == pytest.approx(0.5)
    assert loaded["provenance"]["hdf5_hash"] is None
    assert loaded["provenance"]["log_hash"] is None

    runner._verify(tmp_path, [first], metadata_path=first)


def test_artifact_names_prevent_same_basename_collision(tmp_path, monkeypatch):
    analysis_root = tmp_path / "analysis"
    monkeypatch.setenv("NBODY_ANALYSIS_ROOT", str(analysis_root))
    run_a = tmp_path / "group_a" / "same-run"
    run_b = tmp_path / "group_b" / "same-run"

    out_a = runner._series_output_dir(run_a, "group-a-same-run")
    out_b = runner._series_output_dir(run_b, "group-b-same-run")

    assert out_a != out_b
    assert out_a == analysis_root / "prerun" / "group-a-same-run"
    assert out_b == analysis_root / "prerun" / "group-b-same-run"
    assert AnalysisPaths(analysis_root)._contained(out_a) == out_a
    with pytest.raises(ValueError):
        runner._series_output_dir(run_a, "../escape")

    scan = loaders.scan_sync_points(tmp_path / "missing.log", [])
    metadata = loaders.build_series_metadata(
        run_root=run_a, artifact_identity=out_a.name, ptype=3,
        snapshot_times=[], scan=scan)
    loaders.write_series_metadata(metadata, out_a / "series_metadata.json")
    runner._check_artifact_collision(out_a, run_a)
    with pytest.raises(SystemExit, match="artifact collision"):
        runner._check_artifact_collision(out_a, run_b)
