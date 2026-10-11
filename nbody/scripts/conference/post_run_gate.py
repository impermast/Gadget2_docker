#!/usr/bin/env python3
"""Small, offline completion gate for a terminal simulation run."""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

TAIL_BYTES = 64 * 1024
_TIME_RE = re.compile(r"(?:Time|time)\s*[:=]?\s*(-?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][-+]?\d+)?)")
_ERROR_RE = re.compile(r"\b(?:ERROR|FATAL|ABORT|segmentation fault|MPI_ABORT)\b", re.I)
_DONE_RE = re.compile(
    r"Simulation finished normally|run completed successfully|finished normally|"
    r"Final\s+time\s*=\s*[-+]?\d+(?:\.\d+)?(?:[eE][-+]?\d+)?\s+reached|"
    r"Simulation exited with code\s*0",
    re.I,
)


def _tail(path: Path) -> str | None:
    if not path.is_file():
        return None
    with path.open("rb") as handle:
        handle.seek(0, 2)
        handle.seek(-min(handle.tell(), TAIL_BYTES), 1)
        return handle.read().decode("utf-8", errors="replace")


def assess(run_root: str | Path, expected_time: float, log: str | Path | None = None,
           min_snapshots: int = 1) -> dict[str, Any]:
    root = Path(run_root)
    log_path = Path(log) if log else root / "run.log"
    text = _tail(log_path)
    lines = text.splitlines() if text is not None else []
    errors = [line.strip() for line in lines if _ERROR_RE.search(line)]
    times = [float(m.group(1)) for line in lines for m in [_TIME_RE.search(line)] if m]
    terminal = bool(text is not None and _DONE_RE.search(text))

    output = root / "output"
    snapshots = []
    if output.is_dir():
        # Names only; cap the inventory so a malformed run cannot cause a large read.
        snapshots = sorted((p.name for p in output.iterdir()
                            if p.is_file() and re.fullmatch(r"snapshot_\d+\.hdf5", p.name)),
                           key=lambda n: int(re.search(r"\d+", n).group()))[:10000]
    usedvalues = ((output / "parameters-usedvalues").is_file() or
                  (root / ".gizmo_run.param-usedvalues").is_file())
    final_time = bool(times and times[-1] >= expected_time - 1e-9)

    active = False
    try:
        scripts_dir = Path(__file__).resolve().parents[1]
        if str(scripts_dir) not in sys.path:
            sys.path.insert(0, str(scripts_dir))
        from check_simulations.processes import find_processes
        process_info = find_processes(root)
        # The CLI command itself contains --run-root and must not self-report
        # as an active simulation.
        active = any("post_run_gate.py" not in str(item.get("args", ""))
                     for item in process_info.get("processes", []))
    except Exception:
        pass
    if active or text is None:
        verdict = "active_or_unknown"
    elif errors:
        verdict = "failed"
    elif terminal and final_time and len(snapshots) >= min_snapshots and usedvalues:
        verdict = "completed"
    elif snapshots or terminal or usedvalues:
        verdict = "partial"
    else:
        verdict = "active_or_unknown"
    return {"terminal_detected": terminal, "final_time_reached": final_time,
            "error_markers": errors, "snapshot_count": len(snapshots),
            "usedvalues_present": usedvalues, "verdict": verdict}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-root", required=True)
    parser.add_argument("--expected-time", required=True, type=float)
    parser.add_argument("--log")
    parser.add_argument("--min-snapshots", type=int, default=1)
    args = parser.parse_args()
    print(json.dumps(assess(args.run_root, args.expected_time, args.log, args.min_snapshots),
                     ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
