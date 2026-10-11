"""Synthetic contract tests for conference campaign summaries."""

from __future__ import annotations

import csv
import json
from pathlib import Path

import pytest

from conference.summarize_campaign import (
    CAMPAIGN_COLUMNS,
    REQUIRED_METRICS,
    SummaryError,
    build_campaign_table,
    late_time_summary,
    main,
    write_campaign_csv,
)


def _manifest(*, time_max=2.0, cadence=0.5, health="ok", notes="", verdict_raw="{}"):
    return {
        "group": "g",
        "run_id": "r",
        "run_path": "g/r",
        "time_max": str(time_max),
        "time_bet_snapshot": str(cadence),
        "status": "completed",
        "health": health,
        "metrics_status": "complete",
        "provenance_status": "ok",
        "notes": notes,
        "verdict_raw": verdict_raw,
        "min_systemstep": "0.0001",
    }


def _metric_row(time, **updates):
    row = {
        "time": time,
        "ca_r5": 0.30,
        "z_rms_over_R_rms_r5": 0.20,
        "vrot_over_sigma_r5": 0.80,
        "jz_total_r5": 10.0,
        "jz_mass_r5": 2.0,
        "jz_per_mass_r5": 5.0,
        "ninteractions_total": 10.0,
        "interacted_fraction": 0.10,
        "rho_core_r2": 1.0,
        "nearest_systemstep": 0.001,
    }
    row.update(updates)
    return row


def _write_metrics(path: Path, rows, *, identity=None):
    extra = ["group", "run_id"] if identity else []
    fieldnames = ["time", *extra, *REQUIRED_METRICS]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            value = dict(row)
            if identity:
                value.update({"group": identity[0], "run_id": identity[1]})
            writer.writerow(value)


def _summary(tmp_path, rows, *, manifest=None, metadata=None, index_identity=("g", "r")):
    metrics = tmp_path / "metrics.csv"
    _write_metrics(metrics, rows, identity=index_identity if index_identity else None)
    index_value = {index_identity: metrics}
    if metadata is not None:
        metadata_path = tmp_path / "series_metadata.json"
        metadata_path.write_text(json.dumps(metadata), encoding="utf-8")
        index_value = {index_identity: {"metrics_csv": metrics, "series_metadata_json": metadata_path}}
    return late_time_summary(manifest or _manifest(), index_value)


def test_inclusive_boundaries_and_partial_t5_no_interpolation(tmp_path):
    t2 = _summary(tmp_path, [_metric_row(t) for t in (0, 1, 2, 2.5)])
    assert t2["requested_window_start"] == 1.0
    assert t2["requested_window_end"] == 2.0
    assert t2["ca_r5_points_in_window"] == 2
    assert t2["ca_r5_status"] == "insufficient_coverage"

    t5 = _summary(
        tmp_path,
        [_metric_row(t) for t in (0, 2.5, 3.0, 3.5, 4.0)],
        manifest=_manifest(time_max=5.0),
    )
    assert t5["window_label"] == "T5"
    assert t5["window_is_partial"] is True
    assert t5["effective_window_start"] == 2.5
    assert t5["effective_window_end"] == 4.0
    assert t5["ca_r5_points_in_window"] == 4
    assert t5["ca_r5_status"] == "ok"
    assert t5["ca_r5_final_time"] == 4.0


def test_common_t2_t5_label_and_per_series_window_error(tmp_path):
    metrics = tmp_path / "metrics.csv"
    _write_metrics(metrics, [_metric_row(t) for t in (0, 1, 1.5, 2, 3)])
    common = late_time_summary(
        _manifest(time_max=5.0), {("g", "r"): metrics}, window_label="common_T2_T5"
    )
    assert common["window_label"] == "common_T2_T5"
    assert common["requested_window_start"] == 1.0
    assert common["requested_window_end"] == 2.0

    other = {**_manifest(), "run_id": "other"}
    index = [
        {"group": "g", "run_id": "r", "metrics_csv": str(metrics), "window_start": "3", "window_end": "2"},
        {"group": "g", "run_id": "other", "metrics_csv": str(metrics)},
    ]
    rows = build_campaign_table([_manifest(), other], index)
    bad = next(row for row in rows if row["run_id"] == "r")
    good = next(row for row in rows if row["run_id"] == "other")
    assert bad["status"] == "invalid"
    assert bad["error"].startswith("invalid_window:")
    assert good["status"] in {"ok", "insufficient_coverage"}


