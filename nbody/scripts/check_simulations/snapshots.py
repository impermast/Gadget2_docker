#!/usr/bin/env python3
"""Cheap snapshot inventory and metadata readers."""
from __future__ import annotations

import glob
import re
from pathlib import Path
from typing import Dict, Optional

try:
    import h5py
except Exception:  # pragma: no cover
    h5py = None


def _snap_num(path: str) -> int:
    m = re.search(r"snapshot_?(\d+)\.hdf5$", Path(path).name)
    return int(m.group(1)) if m else -1


def list_snapshots(run_root: str | Path):
    out = Path(run_root) / "output"
    return sorted(glob.glob(str(out / "snapshot_*.hdf5")), key=_snap_num)


def latest_snapshot_metadata(path: str | Path, ptype: int = 3, read_interactions: bool = True) -> Dict[str, object]:
    p = Path(path)
    meta: Dict[str, object] = {"path": str(p), "exists": p.exists()}
    if not p.exists() or h5py is None:
        meta["h5py_available"] = h5py is not None
        return meta
    try:
        with h5py.File(p, "r") as f:
            h = f["Header"].attrs
            meta["time"] = float(h.get("Time", 0.0))
            meta["cross_section"] = float(h.get("DM_InteractionCrossSection", 0.0))
            gname = f"PartType{ptype}"
            if gname not in f:
                pts = [k for k in f.keys() if k.startswith("PartType")]
                if pts:
                    gname = sorted(pts)[-1]
                else:
                    meta["particle_group"] = None
                    return meta
            g = f[gname]
            meta["particle_group"] = gname
            counts = h.get("NumPart_ThisFile")
            if counts is not None:
                idx = int(gname.replace("PartType", ""))
                meta["particles_header"] = int(counts[idx]) if idx < len(counts) else None
            if "Coordinates" in g:
                meta["particles_dataset"] = int(g["Coordinates"].shape[0])
            if "NInteractions" in g:
                meta["ninteractions_present"] = True
                if read_interactions:
                    ni = g["NInteractions"][:]
                    nz = int((ni > 0).sum())
                    total = int(ni.sum())
                    n = int(ni.shape[0])
                    meta["ninteractions_total"] = total
                    meta["particles_interacted"] = nz
                    meta["particles_interacted_fraction"] = (nz / n) if n else None
            else:
                meta["ninteractions_present"] = False
    except Exception as e:
        meta["error"] = str(e)
    return meta


def inspect_snapshots(run_root: str | Path, time_max=None, time_bet=None, ptype: int = 3) -> Dict[str, object]:
    snaps = list_snapshots(run_root)
    latest = snaps[-1] if snaps else None
    expected: Optional[int] = None
    try:
        if time_max is not None and time_bet not in (None, 0):
            expected = int(float(time_max) / float(time_bet) + 1.0000001)
    except Exception:
        expected = None
    return {
        "count": len(snaps),
        "expected": expected,
        "latest": latest,
        "latest_name": Path(latest).name if latest else None,
        "latest_metadata": latest_snapshot_metadata(latest, ptype=ptype) if latest else None,
    }
