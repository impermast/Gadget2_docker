#!/usr/bin/env python3
"""Reusable run monitor/diagnostic/summary CLI for GIZMO runs.

Examples:
  python3 /nbody/scripts/check_simulations/check_run.py --run-root /nbody/runs/myrun
  python3 /nbody/scripts/check_simulations/check_run.py --run-root /nbody/runs/myrun --mode diagnose --format tg
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Dict

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from eta import estimate_eta, read_state
from formatting import emit_report
from gizmo_log import parse_log
from params import read_run_params
from processes import find_processes
from snapshots import inspect_snapshots
from verdict import classify


def _float_or_none(x):
    try:
        return float(x)
    except Exception:
        return None


def build_report(run_root: str | Path, mode: str = "auto", ptype: int = 3) -> Dict[str, object]:
    root = Path(run_root)
    params = read_run_params(root)
    selected = params.get("selected", {}) or {}
    log = parse_log(root / "run.log")
    snaps = inspect_snapshots(root, time_max=selected.get("TimeMax"), time_bet=selected.get("TimeBetSnapshot"), ptype=ptype)
    procs = find_processes(root)
    state = read_state(root / "run.state")
    report: Dict[str, object] = {
        "run_root": str(root),
        "mode_requested": mode,
        "exists": root.exists(),
        "state": state,
        "processes": procs,
        "params": params,
        "log": log,
        "snapshots": snaps,
    }
    verdict = classify(report)
    latest = log.get("latest") or {}
    snap_meta = snaps.get("latest_metadata") or {}
    current_time = _float_or_none(latest.get("time")) or _float_or_none(snap_meta.get("time"))
    eta = estimate_eta(root, current_time, _float_or_none(selected.get("TimeMax")), verdict.get("health", "unknown"))
    report["verdict"] = verdict
    report["eta"] = eta
    return report


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--run-root", required=True, help="Run directory, e.g. /nbody/runs/<run>")
    ap.add_argument("--mode", choices=["auto", "monitor", "diagnose", "summary"], default="auto")
    ap.add_argument("--format", choices=["human", "json", "tg"], default="human")
    ap.add_argument("--tg", action="store_true", help="Also send the printed report via /nbody/tg/tg_notify.py")
    ap.add_argument("--ptype", type=int, default=3, help="Preferred particle type for snapshot metadata")
    args = ap.parse_args()
    report = build_report(args.run_root, mode=args.mode, ptype=args.ptype)
    return emit_report(report, fmt=args.format, tg=args.tg)


if __name__ == "__main__":
    raise SystemExit(main())