def test_unsorted_times_are_stable_and_duplicates_are_marked(tmp_path):
    rows = [
        _metric_row(2.0, ca_r5=0.4),
        _metric_row(1.0, ca_r5=0.5),
        _metric_row(2.0, ca_r5=0.2),  # stable last duplicate wins for screening
        _metric_row(3.0, ca_r5=0.1),
    ]
    # Keep T2 as the requested window while retaining a later point for the
    # final-value assertion; duplicate values at t=2 are both included.
    summary = _summary(tmp_path, rows, manifest=_manifest(time_max=2.0))
    assert summary["duplicate_time_count"] == 1
    assert summary["duplicate_times"] == "2"
    assert summary["ca_r5_final_time"] == 3.0
    assert summary["ca_r5_late_median"] == pytest.approx(0.4)


def test_nan_coverage_is_per_metric_and_does_not_drop_shape_rows(tmp_path):
    rows = [
        _metric_row(1.0, ca_r5="nan"),
        _metric_row(1.5, ca_r5=0.4),
        _metric_row(2.0, ca_r5=0.3),
        _metric_row(2.5, ca_r5=0.2),
    ]
    summary = _summary(tmp_path, rows)
    assert summary["ca_r5_finite_count_in_window"] == 2
    assert summary["ca_r5_value_coverage"] == pytest.approx(2 / 3)
    assert summary["ca_r5_status"] == "insufficient_coverage"
    assert summary["z_rms_over_R_rms_r5_finite_count_in_window"] == 3
    assert summary["z_rms_over_R_rms_r5_status"] == "ok"


def test_missing_t0_does_not_use_first_late_point_as_normalization(tmp_path):
    summary = _summary(tmp_path, [_metric_row(t, jz_total_r5=10 - t) for t in (1, 1.5, 2)])
    assert summary["normalization_undefined"] is True
    assert summary["jz_total_base_source"] == "normalization_undefined"
    assert summary["jz_total_ratio_r5_final"] != summary["jz_total_ratio_r5_final"]
    assert summary["jz_total_ratio_r5_status"] == "missing"


def test_zero_and_tiny_bases_are_nan_with_explicit_reason(tmp_path):
    rows = [
        _metric_row(0, jz_total_r5=0.0, jz_per_mass_r5=1e-14),
        _metric_row(1, jz_total_r5=2.0, jz_per_mass_r5=2e-14),
        _metric_row(1.5, jz_total_r5=3.0, jz_per_mass_r5=3e-14),
        _metric_row(2, jz_total_r5=4.0, jz_per_mass_r5=4e-14),
    ]
    summary = _summary(tmp_path, rows)
    assert summary["normalization_undefined"] is True
    assert set(summary["normalization_undefined_metrics"].split(",")) == {
        "jz_total_ratio_r5",
        "jz_specific_ratio_r5",
    }
    assert summary["jz_total_ratio_r5_final"] != summary["jz_total_ratio_r5_final"]
    assert summary["jz_specific_ratio_r5_final"] != summary["jz_specific_ratio_r5_final"]


def test_total_and_specific_ratios_preserve_sign_and_mass_effect(tmp_path):
    rows = [
        _metric_row(0, jz_total_r5=-10.0, jz_mass_r5=2.0, jz_per_mass_r5=-5.0),
        _metric_row(1, jz_total_r5=-15.0, jz_mass_r5=3.0, jz_per_mass_r5=-5.0),
        _metric_row(1.5, jz_total_r5=-20.0, jz_mass_r5=4.0, jz_per_mass_r5=-5.0),
        _metric_row(2, jz_total_r5=-30.0, jz_mass_r5=6.0, jz_per_mass_r5=-5.0),
    ]
    summary = _summary(tmp_path, rows)
    assert summary["jz_total_ratio_r5_final"] == pytest.approx(3.0)
    assert summary["jz_specific_ratio_r5_final"] == pytest.approx(1.0)
    assert summary["jz_total_base_source"] == "metrics_time_zero"
    assert summary["jz_specific_base_source"] == "metrics_time_zero"
    assert summary["normalization_undefined"] is False


def test_simultaneous_screening_does_not_combine_async_extrema(tmp_path):
    rows = [
        _metric_row(1.0, ca_r5=0.40, z_rms_over_R_rms_r5=0.50, vrot_over_sigma_r5=0.70),
        _metric_row(1.5, ca_r5=0.40, z_rms_over_R_rms_r5=0.30, vrot_over_sigma_r5=0.70),
        _metric_row(2.0, ca_r5=0.30, z_rms_over_R_rms_r5=0.30, vrot_over_sigma_r5=0.70),
    ]
    summary = _summary(tmp_path, rows)
    assert summary["screening_candidate"] is False
    assert summary["screening_consecutive_count"] == 2
    assert summary["campaign_interpretation"] == "no_simultaneous_three_snapshot_candidate"

    qualifying = [_metric_row(t) for t in (1.0, 1.5, 2.0)]
    candidate = _summary(tmp_path, qualifying)
    assert candidate["screening_candidate"] is True
    assert candidate["screening_consecutive_count"] == 3
    assert candidate["screening_covered_t_start"] == 1.0
    assert candidate["screening_covered_t_end"] == 2.0


