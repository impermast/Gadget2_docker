#!/usr/bin/env python3
"""Process inspection helpers without psutil."""
from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Dict, List


def _relative_run_name(root: Path) -> str:
    parts = root.parts
    try:
        i = parts.index("runs")
        return "/".join(parts[i + 1:])
    except ValueError:
        return root.name


def find_processes(run_root: str | Path) -> Dict[str, object]:
    root = Path(run_root)
    abs_root = str(root)
    rel_name = _relative_run_name(root)
    leaf = root.name
    try:
        cp = subprocess.run(["ps", "-eo", "pid,ppid,args"], text=True, capture_output=True, check=False)
        lines = cp.stdout.splitlines()
    except Exception:
        lines = []
    matches: List[Dict[str, object]] = []
    for line in lines[1:]:
        if "/nbody/scripts/check_simulations/" in line:
            continue
        if " ps -eo pid,ppid,args" in line:
            continue
        matched = False
        if abs_root in line:
            matched = True
        if "run_sim.sh" in line and rel_name and rel_name in line:
            matched = True
        if "mpirun" in line and leaf and leaf in line:
            matched = True
        # GIZMO worker lines often only show '.gizmo_run.param', so they cannot
        # be safely attributed to a specific run without cwd inspection. We do
        # not count them here to avoid false positives.
        if not matched:
            continue
        parts = line.strip().split(None, 2)
        if len(parts) >= 3:
            matches.append({"pid": int(parts[0]), "ppid": int(parts[1]), "args": parts[2]})
    return {"active": bool(matches), "count": len(matches), "processes": matches}
