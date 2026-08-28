#!/usr/bin/env python3
"""Parameter readers for run-specific GIZMO files."""
from __future__ import annotations

from pathlib import Path
from typing import Dict, Optional

KEYS = [
    "TimeMax",
    "TimeBetSnapshot",
    "InitCondFile",
    "OutputDir",
    "DM_InteractionCrossSection",
    "DM_DissipationFactor",
    "DM_KickPerCollision",
    "DM_InteractionVelocityScale",
    "SofteningHalo",
]


def parse_param_file(path: str | Path) -> Dict[str, str]:
    p = Path(path)
    out: Dict[str, str] = {}
    if not p.exists():
        return out
    for raw in p.read_text(errors="replace").splitlines():
        line = raw.split("%", 1)[0].split("#", 1)[0].strip()
        if not line:
            continue
        parts = line.split()
        if len(parts) >= 2:
            out[parts[0]] = parts[1]
    return out


def _num(value: Optional[str]):
    if value is None:
        return None
    try:
        f = float(value)
        return int(f) if f.is_integer() else f
    except Exception:
        return value


def read_run_params(run_root: str | Path) -> Dict[str, object]:
    root = Path(run_root)
    runtime = parse_param_file(root / ".gizmo_run.param")
    used = parse_param_file(root / "output" / "parameters-usedvalues")
    merged = dict(runtime)
    merged.update(used)
    selected = {k: _num(merged.get(k)) for k in KEYS if k in merged}
    return {
        "runtime_param_exists": (root / ".gizmo_run.param").exists(),
        "usedvalues_exists": (root / "output" / "parameters-usedvalues").exists(),
        "runtime": {k: _num(v) for k, v in runtime.items() if k in KEYS},
        "used": {k: _num(v) for k, v in used.items() if k in KEYS},
        "selected": selected,
    }
