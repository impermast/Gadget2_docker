#!/usr/bin/env python3
"""Status and health classification for simulation checks."""
from __future__ import annotations

from typing import Dict, List, Optional


def _f(x) -> Optional[float]:
    try:
        return float(x)
    except Exception:
        return None


def classify(report: Dict[str, object]) -> Dict[str, object]:
    flags: List[str] = []
    procs = report.get("processes", {}) or {}
    params = ((report.get("params", {}) or {}).get("selected", {}) or {})
    log = report.get("log", {}) or {}
    latest = log.get("latest") or {}
    snaps = report.get("snapshots", {}) or {}
    snap_meta = snaps.get("latest_metadata") or {}

    time_max = _f(params.get("TimeMax"))
    cur_time = _f(latest.get("time")) or _f(snap_meta.get("time"))
    systemstep = _f(latest.get("systemstep"))
    sync = _f(latest.get("sync_point"))

    if systemstep is not None:
        if systemstep < 1e-6:
            flags.append("timestep-collapse")
        elif systemstep < 1e-5:
            flags.append("small-systemstep")
    if sync is not None and time_max and cur_time is not None:
        if sync > 1_000_000 and cur_time < 0.95 * time_max:
            flags.append("syncpoint-runaway")
    if log.get("small_dt_bins"):
        flags.append("low-dt-timebins")

    prev = log.get("previous_window") or {}
    prev_time = _f(prev.get("time"))
    prev_sync = _f(prev.get("sync_point"))
    if prev_time is not None and cur_time is not None and prev_sync is not None and sync is not None:
        if (sync - prev_sync) >= 1000 and abs(cur_time - prev_time) < 1e-4:
            flags.append("stalled-time-progress")

    status = "unknown"
    state = report.get("state", {}) or {}
    state_status = str(state.get("STATUS", "")).lower()
    if state_status in {"completed", "failed", "running", "stopped"}:
        status = state_status
    if procs.get("active"):
        status = "running"
    if status in {"unknown", "stopped"}:
        complete_by_time = bool(time_max and cur_time is not None and cur_time >= 0.995 * time_max)
        complete_by_snaps = snaps.get("expected") and snaps.get("count", 0) >= int(snaps.get("expected") or 0) - 1
        if complete_by_time or complete_by_snaps:
            status = "completed"
        elif snaps.get("count", 0) > 0:
            status = "incomplete"

    if any(f in flags for f in ["timestep-collapse", "syncpoint-runaway", "stalled-time-progress"]):
        health = "pathological"
    elif any(f in flags for f in ["small-systemstep", "low-dt-timebins"]):
        health = "degraded"
    elif status in {"completed", "running"}:
        health = "ok"
    else:
        health = "unknown"

    confidence = "final" if status == "completed" and health != "pathological" else "preliminary"
    if status == "failed":
        confidence = "final"

    if health == "pathological":
        rec = "Не считать run нормальным; ETA ненадёжен. Имеет смысл остановить/перезапустить с более мягкими параметрами, если это не целевой failure test."
    elif status == "running":
        rec = "Продолжать мониторинг; итоговый физический вывод пока предварительный."
    elif status == "completed":
        rec = "Run готов к финальному анализу; можно запускать стандартный plotting pipeline, если summary ещё нет."
    elif status == "incomplete":
        rec = "Run неполный; проверить логи и параметры перед анализом."
    else:
        rec = "Недостаточно данных; проверь run.log/output/run.state."

    return {
        "status": status,
        "health": health,
        "confidence": confidence,
        "flags": sorted(set(flags)),
        "recommendation": rec,
    }
