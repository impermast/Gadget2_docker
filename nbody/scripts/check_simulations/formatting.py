#!/usr/bin/env python3
"""Human and Telegram formatting."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Dict, List


def _fmt_float(x, nd=4):
    if x is None:
        return "N/A"
    try:
        return f"{float(x):.{nd}g}"
    except Exception:
        return str(x)


def make_human(report: Dict[str, object], compact: bool = False) -> str:
    verdict = report.get("verdict", {}) or {}
    params = ((report.get("params", {}) or {}).get("selected", {}) or {})
    log = report.get("log", {}) or {}
    latest = log.get("latest") or {}
    snaps = report.get("snapshots", {}) or {}
    snap_meta = snaps.get("latest_metadata") or {}
    eta = report.get("eta", {}) or {}
    procs = report.get("processes", {}) or {}

    t_cur = latest.get("time") or snap_meta.get("time")
    t_max = params.get("TimeMax")
    progress = None
    try:
        progress = 100.0 * float(t_cur) / float(t_max)
    except Exception:
        pass

    title = "CHECK-RUN REPORT"
    if compact:
        title = "🧪 check-run"
    lines: List[str] = [title, f"Run: {report.get('run_root')}"]
    lines.append(f"Status: {verdict.get('status', 'unknown')} | Health: {verdict.get('health', 'unknown')} | Confidence: {verdict.get('confidence', 'preliminary')}")
    if progress is not None:
        lines.append(f"Time: {_fmt_float(t_cur)} / {_fmt_float(t_max)} ({progress:.1f}%)")
    else:
        lines.append(f"Time: {_fmt_float(t_cur)} / {_fmt_float(t_max)}")
    lines.append(f"Snapshots: {snaps.get('count', 0)} / expected {snaps.get('expected', 'N/A')} | latest: {snaps.get('latest_name') or 'N/A'}")
    lines.append(f"Sync-Point: {latest.get('sync_point', 'N/A')} | Systemstep: {latest.get('systemstep', 'N/A')}")
    lines.append(f"Processes: {'active' if procs.get('active') else 'not found'} ({procs.get('count', 0)})")
    if params:
        key_parts = []
        for k in ["DM_InteractionCrossSection", "DM_DissipationFactor", "DM_KickPerCollision", "TimeBetSnapshot"]:
            if k in params:
                key_parts.append(f"{k}={params[k]}")
        if key_parts:
            lines.append("Params: " + ", ".join(key_parts))
    if snap_meta:
        ni = snap_meta.get("ninteractions_total")
        frac = snap_meta.get("particles_interacted_fraction")
        if ni is not None:
            frac_s = f" ({100*float(frac):.2f}% particles)" if frac is not None else ""
            lines.append(f"NInteractions latest: {ni}{frac_s}")
        elif snap_meta.get("ninteractions_present") is False:
            lines.append("NInteractions latest: not present")
    flags = verdict.get("flags") or []
    lines.append("Flags: " + (", ".join(flags) if flags else "none"))
    lines.append(f"ETA: {eta.get('text', 'unavailable')}")
    lines.append("Recommendation: " + str(verdict.get("recommendation", "N/A")))
    return "\n".join(lines)


def make_tg_run(report: Dict[str, object]) -> str:
    """Compact Telegram-safe single-run report.

    Telegram clients wrap wide monospace-like tables poorly, so keep every line
    short and avoid alignment-dependent formatting.
    """
    verdict = report.get("verdict", {}) or {}
    params = ((report.get("params", {}) or {}).get("selected", {}) or {})
    log = report.get("log", {}) or {}
    latest = log.get("latest") or {}
    snaps = report.get("snapshots", {}) or {}
    snap_meta = snaps.get("latest_metadata") or {}
    eta = report.get("eta", {}) or {}
    procs = report.get("processes", {}) or {}

    run_name = Path(str(report.get("run_root", ""))).name or str(report.get("run_root"))
    t_cur = latest.get("time") or snap_meta.get("time")
    t_max = params.get("TimeMax")
    progress = None
    try:
        progress = 100.0 * float(t_cur) / float(t_max)
    except Exception:
        pass

    status = verdict.get("status", "unknown")
    health = verdict.get("health", "unknown")
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

    lines: List[str] = [
        f"{icon} check-run: {run_name}",
        f"status: {status}",
        f"health: {health}",
    ]
    if progress is not None:
        lines.append(f"time: {_fmt_float(t_cur)} / {_fmt_float(t_max)} ({progress:.1f}%)")
    else:
        lines.append(f"time: {_fmt_float(t_cur)} / {_fmt_float(t_max)}")
    lines.append(f"snaps: {snaps.get('count', 0)}/{snaps.get('expected', 'N/A')}")
    lines.append(f"sync: {latest.get('sync_point', 'N/A')}")
    lines.append(f"dt: {latest.get('systemstep', 'N/A')}")
    lines.append(f"proc: {'active' if procs.get('active') else 'none'}")

    sigma = params.get("DM_InteractionCrossSection")
    diss = params.get("DM_DissipationFactor")
    kick = params.get("DM_KickPerCollision")
    if sigma is not None or diss is not None or kick is not None:
        lines.append(f"params: σ={sigma}, f={diss}, kick={kick}")

    ni = snap_meta.get("ninteractions_total") if snap_meta else None
    frac = snap_meta.get("particles_interacted_fraction") if snap_meta else None
    if ni is not None:
        frac_s = f", {100*float(frac):.2f}%" if frac is not None else ""
        lines.append(f"NI: {ni}{frac_s}")

    flags = verdict.get("flags") or []
    if flags:
        lines.append("flags:")
        for flag in flags[:6]:
            lines.append(f"- {flag}")
    else:
        lines.append("flags: none")
    lines.append(f"ETA: {eta.get('text', 'unavailable')}")
    lines.append("next: " + str(verdict.get("recommendation", "N/A")))
    return "\n".join(lines)


def emit_report(report: Dict[str, object], fmt: str = "human", tg: bool = False) -> int:
    if fmt == "json":
        text = json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True)
    elif fmt == "tg":
        text = make_tg_run(report)
    else:
        text = make_human(report, compact=False)
    print(text)
    if tg or fmt == "tg":
        send_tg(text)
    return 0


def send_tg(text: str) -> None:
    code = (
        "import sys; sys.path.insert(0, '/nbody/tg'); "
        "from tg_notify import TgNotify; "
        "TgNotify().send_message(sys.stdin.read(), parse_mode=None)"
    )
    try:
        cp = subprocess.run([sys.executable, "-c", code], input=text, text=True, capture_output=True, check=False, timeout=20)
        if cp.returncode != 0:
            print(f"[WARN] Telegram notification failed: {cp.stderr.strip() or cp.stdout.strip()}", file=sys.stderr)
    except Exception as e:
        print(f"[WARN] Telegram notification failed: {e}", file=sys.stderr)
