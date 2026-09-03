#!/usr/bin/env python3
"""Compare shape/thickness time-series diagnostics across several GIZMO runs.

Input is produced by ``analyze_series.py`` in each run directory:

    <run>/partial_analysis/metrics_series.csv

The script does not read HDF5 snapshots. It only aggregates CSV metrics,
writes a compact CSV/TXT report, and optionally sends the TXT report to
Telegram via the existing notifier.
"""
from __future__ import annotations

import argparse
import csv
import math
import sys
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Dict, Iterable, List, Optional

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from formatting import send_tg  # noqa: E402


KEYS = [
    "ca_r5",
    "ca_r10",
    "z_rms_over_R_rms_r5",
    "z_p68_over_R_p68_r5",
    "vrot_over_sigma_r5",
    "mean_vphi_r5",
    "rho_core_r2",
    "ninteractions_total",
    "interacted_fraction",
]


@dataclass
class ShapeSummary:
    run: str
    time_start: float
    time_final: float
    snapshots: int
    ca_r5_initial: float
    ca_r5_final: float
    ca_r5_min: float
    ca_r10_final: float
    thickness_r5_final: float
    thickness_p68_r5_final: float
    vrot_over_sigma_r5_final: float
    mean_vphi_r5_final: float
    rho_core_r2_growth: float
    ninteractions_final: int
    interacted_fraction_final: float
    disk_score: float
    verdict: str


def _float(row: Dict[str, str], key: str, default: float = math.nan) -> float:
    try:
        return float(row.get(key, default))
    except Exception:
        return default


def _int(row: Dict[str, str], key: str, default: int = 0) -> int:
    try:
        return int(float(row.get(key, default)))
    except Exception:
        return default


def read_metrics(path: Path) -> List[Dict[str, str]]:
    if not path.exists():
        raise FileNotFoundError(path)
    with path.open(newline="") as f:
        rows = list(csv.DictReader(f))
    if not rows:
        raise ValueError(f"empty metrics file: {path}")
    return rows


def summarize_run(run_root: Path, metrics_rel: str) -> ShapeSummary:
    rows = read_metrics(run_root / metrics_rel)
    first, last = rows[0], rows[-1]
    ca_series = [_float(r, "ca_r5") for r in rows]
    finite_ca = [x for x in ca_series if math.isfinite(x)]
    ca_min = min(finite_ca) if finite_ca else math.nan
    ca_i = _float(first, "ca_r5")
    ca_f = _float(last, "ca_r5")
    thick_f = _float(last, "z_rms_over_R_rms_r5")
    vrot_f = _float(last, "vrot_over_sigma_r5")
    rho0 = _float(first, "rho_core_r2")
    rhof = _float(last, "rho_core_r2")
    rho_growth = rhof / rho0 if rho0 and math.isfinite(rho0) and rho0 > 0 else math.nan

    # Heuristic score: lower c/a + lower thickness + stronger ordered rotation.
    # Not a discovery claim; it ranks candidates for follow-up simulations.
    disk_score = 0.0
    if math.isfinite(ca_f):
        disk_score += max(0.0, 0.75 - ca_f)
    if math.isfinite(thick_f):
        disk_score += max(0.0, 0.55 - thick_f)
    if math.isfinite(vrot_f):
        disk_score += 0.5 * max(0.0, vrot_f - 0.15)

    if disk_score >= 0.35 and math.isfinite(vrot_f) and vrot_f >= 0.25:
        verdict = "promising-disk-candidate"
    elif disk_score >= 0.2:
        verdict = "weak-flattening"
    else:
        verdict = "no-clear-disk"

    return ShapeSummary(
        run=run_root.name,
        time_start=_float(first, "time"),
        time_final=_float(last, "time"),
        snapshots=len(rows),
        ca_r5_initial=ca_i,
        ca_r5_final=ca_f,
        ca_r5_min=ca_min,
        ca_r10_final=_float(last, "ca_r10"),
        thickness_r5_final=thick_f,
        thickness_p68_r5_final=_float(last, "z_p68_over_R_p68_r5"),
        vrot_over_sigma_r5_final=vrot_f,
        mean_vphi_r5_final=_float(last, "mean_vphi_r5"),
        rho_core_r2_growth=rho_growth,
        ninteractions_final=_int(last, "ninteractions_total"),
        interacted_fraction_final=_float(last, "interacted_fraction"),
        disk_score=disk_score,
        verdict=verdict,
    )


def discover_runs(group_root: Path, requested: Optional[List[str]]) -> List[Path]:
    if requested:
        return [group_root / name for name in requested]
    return sorted(p for p in group_root.iterdir() if p.is_dir() and (p / "partial_analysis" / "metrics_series.csv").exists())


