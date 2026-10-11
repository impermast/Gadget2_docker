import importlib.util
import json


SPEC = importlib.util.spec_from_file_location("post_run_gate", "nbody/scripts/conference/post_run_gate.py")
gate = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(gate)


def make_run(tmp_path, log=None, snapshots=(), used=False):
    (tmp_path / "output").mkdir()
    if log is not None:
        (tmp_path / "run.log").write_text(log)
    for name in snapshots:
        (tmp_path / "output" / name).touch()
    if used:
        (tmp_path / "output" / "parameters-usedvalues").write_text("TimeMax 2\n")
    return tmp_path


def test_complete(tmp_path):
    root = make_run(tmp_path, "Time 2.0\nSimulation finished normally.\n", ["snapshot_000.hdf5"], True)
    result = gate.assess(root, 2.0)
    assert result["verdict"] == "completed"
    assert result["terminal_detected"] and result["final_time_reached"]


def test_gizmo_final_time_marker(tmp_path):
    root = make_run(tmp_path, "Final time=2 reached\n", ["snapshot_000.hdf5"], True)
    result = gate.assess(root, 2.0)
    assert result["terminal_detected"]


def test_partial_without_final_marker(tmp_path):
    result = gate.assess(make_run(tmp_path, "Time 1.0\n", ["snapshot_000.hdf5"]), 2.0)
    assert result["verdict"] == "partial"


def test_error_marker(tmp_path):
    result = gate.assess(make_run(tmp_path, "ERROR: crashed\n"), 2.0)
    assert result["verdict"] == "failed"
    assert result["error_markers"]


def test_missing_log_is_unknown(tmp_path):
    result = gate.assess(make_run(tmp_path), 2.0)
    assert result["verdict"] == "active_or_unknown"