def test_pathological_manifest_veto_is_separate_from_raw_verdict(tmp_path):
    summary = _summary(
        tmp_path,
        [_metric_row(t) for t in (1.0, 1.5, 2.0, 2.5)],
        manifest=_manifest(health="pathological", notes="dt runaway", verdict_raw='{"flags":["pathological"]}'),
    )
    assert summary["screening_candidate"] is False
    assert summary["manifest_verdict_raw"] == '{"flags":["pathological"]}'
    assert "patholog" in summary["manifest_pathology_flags"]
    assert summary["campaign_interpretation"] == "vetoed_manifest_pathology"


def test_missing_mapping_is_a_row_error_but_duplicate_mapping_is_structural(tmp_path):
    metrics = tmp_path / "metrics.csv"
    _write_metrics(metrics, [_metric_row(t) for t in (1, 1.5, 2)])
    manifest = [_manifest(), {**_manifest(), "run_id": "missing"}]
    rows = build_campaign_table(manifest, {("g", "r"): metrics})
    missing = next(row for row in rows if row["run_id"] == "missing")
    assert missing["status"] == "missing"
    assert missing["error"] == "missing_series_mapping"

    duplicate_index = [
        {"group": "g", "run_id": "r", "metrics_csv": str(metrics)},
        {"group": "g", "run_id": "r", "metrics_csv": str(metrics)},
    ]
    with pytest.raises(SummaryError, match="duplicate series mapping"):
        build_campaign_table([_manifest()], duplicate_index)


def test_wrong_metrics_identity_is_invalid_not_silently_accepted(tmp_path):
    metrics = tmp_path / "wrong.csv"
    _write_metrics(metrics, [_metric_row(t) for t in (1, 1.5, 2)], identity=("g", "other"))
    summary = build_campaign_table([_manifest()], {("g", "r"): metrics})[0]
    assert summary["status"] == "invalid"
    assert summary["series_mapping_status"] == "invalid"
    assert "identity_mismatch" in summary["error"]


def test_full_log_min_timestep_comes_from_metadata_not_series_fallback(tmp_path):
    summary = _summary(
        tmp_path,
        [_metric_row(t, nearest_systemstep=0.2) for t in (1, 1.5, 2)],
        metadata={"group": "g", "run_id": "r", "full_log_min_systemstep": 1e-8},
    )
    assert summary["full_log_min_systemstep"] == pytest.approx(1e-8)
    assert summary["full_log_min_systemstep_source"] == "series_metadata.full_log_min_systemstep"


def test_deterministic_csv_cli_and_metadata(tmp_path):
    metrics = tmp_path / "metrics.csv"
    _write_metrics(metrics, [_metric_row(t) for t in (0, 1, 1.5, 2)])
    manifest_path = tmp_path / "manifest.csv"
    with manifest_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(_manifest()))
        writer.writeheader()
        writer.writerow(_manifest())
    index_path = tmp_path / "series_index.csv"
    with index_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["group", "run_id", "metrics_csv"])
        writer.writeheader()
        writer.writerow({"group": "g", "run_id": "r", "metrics_csv": metrics.name})
    out_a, out_b = tmp_path / "a.csv", tmp_path / "b.csv"
    meta = tmp_path / "metadata.json"
    assert main(["--manifest", str(manifest_path), "--series-index", str(index_path), "--out", str(out_a), "--metadata-out", str(meta)]) == 0
    assert main(["--manifest", str(manifest_path), "--series-index", str(index_path), "--out", str(out_b)]) == 0
    assert out_a.read_bytes() == out_b.read_bytes()
    with out_a.open(newline="", encoding="utf-8") as handle:
        table = list(csv.DictReader(handle))
    assert list(table[0]) == list(CAMPAIGN_COLUMNS)
    assert table[0]["schema_version"] == "conference-campaign-summary-v1"
    metadata = json.loads(meta.read_text(encoding="utf-8"))
    assert metadata["method_version"] == "m4b-late-time-summary-2026-10-10"
    assert metadata["no_interpolation"] is True
