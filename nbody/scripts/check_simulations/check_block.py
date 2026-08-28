#!/usr/bin/env python3
"""Check a group directory containing multiple simulation runs."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Dict, List

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from check_run import build_report
from formatting import _fmt_float, send_tg


def find_runs(group_root: str | Path) -> List[Path]:
    root = Path(group_root)
    if not root.exists():
        return []
    runs = []
    for p in sorted(root.iterdir()):
        if not p.is_dir():
            continue
        if (p / "run.log").exists() or (p / "output").exists() or (p / ".gizmo_run.param").exists():
            runs.append(p)
    return runs


def make_table(reports: List[Dict[str, object]], group_root: str | Path) -> str:
    lines = ["CHECK-BLOCK REPORT", f"Group: {group_root}", ""]
    lines.append(f"{'RUN':34} {'STATUS':11} {'HEALTH':13} {'TIME/MAX':17} {'SNAPS':9} {'FLAGS'}")
    lines.append("-" * 100)
    compare_ready = True
    for r in reports:
        name = Path(str(r.get("run_root"))).name
        v = r.get("verdict", {}) or {}
        latest = (r.get("log", {}) or {}).get("latest") or {}
        sm = ((r.get("snapshots", {}) or {}).get("latest_metadata") or {})
        params = ((r.get("params", {}) or {}).get("selected", {}) or {})
        t = latest.get("time") or sm.get("time") or "N/A"
        tm = params.get("TimeMax", "N/A")
        snaps = r.get("snapshots", {}) or {}
        sn = f"{snaps.get('count', 0)}/{snaps.get('expected', 'N/A')}"
        flags = ",".join(v.get("flags") or []) or "-"
        lines.append(f"{name[:34]:34} {str(v.get('status','?')):11} {str(v.get('health','?')):13} {str(t)[:8]}/{str(tm)[:8]:8} {sn:9} {flags}")
        if v.get("status") != "completed" or v.get("health") == "pathological":
            compare_ready = False
    lines.append("")
    lines.append(f"COMPARE_READY: {'yes' if compare_ready and reports else 'no'}")
    if not compare_ready:
        lines.append("Reason: at least one run is incomplete/running/failed/pathological.")
    return "\n".join(lines)


def make_tg_block(reports: List[Dict[str, object]], group_root: str | Path) -> str:
    """Compact Telegram-safe block report: no wide tables."""
    group_name = Path(str(group_root)).name or str(group_root)
    lines = [f"🧪 check-block: {group_name}"]
    compare_ready = True
    for r in reports:
        name = Path(str(r.get("run_root"))).name
        v = r.get("verdict", {}) or {}
        latest = (r.get("log", {}) or {}).get("latest") or {}
        sm = ((r.get("snapshots", {}) or {}).get("latest_metadata") or {})
        params = ((r.get("params", {}) or {}).get("selected", {}) or {})
        snaps = r.get("snapshots", {}) or {}
        status = v.get("status", "?")
        health = v.get("health", "?")
        if health == "pathological":
            icon = "🔴"
        elif health == "degraded":
            icon = "🟠"
        elif status == "completed":
            icon = "✅"
        elif status == "running":
            icon = "🟢"
        else:
            icon = "⚪"
        t = latest.get("time") or sm.get("time")
        tm = params.get("TimeMax")
        flags = v.get("flags") or []
        lines.append("")
        lines.append(f"{icon} {name}")
        lines.append(f"status: {status}; health: {health}")
        lines.append(f"time: {_fmt_float(t)} / {_fmt_float(tm)}")
        lines.append(f"snaps: {snaps.get('count', 0)}/{snaps.get('expected', 'N/A')}")
        if latest.get("systemstep") is not None:
            lines.append(f"dt: {latest.get('systemstep')}")
        if flags:
            lines.append("flags: " + ", ".join(flags[:3]))
        if status != "completed" or health == "pathological":
            compare_ready = False
    lines.append("")
    lines.append(f"COMPARE_READY: {'yes' if compare_ready and reports else 'no'}")
    if not compare_ready:
        lines.append("reason: incomplete/running/failed/pathological run present")
    return "\n".join(lines)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--group-root", required=True, help="Directory containing run subdirectories")
    ap.add_argument("--format", choices=["human", "json", "tg"], default="human")
    ap.add_argument("--tg", action="store_true", help="Also send report via Telegram notifier")
    ap.add_argument("--ptype", type=int, default=3)
    args = ap.parse_args()
    runs = find_runs(args.group_root)
    reports = [build_report(p, mode="auto", ptype=args.ptype) for p in runs]
    if args.format == "json":
        text = json.dumps({"group_root": args.group_root, "runs": reports}, ensure_ascii=False, indent=2, sort_keys=True)
    elif args.format == "tg":
        text = make_tg_block(reports, args.group_root)
    else:
        text = make_table(reports, args.group_root)
    print(text)
    if args.tg or args.format == "tg":
        send_tg(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
