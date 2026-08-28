#!/usr/bin/env python3
"""Small parsers for GIZMO run.log files."""
from __future__ import annotations

import re
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Dict, List, Optional

SYNC_RE = re.compile(
    r"Sync-Point\s+(?P<sync>\d+),\s*Time:\s*(?P<time>[0-9.eE+-]+),\s*Systemstep:\s*(?P<step>[0-9.eE+-]+)"
)
BIN_RE = re.compile(
    r"(?:X\s+)?bin=(?P<bin>\d+)\s+(?P<noncells>\d+)\s+(?P<cells>\d+)\s+(?P<dt>[0-9.eE+-]+)"
)


@dataclass
class SyncPoint:
    sync_point: int
    time: float
    systemstep: float


@dataclass
class TimeBin:
    bin: int
    noncells: int
    cells: int
    dt: float


def _tail_text(path: Path, max_bytes: int = 2_000_000) -> str:
    if not path.exists():
        return ""
    size = path.stat().st_size
    with path.open("rb") as f:
        if size > max_bytes:
            f.seek(size - max_bytes)
        return f.read().decode("utf-8", errors="replace")


def parse_sync_points(log_path: str | Path, max_bytes: int = 2_000_000) -> List[SyncPoint]:
    text = _tail_text(Path(log_path), max_bytes=max_bytes)
    points: List[SyncPoint] = []
    for m in SYNC_RE.finditer(text):
        points.append(SyncPoint(int(m.group("sync")), float(m.group("time")), float(m.group("step"))))
    return points


def parse_latest_timebins(log_path: str | Path, max_bytes: int = 600_000) -> List[TimeBin]:
    text = _tail_text(Path(log_path), max_bytes=max_bytes)
    idx = text.rfind("Occupied timebins:")
    if idx < 0:
        return []
    block = text[idx:]
    bins: List[TimeBin] = []
    for line in block.splitlines():
        m = BIN_RE.search(line)
        if m:
            bins.append(TimeBin(
                bin=int(m.group("bin")),
                noncells=int(m.group("noncells")),
                cells=int(m.group("cells")),
                dt=float(m.group("dt")),
            ))
    return bins


def parse_log(log_path: str | Path) -> Dict[str, object]:
    path = Path(log_path)
    points = parse_sync_points(path)
    bins = parse_latest_timebins(path)
    latest: Optional[SyncPoint] = points[-1] if points else None
    previous: Optional[SyncPoint] = points[-6] if len(points) >= 6 else (points[0] if len(points) >= 2 else None)
    small_bins = [b for b in bins if b.dt <= 1e-6 and (b.noncells + b.cells) > 0]
    return {
        "exists": path.exists(),
        "path": str(path),
        "latest": asdict(latest) if latest else None,
        "previous_window": asdict(previous) if previous else None,
        "sync_points_seen_tail": len(points),
        "timebins": [asdict(b) for b in bins],
        "small_dt_bins": [asdict(b) for b in small_bins],
    }
