#!/usr/bin/env python3
"""Deterministic late-time summaries for an explicit campaign series index.

This module is deliberately a text-only layer.  It reads a manifest and an
explicit ``(group, run_id) -> metrics CSV`` mapping; it never globs for a CSV,
chooses the first existing candidate, opens HDF5 files, or runs a solver.

The public entry points are :func:`late_time_summary` (one row or a list of
rows) and :func:`build_campaign_table` (always a list).  A series-index CSV
has at least ``group,run_id,metrics_csv`` and may add
``series_metadata_json,expected_cadence,window_label,window_start,window_end``.
The same mapping can be supplied as a Python mapping keyed by ``(group,
run_id)``.  Relative paths are resolved only against the index file's parent
directory; there is no fallback path search.

The summary keeps final values separate from inclusive-window late medians,
reports per-column coverage, and computes Jz ratios only from a confirmed
time-zero row or explicitly supplied time-zero metadata.  Missing values stay
NaN/empty in memory and are serialized as ``nan`` rather than zero.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import statistics
import sys
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence


SCHEMA_VERSION = "conference-campaign-summary-v1"
METHOD_VERSION = "m4b-late-time-summary-2026-10-10"

T2_WINDOW = (1.0, 2.0)
T5_WINDOW = (2.5, 5.0)
COMMON_T2_T5_WINDOW = (1.0, 2.0)
WINDOWS = {
    "T2": T2_WINDOW,
    "T5": T5_WINDOW,
    "common_t1_t2": COMMON_T2_T5_WINDOW,
    "common_T2_T5": COMMON_T2_T5_WINDOW,
    "common": COMMON_T2_T5_WINDOW,
    "T2_T5_common": COMMON_T2_T5_WINDOW,
}

REQUIRED_METRICS = (
    "ca_r5",
    "z_rms_over_R_rms_r5",
    "vrot_over_sigma_r5",
    "jz_total_r5",
    "jz_mass_r5",
    "jz_per_mass_r5",
    "ninteractions_total",
    "interacted_fraction",
    "rho_core_r2",
    "nearest_systemstep",
)
NORMALIZED_METRICS = ("jz_total_ratio_r5", "jz_specific_ratio_r5")
SUMMARY_METRICS = REQUIRED_METRICS + NORMALIZED_METRICS

MANIFEST_ID_COLUMNS = ("group", "run_id")
SERIES_INDEX_COLUMNS = ("group", "run_id", "metrics_csv")

# Time comparisons deliberately use fixed, documented tolerances.  They are
# only for identifying duplicate/zero timestamps, not for inventing samples.
TIME_ABS_TOL = 1.0e-12
TIME_REL_TOL = 1.0e-10
BASE_ABS_TOL = 1.0e-12
BASE_REL_TOL = 1.0e-10

SCREENING_THRESHOLDS = {
    "ca_r5_lt": 0.45,
    "z_rms_over_R_rms_r5_lt": 0.35,
    "abs_vrot_over_sigma_r5_gt": 0.6,
    "minimum_consecutive_snapshots": 3,
}


class SummaryError(ValueError):
    """A malformed or structurally ambiguous summary input."""


def _finite(value: Any) -> bool:
    try:
        return math.isfinite(float(value))
    except (TypeError, ValueError):
        return False


def _float_or_nan(value: Any) -> float:
    """Parse a numeric CSV/JSON value without converting missing to zero."""

    if value is None:
        return math.nan
    if isinstance(value, str):
        text = value.strip()
        if not text or text.lower() in {"nan", "na", "n/a", "none", "null", "missing"}:
            return math.nan
        value = text
    try:
        number = float(value)
    except (TypeError, ValueError):
        return math.nan
    return number if math.isfinite(number) else math.nan


def _parse_cell(value: Any) -> tuple[float, bool]:
    """Return ``(value, valid)``; NaN/blank is valid missing, text is invalid."""

    if value is None:
        return math.nan, True
    if isinstance(value, str):
        text = value.strip()
        if not text or text.lower() in {"nan", "na", "n/a", "none", "null", "missing"}:
            return math.nan, True
        try:
            number = float(text)
        except (TypeError, ValueError):
            return math.nan, False
    else:
        try:
            number = float(value)
        except (TypeError, ValueError):
            return math.nan, False
    if not math.isfinite(number):
        return math.nan, True
    return number, True


def _format_value(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, float):
        if math.isnan(value):
            return "nan"
        if math.isinf(value):
            return "inf" if value > 0 else "-inf"
        return format(value, ".17g")
    if isinstance(value, (dict, list, tuple)):
        return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return str(value)


def _canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _same_time(left: float, right: float) -> bool:
    return math.isclose(left, right, rel_tol=TIME_REL_TOL, abs_tol=TIME_ABS_TOL)


def _source_rows(source: Any, *, label: str) -> tuple[list[dict[str, Any]], Path | None]:
    """Load mappings/CSV rows and return rows plus their parent directory."""

    if hasattr(source, "as_dict") and callable(source.as_dict):
        return [dict(source.as_dict())], None
    if isinstance(source, Mapping):
        return [dict(source)], None
    if isinstance(source, (str, Path)):
        path = Path(source).expanduser()
        if not path.is_file():
            raise SummaryError(f"{label} file does not exist: {path}")
        try:
            with path.open("r", encoding="utf-8", errors="replace", newline="") as handle:
                reader = csv.DictReader(handle)
                if not reader.fieldnames:
                    raise SummaryError(f"{label} has no CSV header: {path}")
                return [dict(row) for row in reader], path.parent
        except csv.Error as exc:
            raise SummaryError(f"cannot parse {label} CSV {path}: {exc}") from exc
    try:
        rows = []
        for item in source:
            if hasattr(item, "as_dict") and callable(item.as_dict):
                rows.append(dict(item.as_dict()))
            elif isinstance(item, Mapping):
                rows.append(dict(item))
            else:
                raise SummaryError(f"{label} iterable contains a non-mapping row")
        return rows, None
    except TypeError as exc:
        raise SummaryError(f"{label} must be a CSV path or iterable of mappings") from exc


def _id_value(row: Mapping[str, Any], key: str) -> str:
    return str(row.get(key, "") or "").strip()


def _normalise_manifest(source: Any) -> tuple[list[dict[str, Any]], bool]:
    rows, _base = _source_rows(source, label="manifest")
    result: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()
    for index, row in enumerate(rows):
        group, run_id = _id_value(row, "group"), _id_value(row, "run_id")
        if not group or not run_id:
            raise SummaryError(f"manifest row {index} lacks group/run_id")
        key = (group, run_id)
        if key in seen:
            raise SummaryError(f"duplicate manifest identity: {group}/{run_id}")
        seen.add(key)
        record = dict(row)
        record["group"], record["run_id"], record["_manifest_index"] = group, run_id, index
        result.append(record)
    result.sort(key=lambda row: (row["group"], row["run_id"], str(row.get("run_path", ""))))
    return result, len(rows) == 1


def _resolve_path(value: Any, base: Path | None) -> Path | None:
    if value is None or not str(value).strip():
        return None
    path = Path(str(value)).expanduser()
    if not path.is_absolute() and base is not None:
        path = base / path
    return path


def _normalise_series_index(source: Any) -> tuple[dict[tuple[str, str], dict[str, Any]], Path | None]:
    """Normalize an explicit index and reject structurally ambiguous mappings."""

    if isinstance(source, (str, Path)):
        rows, base = _source_rows(source, label="series index")
        entries = []
        for index, row in enumerate(rows):
            entry = dict(row)
            entry["_index_row"] = index
            entries.append(entry)
    elif isinstance(source, Mapping):
        base = None
        entries = []
        for index, (key, value) in enumerate(source.items()):
            if isinstance(key, tuple) and len(key) == 2:
                group, run_id = str(key[0]), str(key[1])
            else:
                text = str(key)
                if "/" not in text:
                    raise SummaryError(
                        "series index mapping keys must be (group, run_id) tuples or group/run_id strings"
                    )
                group, run_id = text.rsplit("/", 1)
            if isinstance(value, Mapping):
                entry = dict(value)
            elif isinstance(value, (tuple, list)) and 1 <= len(value) <= 2:
                # A compact in-memory spelling is useful for synthetic callers:
                # ``{(group, run): (metrics_csv, metadata_json)}``.
                entry = {"metrics_csv": value[0]}
                if len(value) == 2:
                    entry["series_metadata_json"] = value[1]
            else:
                entry = {"metrics_csv": value}
            entry.update({"group": group, "run_id": run_id, "_index_row": index})
            entries.append(entry)
    else:
        rows, base = _source_rows(source, label="series index")
        entries = []
        for index, row in enumerate(rows):
            entry = dict(row)
            entry["_index_row"] = index
            entries.append(entry)

    result: dict[tuple[str, str], dict[str, Any]] = {}
    for entry in entries:
        group, run_id = _id_value(entry, "group"), _id_value(entry, "run_id")
        if not group or not run_id:
            raise SummaryError(f"series index row {entry.get('_index_row')} lacks group/run_id")
        key = (group, run_id)
        if key in result:
            raise SummaryError(f"duplicate series mapping: {group}/{run_id}")
        metrics_value = entry.get("metrics_csv", entry.get("metrics_path"))
        metadata_value = entry.get(
            "series_metadata_json",
            entry.get("metadata_json", entry.get("series_metadata")),
        )
        result[key] = {
            "group": group,
            "run_id": run_id,
            "metrics_csv": _resolve_path(metrics_value, base),
            "metrics_csv_text": "" if metrics_value is None else str(metrics_value),
            "series_metadata_json": _resolve_path(metadata_value, base),
            "series_metadata_json_text": "" if metadata_value is None else str(metadata_value),
            "expected_cadence": _float_or_nan(entry.get("expected_cadence")),
            "window_label": str(entry.get("window_label", "") or "").strip(),
            "window_start": _float_or_nan(entry.get("window_start")),
            "window_end": _float_or_nan(entry.get("window_end")),
            "_index_row": entry.get("_index_row"),
        }
    return result, base


def _identity_from_mapping(value: Mapping[str, Any]) -> tuple[str | None, str | None]:
    identity = value.get("identity") if isinstance(value.get("identity"), Mapping) else value
    group = identity.get("group") if isinstance(identity, Mapping) else None
    run_id = identity.get("run_id") if isinstance(identity, Mapping) else None
    if run_id is None and isinstance(identity, Mapping):
        run_id = identity.get("run")
    return (str(group).strip() if group not in (None, "") else None,
            str(run_id).strip() if run_id not in (None, "") else None)


def _load_series_metadata(path: Path | None, expected: tuple[str, str]) -> tuple[dict[str, Any], str | None]:
    if path is None:
        return {}, None
    if not path.is_file():
        return {}, f"series_metadata_missing:{path}"
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        return {}, f"series_metadata_invalid:{type(exc).__name__}"
    if not isinstance(value, Mapping):
        return {}, "series_metadata_invalid:not_object"
    group, run_id = _identity_from_mapping(value)
    if (group is not None and group != expected[0]) or (run_id is not None and run_id != expected[1]):
        return dict(value), "identity_mismatch:series_metadata"
    return dict(value), None


def _load_metrics(path: Path | None, expected: tuple[str, str]) -> tuple[dict[str, Any], str | None]:
    if path is None:
        return {"rows": [], "fieldnames": set(), "invalid_time_rows": 0, "identity": None}, "metrics_csv_missing"
    if not path.is_file():
        return {"rows": [], "fieldnames": set(), "invalid_time_rows": 0, "identity": None}, f"metrics_csv_missing:{path}"
    try:
        with path.open("r", encoding="utf-8", errors="replace", newline="") as handle:
            reader = csv.DictReader(handle)
            if not reader.fieldnames:
                return {"rows": [], "fieldnames": set(), "invalid_time_rows": 0, "identity": None}, "metrics_csv_invalid:empty_header"
            fieldnames = {str(name).strip() for name in reader.fieldnames if name}
            if "time" not in fieldnames:
                return {"rows": [], "fieldnames": fieldnames, "invalid_time_rows": 0, "identity": None}, "metrics_csv_invalid:missing_time"
            rows: list[dict[str, Any]] = []
            invalid_time_rows = 0
            invalid_metric_cells: dict[str, int] = {metric: 0 for metric in SUMMARY_METRICS}
            identities: set[tuple[str, str]] = set()
            for source_index, raw in enumerate(reader):
                row = {str(key).strip(): value for key, value in raw.items() if key}
                time, time_valid = _parse_cell(row.get("time"))
                if not time_valid or not _finite(time):
                    if any(value not in (None, "") for value in row.values()):
                        invalid_time_rows += 1
                    continue
                parsed: dict[str, Any] = {"time": time, "_source_index": source_index}
                for metric in SUMMARY_METRICS:
                    value, valid = _parse_cell(row.get(metric))
                    parsed[metric] = value
                    if not valid:
                        invalid_metric_cells[metric] += 1
                group, run_id = _id_value(row, "group"), _id_value(row, "run_id")
                if group or run_id:
                    identities.add((group, run_id))
                rows.append(parsed)
            if identities:
                if len(identities) != 1 or next(iter(identities)) != expected:
                    return {
                        "rows": rows,
                        "fieldnames": fieldnames,
                        "invalid_time_rows": invalid_time_rows,
                        "invalid_metric_cells": invalid_metric_cells,
                        "identity": sorted(identities),
                    }, "identity_mismatch:metrics_csv"
            rows.sort(key=lambda row: (row["time"], row["_source_index"]))
            duplicate_groups: list[float] = []
            for previous, current in zip(rows, rows[1:]):
                if _same_time(previous["time"], current["time"]):
                    if not duplicate_groups or not _same_time(duplicate_groups[-1], current["time"]):
                        duplicate_groups.append(current["time"])
            return {
                "rows": rows,
                "fieldnames": fieldnames,
                "invalid_time_rows": invalid_time_rows,
                "invalid_metric_cells": invalid_metric_cells,
                "identity": sorted(identities) if identities else None,
                "duplicate_groups": duplicate_groups,
            }, None
    except (OSError, UnicodeError, csv.Error) as exc:
        return {"rows": [], "fieldnames": set(), "invalid_time_rows": 0, "identity": None}, f"metrics_csv_invalid:{type(exc).__name__}"


def _window_from_entry(
    manifest: Mapping[str, Any],
    entry: Mapping[str, Any],
    metadata: Mapping[str, Any],
    explicit_window: tuple[float, float] | None,
    explicit_label: str | None,
) -> tuple[float, float, str, str]:
    if explicit_window is not None:
        start, end = explicit_window
        label = explicit_label or "explicit"
        return start, end, label, "explicit_argument"
    if explicit_label:
        if explicit_label not in WINDOWS:
            raise SummaryError(f"unknown window label: {explicit_label}")
        start, end = WINDOWS[explicit_label]
        return start, end, explicit_label, "explicit_label"
    entry_start, entry_end = entry.get("window_start"), entry.get("window_end")
    if _finite(entry_start) and _finite(entry_end):
        return float(entry_start), float(entry_end), entry.get("window_label") or "index_window", "series_index"
    label = str(entry.get("window_label") or metadata.get("window_label") or "").strip()
    if label in WINDOWS:
        start, end = WINDOWS[label]
        return start, end, label, "label"
    time_max = _float_or_nan(manifest.get("time_max"))
    if _finite(time_max) and time_max > 2.5:
        return T5_WINDOW[0], T5_WINDOW[1], "T5", "manifest_time_max"
    return T2_WINDOW[0], T2_WINDOW[1], "T2", "manifest_time_max_or_default"


def _effective_window(rows: Sequence[Mapping[str, Any]], requested: tuple[float, float]) -> dict[str, Any]:
    finite_times = [float(row["time"]) for row in rows if _finite(row.get("time"))]
    if not finite_times:
        return {
            "requested_start": requested[0], "requested_end": requested[1],
            "effective_start": math.nan, "effective_end": math.nan,
            "available_start": math.nan, "available_end": math.nan,
            "partial": True, "rows": [],
        }
    available_start, available_end = min(finite_times), max(finite_times)
    effective_start = max(requested[0], available_start)
    effective_end = min(requested[1], available_end)
    selected = [
        row for row in rows
        if requested[0] - TIME_ABS_TOL <= float(row["time"]) <= requested[1] + TIME_ABS_TOL
    ]
    return {
        "requested_start": requested[0], "requested_end": requested[1],
        "effective_start": effective_start if effective_start <= effective_end + TIME_ABS_TOL else math.nan,
        "effective_end": effective_end if effective_start <= effective_end + TIME_ABS_TOL else math.nan,
        "available_start": available_start, "available_end": available_end,
        "partial": (available_start > requested[0] + TIME_ABS_TOL
                    or available_end < requested[1] - TIME_ABS_TOL),
        "rows": selected,
    }


def _unique_time_count(rows: Sequence[Mapping[str, Any]]) -> int:
    count = 0
    previous = math.nan
    for row in rows:
        time = float(row["time"])
        if count == 0 or not _same_time(previous, time):
            count += 1
            previous = time
    return count


def _expected_points(start: float, end: float, cadence: float) -> float:
    if not (_finite(start) and _finite(end) and _finite(cadence) and cadence > 0 and end >= start):
        return math.nan
    return float(max(1, math.floor((end - start) / cadence + TIME_REL_TOL) + 1))


def normalization_tolerance(base: float, values: Sequence[float] = ()) -> float:
    """Return the deterministic scale-aware zero-denominator tolerance."""

    finite_values = [abs(float(value)) for value in values if _finite(value)]
    scale = max(abs(float(base)) if _finite(base) else 0.0,
                statistics.median(finite_values) if finite_values else 0.0,
                sys.float_info.epsilon)
    return BASE_ABS_TOL + BASE_REL_TOL * scale


def _base_value(
    rows: Sequence[Mapping[str, Any]],
    metadata: Mapping[str, Any],
    metric: str,
) -> tuple[float, float, str]:
    """Return confirmed ``(value, time, source)`` or NaN/empty source."""

    metadata_time = _float_or_nan(metadata.get("base_time"))
    metadata_source = str(metadata.get("base_source") or "").strip()
    base_values = metadata.get("base_values")
    if _finite(metadata_time) and not _same_time(metadata_time, 0.0):
        return math.nan, math.nan, "base_time_not_zero"
    if _finite(metadata_time) and _same_time(metadata_time, 0.0) and isinstance(base_values, Mapping):
        value = _float_or_nan(base_values.get(metric))
        source = metadata_source or "series_metadata_time_zero"
        if value == value and source.lower() not in {"unknown", "inferred_first_row", "first_row"}:
            return value, 0.0, source
    zero_rows = [row for row in rows if _same_time(float(row["time"]), 0.0)]
    if zero_rows:
        # Rows are stably sorted; the final duplicate is the deterministic base.
        value = _float_or_nan(zero_rows[-1].get(metric))
        return value, 0.0, metadata_source or "metrics_time_zero"
    return math.nan, math.nan, "normalization_undefined"


def _metric_summary(
    metric: str,
    rows: Sequence[Mapping[str, Any]],
    window_rows: Sequence[Mapping[str, Any]],
    fieldnames: set[str],
    invalid_cells: Mapping[str, int],
    window_info: Mapping[str, Any],
    expected_points: float,
) -> dict[str, Any]:
    prefix = metric
    if metric not in fieldnames and metric not in NORMALIZED_METRICS:
        status = "missing"
        all_values: list[tuple[float, float]] = []
        window_values: list[tuple[float, float]] = []
    else:
        all_values = [(float(row["time"]), float(row.get(metric, math.nan))) for row in rows if _finite(row.get(metric))]
        window_values = [(float(row["time"]), float(row.get(metric, math.nan))) for row in window_rows if _finite(row.get(metric))]
        if invalid_cells.get(metric, 0):
            status = "invalid"
        elif not all_values:
            status = "missing"
        elif len(window_values) < 3:
            status = "insufficient_coverage"
        else:
            status = "ok"
    final_value = all_values[-1][1] if all_values else math.nan
    final_time = all_values[-1][0] if all_values else math.nan
    late_values = [value for _time, value in window_values]
    late_median = statistics.median(late_values) if late_values else math.nan
    actual_start = min((time for time, _value in window_values), default=math.nan)
    actual_end = max((time for time, _value in window_values), default=math.nan)
    points = len(window_rows)
    unique_times = _unique_time_count(window_rows)
    value_coverage = len(window_values) / points if points else math.nan
    requested_span = float(window_info["requested_end"] - window_info["requested_start"])
    time_span = actual_end - actual_start if _finite(actual_start) and _finite(actual_end) else math.nan
    time_coverage = (
        max(0.0, min(1.0, time_span / requested_span))
        if _finite(time_span) and requested_span > 0 else (1.0 if window_values and requested_span == 0 else math.nan)
    )
    expected_coverage = unique_times / expected_points if _finite(expected_points) and expected_points > 0 else math.nan
    return {
        f"{prefix}_final": final_value,
        f"{prefix}_final_time": final_time,
        f"{prefix}_late_median": late_median,
        f"{prefix}_actual_t_start": actual_start,
        f"{prefix}_actual_t_end": actual_end,
        f"{prefix}_finite_count": len(all_values),
        f"{prefix}_finite_count_in_window": len(window_values),
        f"{prefix}_points_in_window": points,
        f"{prefix}_unique_times_in_window": unique_times,
        f"{prefix}_value_coverage": value_coverage,
        f"{prefix}_coverage": value_coverage,
        f"{prefix}_time_coverage": time_coverage,
        f"{prefix}_expected_coverage": expected_coverage,
        f"{prefix}_status": status,
        f"{prefix}_invalid_count": int(invalid_cells.get(metric, 0)),
    }


def _metadata_full_log_step(manifest: Mapping[str, Any], metadata: Mapping[str, Any]) -> tuple[float, str]:
    for key in ("full_log_min_systemstep", "min_systemstep_full_log", "min_systemstep"):
        value = _float_or_nan(metadata.get(key))
        if _finite(value):
            return value, f"series_metadata.{key}"
    value = _float_or_nan(manifest.get("min_systemstep"))
    if _finite(value):
        return value, "manifest.min_systemstep"
    return math.nan, "missing"


def _pathology_flags(manifest: Mapping[str, Any]) -> list[str]:
    values = [
        str(manifest.get("health", "") or ""),
        str(manifest.get("notes", "") or ""),
        str(manifest.get("verdict_raw", "") or ""),
    ]
    text = " ".join(values).lower()
    tokens = ("patholog", "runaway", "ntreeforce", "numerical_collapse", "dt_collapse")
    return [token for token in tokens if token in text]


def _screen(rows: Sequence[Mapping[str, Any]], window_rows: Sequence[Mapping[str, Any]], manifest: Mapping[str, Any]) -> dict[str, Any]:
    # One representative per timestamp prevents duplicate rows from faking
    # three consecutive snapshots.  Stable sort means the last duplicate wins.
    representatives: list[Mapping[str, Any]] = []
    for row in window_rows:
        if not representatives or not _same_time(float(representatives[-1]["time"]), float(row["time"])):
            representatives.append(row)
        else:
            representatives[-1] = row
    best_count = 0
    best_times: list[float] = []
    current: list[float] = []
    for row in representatives:
        ca, thickness, support = (row.get(name, math.nan) for name in (
            "ca_r5", "z_rms_over_R_rms_r5", "vrot_over_sigma_r5"))
        qualifies = (_finite(ca) and _finite(thickness) and _finite(support)
                     and float(ca) < SCREENING_THRESHOLDS["ca_r5_lt"]
                     and float(thickness) < SCREENING_THRESHOLDS["z_rms_over_R_rms_r5_lt"]
                     and abs(float(support)) > SCREENING_THRESHOLDS["abs_vrot_over_sigma_r5_gt"])
        if qualifies:
            current.append(float(row["time"]))
            if len(current) > best_count:
                best_count, best_times = len(current), list(current)
        else:
            current = []
    pathology = _pathology_flags(manifest)
    if pathology:
        interpretation = "vetoed_manifest_pathology"
        candidate = False
    elif best_count >= SCREENING_THRESHOLDS["minimum_consecutive_snapshots"]:
        interpretation = "simultaneous_disk_candidate"
        candidate = True
    elif len(representatives) < SCREENING_THRESHOLDS["minimum_consecutive_snapshots"]:
        interpretation = "insufficient_coverage_for_screening"
        candidate = False
    else:
        interpretation = "no_simultaneous_three_snapshot_candidate"
        candidate = False
    return {
        "manifest_verdict_raw": str(manifest.get("verdict_raw", "") or ""),
        "manifest_pathology_flags": ",".join(pathology),
        "screening_candidate": candidate,
        "screening_consecutive_count": best_count,
        "screening_covered_t_start": min(best_times) if best_times else math.nan,
        "screening_covered_t_end": max(best_times) if best_times else math.nan,
        "screening_covered_interval": (max(best_times) - min(best_times)) if best_times else math.nan,
        "screening_unique_points": len(representatives),
        "campaign_interpretation": interpretation,
    }


def _empty_metric_fields(status: str) -> dict[str, Any]:
    output: dict[str, Any] = {}
    for metric in SUMMARY_METRICS:
        output.update({
            f"{metric}_final": math.nan,
            f"{metric}_final_time": math.nan,
            f"{metric}_late_median": math.nan,
            f"{metric}_actual_t_start": math.nan,
            f"{metric}_actual_t_end": math.nan,
            f"{metric}_finite_count": 0,
            f"{metric}_finite_count_in_window": 0,
            f"{metric}_points_in_window": 0,
            f"{metric}_unique_times_in_window": 0,
            f"{metric}_value_coverage": math.nan,
            f"{metric}_coverage": math.nan,
            f"{metric}_time_coverage": math.nan,
            f"{metric}_expected_coverage": math.nan,
            f"{metric}_status": status,
            f"{metric}_invalid_count": 0,
        })
    return output


def _series_error_row(
    manifest: Mapping[str, Any],
    entry: Mapping[str, Any] | None,
    error: str,
) -> dict[str, Any]:
    """Return a complete, deterministic row for an isolated series error."""

    group, run_id = _id_value(manifest, "group"), _id_value(manifest, "run_id")
    full_step, full_step_source = _metadata_full_log_step(manifest, {})
    status = "invalid" if entry else "missing"
    output: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "method_version": METHOD_VERSION,
        "group": group,
        "run_id": run_id,
        "run_key": f"{group}/{run_id}",
        "run_path": str(manifest.get("run_path", "") or ""),
        "manifest_status": str(manifest.get("status", "") or ""),
        "manifest_health": str(manifest.get("health", "") or ""),
        "manifest_metrics_status": str(manifest.get("metrics_status", "") or ""),
        "manifest_provenance_status": str(manifest.get("provenance_status", "") or ""),
        "series_mapping_status": "invalid" if entry else "missing",
        "series_metrics_csv": str(entry.get("metrics_csv") or "") if entry else "",
        "series_metadata_json": str(entry.get("series_metadata_json") or "") if entry else "",
        "series_schema_version": "",
        "window_label": "",
        "window_source": "",
        "requested_window_start": math.nan,
        "requested_window_end": math.nan,
        "effective_window_start": math.nan,
        "effective_window_end": math.nan,
        "window_is_partial": True,
        "available_t_start": math.nan,
        "available_t_end": math.nan,
        "expected_cadence": math.nan,
        "expected_points": math.nan,
        "points_total": 0,
        "unique_times_total": 0,
        "duplicate_time_count": 0,
        "duplicate_times": "",
        "invalid_time_rows": 0,
        "full_log_min_systemstep": full_step,
        "full_log_min_systemstep_source": full_step_source,
        "jz_total_base_value": math.nan,
        "jz_total_base_time": math.nan,
        "jz_total_base_source": "normalization_undefined",
        "jz_specific_base_value": math.nan,
        "jz_specific_base_time": math.nan,
        "jz_specific_base_source": "normalization_undefined",
        "normalization_undefined": True,
        "normalization_undefined_metrics": ",".join(NORMALIZED_METRICS),
        "normalization_tolerance_abs": BASE_ABS_TOL,
        "normalization_tolerance_rel": BASE_REL_TOL,
        "normalization_tolerance_total": math.nan,
        "normalization_tolerance_specific": math.nan,
        "error": error,
    }
    output.update(_empty_metric_fields(status))
    output.update(_screen([], [], manifest))
    output["status"] = status
    output["metrics_json"] = _canonical_json(
        {metric: {"status": status} for metric in SUMMARY_METRICS}
    )
    return output


def _normalization_series(
    rows: Sequence[Mapping[str, Any]],
    metric: str,
    base: float,
) -> tuple[list[float], float]:
    values = [float(row.get(metric, math.nan)) if _finite(row.get(metric)) else math.nan for row in rows]
    tolerance = normalization_tolerance(base, values)
    if not _finite(base) or abs(float(base)) <= tolerance:
        return [math.nan for _ in rows], tolerance
    return [value / float(base) if _finite(value) else math.nan for value in values], tolerance


def _summarise_one(
    manifest: Mapping[str, Any],
    entry: Mapping[str, Any] | None,
    *,
    explicit_window: tuple[float, float] | None,
    explicit_label: str | None,
) -> dict[str, Any]:
    group, run_id = _id_value(manifest, "group"), _id_value(manifest, "run_id")
    entry = entry or {}
    metadata, metadata_error = _load_series_metadata(entry.get("series_metadata_json"), (group, run_id))
    requested_start, requested_end, window_label, window_source = _window_from_entry(
        manifest, entry, metadata, explicit_window, explicit_label
    )
    full_step, full_step_source = _metadata_full_log_step(manifest, metadata)
    output: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "method_version": METHOD_VERSION,
        "group": group,
        "run_id": run_id,
        "run_key": f"{group}/{run_id}",
        "run_path": str(manifest.get("run_path", "") or ""),
        "manifest_status": str(manifest.get("status", "") or ""),
        "manifest_health": str(manifest.get("health", "") or ""),
        "manifest_metrics_status": str(manifest.get("metrics_status", "") or ""),
        "manifest_provenance_status": str(manifest.get("provenance_status", "") or ""),
        "series_mapping_status": "mapped" if entry else "missing",
        "series_metrics_csv": str(entry.get("metrics_csv") or ""),
        "series_metadata_json": str(entry.get("series_metadata_json") or ""),
        "series_schema_version": str(metadata.get("schema_version", "") or ""),
        "window_label": window_label,
        "window_source": window_source,
        "requested_window_start": requested_start,
        "requested_window_end": requested_end,
        "full_log_min_systemstep": full_step,
        "full_log_min_systemstep_source": full_step_source,
        "error": metadata_error or "",
        "normalization_undefined": False,
        "normalization_undefined_metrics": "",
        "jz_total_base_value": math.nan,
        "jz_total_base_time": math.nan,
        "jz_total_base_source": "normalization_undefined",
        "jz_specific_base_value": math.nan,
        "jz_specific_base_time": math.nan,
        "jz_specific_base_source": "normalization_undefined",
        "normalization_tolerance_abs": BASE_ABS_TOL,
        "normalization_tolerance_rel": BASE_REL_TOL,
        "normalization_tolerance_total": math.nan,
        "normalization_tolerance_specific": math.nan,
    }
    if (not _finite(requested_start) or not _finite(requested_end)
            or requested_end < requested_start):
        output.update(_empty_metric_fields("invalid"))
        output.update(_screen([], [], manifest))
        output["series_mapping_status"] = "invalid" if entry else "missing"
        output["status"] = "invalid"
        output["error"] = f"invalid_window:{requested_start}:{requested_end}"
        output["metrics_json"] = _canonical_json(
            {metric: {"status": "invalid"} for metric in SUMMARY_METRICS}
        )
        return output
    if not entry:
        output.update(_empty_metric_fields("missing"))
        output.update(_screen([], [], manifest))
        output["status"] = "missing"
        output["error"] = "missing_series_mapping"
        return output
    metrics, metrics_error = _load_metrics(entry.get("metrics_csv"), (group, run_id))
    if metadata_error and output["error"] == "":
        output["error"] = metadata_error
    if metrics_error:
        output["series_mapping_status"] = "invalid" if metrics_error.startswith("identity_mismatch") or metrics_error.startswith("metrics_csv_invalid") else "missing"
        output.update(_empty_metric_fields("invalid" if "invalid" in metrics_error or "mismatch" in metrics_error else "missing"))
        output.update(_screen([], [], manifest))
        output["status"] = "invalid" if output["series_mapping_status"] == "invalid" else "missing"
        output["error"] = ";".join(value for value in (output["error"], metrics_error) if value)
        return output
    rows = metrics["rows"]
    window_info = _effective_window(rows, (requested_start, requested_end))
    cadence = _float_or_nan(entry.get("expected_cadence"))
    if not _finite(cadence):
        cadence = _float_or_nan(metadata.get("expected_cadence"))
    if not _finite(cadence):
        cadence = _float_or_nan(manifest.get("time_bet_snapshot"))
    expected_points = _expected_points(window_info["effective_start"], window_info["effective_end"], cadence)
    output.update({
        "available_t_start": window_info["available_start"],
        "available_t_end": window_info["available_end"],
        "effective_window_start": window_info["effective_start"],
        "effective_window_end": window_info["effective_end"],
        "window_is_partial": bool(window_info["partial"]),
        "expected_cadence": cadence,
        "expected_points": expected_points,
        "points_total": len(rows),
        "unique_times_total": _unique_time_count(rows),
        "duplicate_time_count": len(metrics.get("duplicate_groups", [])),
        "duplicate_times": ",".join(_format_value(value) for value in metrics.get("duplicate_groups", [])),
        "invalid_time_rows": int(metrics.get("invalid_time_rows", 0)),
    })

    # Construct normalized series before calculating any per-metric summaries.
    total_base, total_base_time, total_base_source = _base_value(rows, metadata, "jz_total_r5")
    specific_base, specific_base_time, specific_base_source = _base_value(rows, metadata, "jz_per_mass_r5")
    total_series, total_tol = _normalization_series(rows, "jz_total_r5", total_base)
    specific_series, specific_tol = _normalization_series(rows, "jz_per_mass_r5", specific_base)
    total_undefined = not any(_finite(value) for value in total_series)
    specific_undefined = not any(_finite(value) for value in specific_series)
    for row, total_ratio, specific_ratio in zip(rows, total_series, specific_series):
        row["jz_total_ratio_r5"] = total_ratio
        row["jz_specific_ratio_r5"] = specific_ratio
    output.update({
        "jz_total_base_value": total_base,
        "jz_total_base_time": total_base_time,
        "jz_total_base_source": total_base_source,
        "jz_specific_base_value": specific_base,
        "jz_specific_base_time": specific_base_time,
        "jz_specific_base_source": specific_base_source,
        "normalization_tolerance_total": total_tol,
        "normalization_tolerance_specific": specific_tol,
        "normalization_undefined": bool(total_undefined or specific_undefined),
        "normalization_undefined_metrics": ",".join(
            metric for metric, undefined in (("jz_total_ratio_r5", total_undefined), ("jz_specific_ratio_r5", specific_undefined)) if undefined
        ),
    })
    fieldnames = set(metrics["fieldnames"]) | set(NORMALIZED_METRICS)
    invalid_cells = metrics.get("invalid_metric_cells", {})
    for metric in SUMMARY_METRICS:
        output.update(_metric_summary(metric, rows, window_info["rows"], fieldnames, invalid_cells, window_info, expected_points))
    output.update(_screen(rows, window_info["rows"], manifest))
    statuses = [output[f"{metric}_status"] for metric in REQUIRED_METRICS]
    if metadata_error or metrics_error:
        output["status"] = "invalid"
    elif all(status == "missing" for status in statuses):
        output["status"] = "missing"
    elif any(status == "invalid" for status in statuses):
        output["status"] = "invalid"
    elif any(status in {"missing", "insufficient_coverage"} for status in statuses):
        output["status"] = "insufficient_coverage"
    else:
        output["status"] = "ok"
    if metrics.get("invalid_time_rows"):
        output["error"] = ";".join(value for value in (output["error"], "invalid_time_rows") if value)
    nested = {
        metric: {suffix: output.get(f"{metric}_{suffix}") for suffix in (
            "final", "final_time", "late_median", "actual_t_start", "actual_t_end",
            "finite_count", "finite_count_in_window", "points_in_window", "value_coverage",
            "time_coverage", "expected_coverage", "status")}
        for metric in SUMMARY_METRICS
    }
    output["metrics_json"] = _canonical_json(nested)
    return output


def late_time_summary(
    manifest: Any,
    series_index: Any,
    *,
    window: tuple[float, float] | None = None,
    window_label: str | None = None,
) -> dict[str, Any] | list[dict[str, Any]]:
    """Summarize one manifest row or all rows using an explicit series index.

    A mapping with ``group`` and ``run_id`` is treated as one manifest row and
    returns one dictionary.  A manifest CSV or iterable returns a sorted list.
    Duplicate manifest/index identities raise :class:`SummaryError`; missing
    per-run mappings and bad series files become explicit row statuses so that
    other runs remain reportable.
    """

    if window is not None:
        if len(window) != 2 or not all(_finite(value) for value in window):
            raise SummaryError("window must be a finite (start, end) pair")
        if float(window[1]) < float(window[0]):
            raise SummaryError("window end must not be less than window start")
        window = (float(window[0]), float(window[1]))
    manifests, single = _normalise_manifest(manifest)
    index, _index_base = _normalise_series_index(series_index)
    result = [_summarise_one(row, index.get((row["group"], row["run_id"])), explicit_window=window, explicit_label=window_label) for row in manifests]
    return result[0] if single else result


BASE_COLUMNS = (
    "schema_version", "method_version", "group", "run_id", "run_key", "run_path",
    "status", "manifest_status", "manifest_health", "manifest_metrics_status",
    "manifest_provenance_status", "series_mapping_status", "series_metrics_csv",
    "series_metadata_json", "series_schema_version", "window_label", "window_source",
    "requested_window_start", "requested_window_end", "effective_window_start",
    "effective_window_end", "window_is_partial", "available_t_start", "available_t_end",
    "expected_cadence", "expected_points", "points_total", "unique_times_total",
    "duplicate_time_count", "duplicate_times", "invalid_time_rows", "full_log_min_systemstep",
    "full_log_min_systemstep_source", "jz_total_base_value", "jz_total_base_time",
    "jz_total_base_source", "jz_specific_base_value", "jz_specific_base_time",
    "jz_specific_base_source", "normalization_undefined", "normalization_undefined_metrics",
    "normalization_tolerance_abs", "normalization_tolerance_rel", "normalization_tolerance_total",
    "normalization_tolerance_specific", "manifest_verdict_raw", "manifest_pathology_flags",
    "screening_candidate", "screening_consecutive_count", "screening_covered_t_start",
    "screening_covered_t_end", "screening_covered_interval", "screening_unique_points",
    "campaign_interpretation", "error", "metrics_json",
)
METRIC_SUFFIXES = (
    "final", "final_time", "late_median", "actual_t_start", "actual_t_end", "finite_count",
    "finite_count_in_window", "points_in_window", "unique_times_in_window", "value_coverage",
    "coverage", "time_coverage", "expected_coverage", "status", "invalid_count",
)
CAMPAIGN_COLUMNS = BASE_COLUMNS + tuple(
    f"{metric}_{suffix}" for metric in SUMMARY_METRICS for suffix in METRIC_SUFFIXES
)


def build_campaign_table(
    manifest: Any,
    series_index: Any,
    *,
    window: tuple[float, float] | None = None,
    window_label: str | None = None,
    out: str | Path | None = None,
    metadata_out: str | Path | None = None,
) -> list[dict[str, Any]]:
    """Build a sorted campaign table and optionally write deterministic CSV."""

    result = late_time_summary(manifest, series_index, window=window, window_label=window_label)
    rows = [result] if isinstance(result, Mapping) else list(result)
    rows.sort(key=lambda row: (str(row.get("group", "")), str(row.get("run_id", "")), str(row.get("run_path", ""))))
    if out is not None:
        write_campaign_csv(rows, out, metadata_out=metadata_out)
    return rows


def write_campaign_csv(
    rows: Iterable[Mapping[str, Any]],
    out: str | Path,
    *,
    metadata_out: str | Path | None = None,
) -> Path:
    """Write stable schema/order and optional deterministic method metadata."""

    records = [dict(row) for row in rows]
    records.sort(key=lambda row: (str(row.get("group", "")), str(row.get("run_id", "")), str(row.get("run_path", ""))))
    destination = Path(out)
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle, lineterminator="\n")
        writer.writerow(CAMPAIGN_COLUMNS)
        for row in records:
            writer.writerow([_format_value(row.get(column)) for column in CAMPAIGN_COLUMNS])
    if metadata_out is not None:
        metadata = {
            "schema_version": SCHEMA_VERSION,
            "method_version": METHOD_VERSION,
            "columns": list(CAMPAIGN_COLUMNS),
            "row_count": len(records),
            "required_metrics": list(REQUIRED_METRICS),
            "normalized_metrics": list(NORMALIZED_METRICS),
            "windows": {key: list(value) for key, value in WINDOWS.items()},
            "screening_thresholds": SCREENING_THRESHOLDS,
            "normalization_tolerance": {
                "absolute": BASE_ABS_TOL,
                "relative": BASE_REL_TOL,
                "scale": "max(abs(base), median(abs(finite_series)), machine_epsilon)",
            },
            "no_interpolation": True,
            "implicit_glob_or_fallback": False,
        }
        metadata_path = Path(metadata_out)
        metadata_path.parent.mkdir(parents=True, exist_ok=True)
        metadata_path.write_text(json.dumps(metadata, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return destination


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", required=True, help="manifest CSV")
    parser.add_argument("--series-index", required=True, help="explicit group/run -> metrics CSV index")
    parser.add_argument("--out", required=True, help="campaign summary CSV")
    parser.add_argument("--metadata-out", help="optional schema/method JSON sidecar")
    parser.add_argument("--window-start", type=float)
    parser.add_argument("--window-end", type=float)
    parser.add_argument("--window-label")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = _parser()
    args = parser.parse_args(argv)
    if (args.window_start is None) != (args.window_end is None):
        parser.error("--window-start and --window-end must be supplied together")
    window = None
    if args.window_start is not None:
        window = (args.window_start, args.window_end)
        if args.window_end < args.window_start:
            parser.error("--window-end must not be less than --window-start")
    try:
        rows = build_campaign_table(
            args.manifest,
            args.series_index,
            window=window,
            window_label=args.window_label,
            out=args.out,
            metadata_out=args.metadata_out,
        )
    except SummaryError as exc:
        parser.error(str(exc))
    print(f"wrote {len(rows)} campaign summary rows to {args.out}")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
