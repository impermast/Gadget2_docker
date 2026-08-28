#!/usr/bin/env python3
"""Simple ETA estimates for run monitoring."""
from __future__ import annotations

import math
from pathlib import Path
from typing import Dict, Optional


def read_state(path: str | Path) -> Dict[str, str]:
    p = Path(path)
    out: Dict[str, str] = {}
    if not p.exists():
        return out
    for raw in p.read_text(errors="replace").splitlines():
        if "=" in raw:
            k, v = raw.split("=", 1)
            out[k.strip()] = v.strip()
    return out


def estimate_eta(run_root, current_time: Optional[float], time_max: Optional[float], health: str) -> Dict[str, object]:
    state = read_state(Path(run_root) / "run.state")
    if health == "pathological":
        return {"available": False, "eta_min": None, "text": "unreliable: timestep pathology detected"}
    try:
        elapsed = float(state.get("ELAPSED_MIN", "nan"))
        cur = float(current_time)
        tmax = float(time_max)
    except Exception:
        return {"available": False, "eta_min": None, "text": "unavailable: insufficient elapsed/progress data"}
    if not all(math.isfinite(v) for v in [elapsed, cur, tmax]):
        return {"available": False, "eta_min": None, "text": "unavailable: insufficient elapsed/progress data"}
    if elapsed <= 0 or tmax <= 0 or cur <= 0:
        return {"available": False, "eta_min": None, "text": "unavailable: progress too small"}
    frac = min(max(cur / tmax, 0.0), 0.999999)
    if frac <= 0:
        return {"available": False, "eta_min": None, "text": "unavailable: zero progress"}
    eta = elapsed * (1.0 / frac - 1.0)
    return {"available": True, "eta_min": eta, "text": format_minutes(eta)}


def format_minutes(minutes: float) -> str:
    if minutes < 60:
        return f"~{minutes:.0f} min"
    h = int(minutes // 60)
    m = int(round(minutes - h * 60))
    return f"~{h}h {m}m"
