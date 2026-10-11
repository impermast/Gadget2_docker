"""Synthetic contract tests for the conference run manifest."""

from __future__ import annotations

import csv
from pathlib import Path

import pytest

import conference.manifest as manifest_module
from conference.manifest import MANIFEST_COLUMNS, main, scan_runs, write_manifest_csv


def _write_run(
    root: Path,
    *,
    time_max: float = 2.0,
    reached: float | None = 2.0,
    systemstep: float = 0.1,
    metrics: str | None = None,
    used_time_max: float | None = None,
    run_commit: str | None = None,
) -> Path:
    root.mkdir(parents=True, exist_ok=True)
    (root / "output").mkdir(exist_ok=True)
    (root / "output" / "snapshot_000.hdf5").write_bytes(b"not-read-by-manifest")
    if reached is not None:
        (root / "output" / "snapshot_001.hdf5").write_bytes(b"not-read-by-manifest")
        if reached >= time_max:
            (root / "output" / "snapshot_002.hdf5").write_bytes(b"not-read-by-manifest")
    params = [
        f"InitCondFile /nbody/ics/dwarf_rot_N1e5/dwarf_rot_N1e5_k08",
        f"TimeMax {time_max}",
        "TimeBetSnapshot 1",
        "TimeOfFirstSnapshot 0",
        "DM_InteractionCrossSection 2.5",
        "DM_DissipationFactor 0.25",
        "DM_KickPerCollision 0",
        "DM_InteractionVelocityScale 0",
        "SofteningBulge 0.05",
        "MaxSizeTimestep 0.005",
    ]
    (root / ".gizmo_run.param").write_text("\n".join(params) + "\n", encoding="utf-8")
    if used_time_max is not None:
        (root / "output" / "parameters-usedvalues").write_text(
            "\n".join(
                [
                    f"TimeMax {used_time_max}",
                    "TimeBetSnapshot 1",
                    "DM_InteractionCrossSection 2.5",
                    "DM_DissipationFactor 0.25",
                    "DM_KickPerCollision 0",
                    "SofteningBulge 0.05",
                ]
            )
            + "\n",
            encoding="utf-8",
        )
    if run_commit:
        (root / "provenance.json").write_text(
            '{"run_commit": "' + run_commit + '"}\n', encoding="utf-8"
        )
    if reached is not None:
        (root / "run.log").write_text(
            "GIZMO synthetic run\n"
            "Running on 2 MPI tasks.\n"
            f"Sync-Point 0, Time: 0, Systemstep: 0.1\n"
            f"Sync-Point 1, Time: {reached}, Systemstep: {systemstep}\n"
            "done with snapshot.\n",
            encoding="utf-8",
        )
    if metrics is not None:
        (root / "partial_analysis").mkdir(exist_ok=True)
        (root / "partial_analysis" / "metrics_series.csv").write_text(metrics, encoding="utf-8")
    return root


def _metrics(time: float, step: float, interactions: int = 10) -> str:
    return (
        "snapshot,file,time,particles,nearest_systemstep,ninteractions_total\n"
        f"0,snapshot_000.hdf5,0,100,0.1,0\n"
        f"1,snapshot_001.hdf5,{time},100,{step},{interactions}\n"
    )


@pytest.mark.guard
def test_group_run_identity_is_unique(tmp_path):
    _write_run(tmp_path / "group_a" / "same")
    _write_run(tmp_path / "group_b" / "same")

    rows = scan_runs([tmp_path])

    assert {(row.group, row.run_id) for row in rows} == {
        ("group_a", "same"),
        ("group_b", "same"),
    }
    assert len({row.run_path for row in rows}) == 2


@pytest.mark.guard
def test_missing_log_and_metrics_are_unknown_and_missing(tmp_path):
    run = _write_run(tmp_path / "g" / "no_evidence", reached=None)

    row = scan_runs([tmp_path])[0]

    assert row.status == "unknown"
    assert row.health == "unknown"
    assert row.metrics_status == "missing"
    assert row.provenance_status == "missing"
    assert "log=missing" in row.notes
    assert row.dissipation_d == 0.25  # known input, not a missing-value zero
    assert not (run / "run.log").exists()