def fmt(x: float, nd: int = 3) -> str:
    if not math.isfinite(x):
        return "nan"
    return f"{x:.{nd}g}"


def write_summary_csv(summaries: List[ShapeSummary], path: Path) -> None:
    with path.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(asdict(summaries[0]).keys()))
        writer.writeheader()
        for row in summaries:
            writer.writerow(asdict(row))


def write_text_report(summaries: List[ShapeSummary], path: Path, group_root: Path) -> str:
    best = max(summaries, key=lambda s: s.disk_score)
    lines = [
        f"SHAPE/THICKNESS GROUP REPORT: {group_root.name}",
        "",
        "Run | t | c/a r<5 | z_rms/R r<5 | |vrot|/sigma | NI | score | verdict",
        "--- | --- | --- | --- | --- | --- | --- | ---",
    ]
    for s in summaries:
        lines.append(
            f"{s.run} | {fmt(s.time_final)} | {fmt(s.ca_r5_final)} "
            f"| {fmt(s.thickness_r5_final)} | {fmt(s.vrot_over_sigma_r5_final)} "
            f"| {s.ninteractions_final} | {fmt(s.disk_score)} | {s.verdict}"
        )
    lines.append("")
    if best.disk_score > 0:
        lines.append(f"Best disk-score candidate: {best.run} (score={fmt(best.disk_score)})")
    else:
        lines.append("Best disk-score candidate: none (all scores are 0)")
    lines += [
        "Interpretation: score is a follow-up ranking, not a detection claim.",
        "A robust dark disk would require low c/a, low z/R, and significant rotation support relative to controls.",
        f"CSV: {path.with_name('shape_summary.csv')}",
    ]
    text = "\n".join(lines) + "\n"
    path.write_text(text)
    return text


def plot_compare(group_root: Path, runs: List[Path], outdir: Path, metrics_rel: str) -> List[Path]:
    specs = [
        ("compare_ca_r5.png", "c/a r<5", "ca_r5"),
        ("compare_thickness_r5.png", "z_rms/R_rms r<5", "z_rms_over_R_rms_r5"),
        ("compare_rotation_support_r5.png", "|vrot|/sigma r<5", "vrot_over_sigma_r5"),
        ("compare_ninteractions.png", "NInteractions total", "ninteractions_total"),
        ("compare_rho_core_r2.png", "rho_core r<2", "rho_core_r2"),
    ]
    made: List[Path] = []
    for fname, title, key in specs:
        fig, ax = plt.subplots(figsize=(8.5, 5.0))
        for run in runs:
            rows = read_metrics(run / metrics_rel)
            t = [_float(r, "time") for r in rows]
            y = [_float(r, key) for r in rows]
            ax.plot(t, y, marker="o", lw=1.6, ms=3, label=run.name.replace("_N1e5_T2", ""))
        ax.set_title(title)
        ax.set_xlabel("Time [code units]")
        ax.set_ylabel(key)
        if key in {"ninteractions_total", "rho_core_r2"} and any(math.isfinite(v) and v > 0 for v in y):
            ax.set_yscale("log")
        ax.grid(True, alpha=0.3)
        ax.legend(frameon=False, fontsize=8)
        fig.tight_layout()
        p = outdir / fname
        fig.savefig(p, dpi=170)
        plt.close(fig)
        made.append(p)
    return made


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--group-root", required=True)
    ap.add_argument("--runs", nargs="*", default=None, help="Run names relative to group root; default: discover analyzed runs")
    ap.add_argument("--metrics-rel", default="partial_analysis/metrics_series.csv")
    ap.add_argument("--outdir", default=None)
    ap.add_argument("--tg", action="store_true", help="Send text report to Telegram")
    args = ap.parse_args()

    group_root = Path(args.group_root)
    outdir = Path(args.outdir) if args.outdir else group_root / "shape_compare"
    outdir.mkdir(parents=True, exist_ok=True)

    runs = discover_runs(group_root, args.runs)
    if not runs:
        raise FileNotFoundError(f"No analyzed runs found under {group_root}")
    summaries = [summarize_run(run, args.metrics_rel) for run in runs]
    summaries.sort(key=lambda s: (s.disk_score, s.ninteractions_final), reverse=True)

    csv_path = outdir / "shape_summary.csv"
    txt_path = outdir / "shape_summary.txt"
    write_summary_csv(summaries, csv_path)
    text = write_text_report(summaries, txt_path, group_root)
    made = plot_compare(group_root, runs, outdir, args.metrics_rel)

    print(text, end="")
    print("Generated files:")
    print(f"- {csv_path}")
    print(f"- {txt_path}")
    for p in made:
        print(f"- {p}")
    if args.tg:
        send_tg(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())