@pytest.mark.guard
def test_incomplete_and_completed_pathological_are_separate(tmp_path):
    _write_run(tmp_path / "g" / "incomplete", reached=1.0, metrics=_metrics(1.0, 0.1))
    _write_run(
        tmp_path / "g" / "pathological",
        reached=2.0,
        systemstep=1e-8,
        metrics=_metrics(2.0, 1e-8, interactions=1000),
    )

    rows = {row.run_id: row for row in scan_runs([tmp_path])}

    assert rows["incomplete"].status == "incomplete"
    assert rows["incomplete"].health == "ok"
    assert rows["incomplete"].metrics_status == "partial"
    assert rows["pathological"].status == "completed"
    assert rows["pathological"].health == "pathological"
    assert rows["pathological"].metrics_status == "complete"
    assert rows["pathological"].ninteractions_final == 1000


@pytest.mark.guard
def test_old_run_commit_is_unknown_analysis_revision_is_separate(tmp_path):
    row = scan_runs([_write_run(tmp_path / "g" / "run", metrics=_metrics(2.0, 0.1))])[0]

    assert row.run_commit is None
    assert row.analysis_commit is not None
    assert row.analysis_commit != row.run_commit
    assert "run_commit=unknown:no_evidence" in row.notes


@pytest.mark.guard
def test_conflicting_runtime_and_applied_sources_are_visible(tmp_path):
    row = scan_runs(
        [
            _write_run(
                tmp_path / "g" / "conflict",
                used_time_max=3.0,
                metrics=_metrics(3.0, 0.1),
            )
        ]
    )[0]

    assert row.time_max == 3
    assert row.provenance_status == "conflict"
    assert "parameter_conflict=TimeMax" in row.notes


@pytest.mark.guard
def test_csv_output_is_deterministic_and_has_public_schema(tmp_path):
    root = _write_run(tmp_path / "g" / "run", metrics=_metrics(2.0, 0.1))
    rows_a = scan_runs([tmp_path])
    rows_b = scan_runs([tmp_path])
    out_a = tmp_path / "a.csv"
    out_b = tmp_path / "b.csv"

    write_manifest_csv(rows_a, out_a)
    write_manifest_csv(rows_b, out_b)

    assert out_a.read_bytes() == out_b.read_bytes()
    with out_a.open(newline="", encoding="utf-8") as handle:
        table = list(csv.DictReader(handle))
    assert table and list(table[0]) == MANIFEST_COLUMNS
    assert table[0]["run_path"] == "g/run"
    assert root.exists()


@pytest.mark.guard
def test_cli_requires_explicit_roots_and_writes_optional_metadata(tmp_path):
    _write_run(tmp_path / "g" / "run", metrics=_metrics(2.0, 0.1))
    out = tmp_path / "package" / "run_manifest.csv"
    metadata = tmp_path / "package" / "manifest_metadata.json"

    assert main(["--roots", str(tmp_path), "--out", str(out), "--metadata-out", str(metadata)]) == 0
    assert out.is_file()
    assert metadata.is_file()
    metadata_text = metadata.read_text(encoding="utf-8")
    assert "conference-manifest-v1" in metadata_text
    assert "derived_from_newest_evidence_mtime" in metadata_text


@pytest.mark.guard
def test_scan_hashes_solver_inputs_once_for_multiple_runs(tmp_path, monkeypatch):
    _write_run(tmp_path / "g" / "one", metrics=_metrics(2.0, 0.1))
    _write_run(tmp_path / "g" / "two", metrics=_metrics(2.0, 0.1))
    original = manifest_module._solver_hashes
    calls = []

    def counted(*args, **kwargs):
        calls.append((args, kwargs))
        return original(*args, **kwargs)

    monkeypatch.setattr(manifest_module, "_solver_hashes", counted)
    rows = manifest_module.scan_runs([tmp_path])

    assert len(rows) == 2
    assert len(calls) == 1
