#!/usr/bin/env python3
"""Presentation visual morphology package for CDM/SIDM/dSIDM run groups.

The script is a thin integration layer around the registry-based plotting
architecture. It prepares plot-ready data with loaders.py and renders concrete
plots through NbodyPlotter. It can be launched while a group is still running:
runs without readable snapshots are skipped gracefully; metrics-series CSV is
used when available and final-snapshot profiles are computed for discovered
snapshots only.

Example:
    docker exec gadget-gizmo python3 /nbody/scripts/plot_scripts/compare_visual_morphology.py \
      --group-root /nbody/runs/test_dissipation_focused_T5 \
      --outdir /nbody/runs/test_dissipation_focused_T5/visual_compare
"""
from __future__ import annotations

import argparse
import csv
import math
import sys
import time
from pathlib import Path
from typing import Dict, List, Optional

import numpy as np

_HERE = Path(__file__).resolve().parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

from loaders import (  # noqa: E402
    phase_space_histogram,
    prepare_profile_data,
    prepare_visual_snapshot,
    projection_histograms,
    radial_morphology_profiles,
)
from plotter import create_plotter  # noqa: E402
from settings import PlotSettings, RunPaths  # noqa: E402


PREFERRED_ORDER = [
    "cdm_N1e5_T5",
    "sidm10_N1e5_T5",
    "dsidm5_f005_k0_N1e5_T5",
    "dsidm10_f005_k0_N1e5_T5",
    "dsidm10_f01_k0_N1e5_T5",
    "cdm_N1e5_T2",
    "sidm10_N1e5_T2",
    "dsidm5_f005_k0_N1e5_T2",
    "dsidm10_f005_k0_N1e5_T2",
    "dsidm10_f01_k0_N1e5_T2",
]


def short_label(name: str) -> str:
    label = name.replace("_N1e5", "").replace("_T5", "").replace("_T2", "")
    label = label.replace("dsidm", "dSIDM σ=").replace("sidm", "SIDM σ=").replace("cdm", "CDM")
    label = label.replace("_f005", ", f=0.05").replace("_f01", ", f=0.10").replace("_f02", ", f=0.20")
    label = label.replace("_k0", "")
    return label


def discover_runs(group_root: Path, explicit: Optional[List[str]]) -> List[Path]:
    if explicit:
        runs = [group_root / r if not Path(r).is_absolute() else Path(r) for r in explicit]
    else:
        runs = [p for p in group_root.iterdir() if p.is_dir() and (p / "output").exists()]
    order = {name: i for i, name in enumerate(PREFERRED_ORDER)}
    return sorted(runs, key=lambda p: (order.get(p.name, 999), p.name))


def read_last_metrics(run: Path, metrics_rel: str) -> Optional[Dict[str, float]]:
    path = run / metrics_rel
    if not path.exists():
        return None
    with path.open(newline="") as f:
        rows = list(csv.DictReader(f))
    if not rows:
        return None
    row = rows[-1]
    def flt(key: str, default: float = math.nan) -> float:
        try:
            return float(row.get(key, default))
        except Exception:
            return default
    ca = flt("ca_r5")
    thick = flt("z_rms_over_R_rms_r5")
    vrot = flt("vrot_over_sigma_r5")
    disk_score = 0.0
    if math.isfinite(ca):
        disk_score += max(0.0, 0.75 - ca)
    if math.isfinite(thick):
        disk_score += max(0.0, 0.55 - thick)
    if math.isfinite(vrot):
        disk_score += 0.5 * max(0.0, vrot - 0.15)
    return {
        "ca_final": ca,
        "thickness_final": thick,
        "vrot_final": vrot,
        "ninteractions_final": flt("ninteractions_total", 0.0),
        "disk_score": disk_score,
        "time": flt("time"),
    }


def metric_from_profile(profile: Dict[str, object], visual: Dict[str, object]) -> Dict[str, float]:
    radial = radial_morphology_profiles(visual, [5.0])
    ca = float(radial["ca"][0])
    thick = float(radial["thickness"][0])
    vrot = float(radial["vrot_over_sigma"][0])
    disk_score = 0.0
    if math.isfinite(ca):
        disk_score += max(0.0, 0.75 - ca)
    if math.isfinite(thick):
        disk_score += max(0.0, 0.55 - thick)
    if math.isfinite(vrot):
        disk_score += 0.5 * max(0.0, vrot - 0.15)
    ni = visual.get("ninteractions")
    return {
        "ca_final": ca,
        "thickness_final": thick,
        "vrot_final": vrot,
        "ninteractions_final": float(np.sum(ni)) if ni is not None else 0.0,
        "disk_score": disk_score,
        "time": float(profile.get("time", visual.get("time", math.nan))),
    }


def write_visual_summary(outdir: Path, rows: List[Dict[str, object]], made: List[Path], warnings: List[str]) -> Path:
    path = outdir / "visual_summary.txt"
    lines = [
        "VISUAL MORPHOLOGY PACKAGE SUMMARY",
        f"Runs used: {len(rows)}",
        "",
        "Final/available metrics:",
        "| run | time | c/a r<5 | z/R r<5 | |vrot|/sigma | NInteractions | disk_score |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for r in rows:
        lines.append(
            f"| {r['label']} | {float(r['time']):.3f} | {float(r['ca_final']):.3f} | "
            f"{float(r['thickness_final']):.3f} | {float(r['vrot_final']):.3f} | "
            f"{float(r['ninteractions_final']):.0f} | {float(r['disk_score']):.3f} |"
        )
    lines += ["", "Generated files:"]
    lines += [f"- {p.name} ({p.stat().st_size} bytes)" for p in made if p.exists()]
    if warnings:
        lines += ["", "Warnings/skips:"] + [f"- {w}" for w in warnings]
    lines += [
        "",
        "Interpretation note: this package is visual/comparative. A dark-disk claim requires thin edge-on morphology, low c/a and z/R, a coherent R-vphi branch, and significant rotation support versus CDM/SIDM controls.",
    ]
    path.write_text("\n".join(lines) + "\n")
    return path


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--group-root", required=True)
    ap.add_argument("--runs", nargs="*", default=None, help="Run names relative to group root; default: discover output dirs")
    ap.add_argument("--outdir", default=None)
    ap.add_argument("--ptype", type=int, default=3)
    ap.add_argument("--nmax", type=int, default=None, help="Optional particle subsample for maps/phase-space")
    ap.add_argument("--lim", type=float, default=12.0)
    ap.add_argument("--bins", type=int, default=220)
    ap.add_argument("--phase-bins", type=int, default=180)
    ap.add_argument("--metrics-rel", default="partial_analysis/metrics_series.csv")
    args = ap.parse_args()

    t0 = time.time()
    group_root = Path(args.group_root)
    outdir = Path(args.outdir) if args.outdir else group_root / "visual_compare"
    outdir.mkdir(parents=True, exist_ok=True)
    plotter = create_plotter(PlotSettings(), output_dir=outdir)

    labels, times, face, edge, phase, profiles, summaries = [], [], [], [], [], [], []
    warnings: List[str] = []
    phase_extent = None
    radii = np.logspace(np.log10(0.5), np.log10(args.lim), 28)
    profile_series = []
    compare_series = []

    for run in discover_runs(group_root, args.runs):
        try:
            rp = RunPaths(run)
            snap = rp.latest_snapshot()
        except Exception as exc:
            warnings.append(f"skip {run.name}: no snapshot ({exc})")
            continue
        try:
            visual = prepare_visual_snapshot(snap, ptype=args.ptype, nmax=args.nmax)
            prof = prepare_profile_data(snap, rcore=2.0)
        except Exception as exc:
            warnings.append(f"skip {run.name}: could not prepare data from {snap.name}: {exc}")
            continue
        label = short_label(run.name)
        hxy, hxz = projection_histograms(visual, bins=args.bins, lim=args.lim)
        ph, ext = phase_space_histogram(visual, rlim=args.lim, bins_r=args.phase_bins, bins_v=args.phase_bins)
        rad = radial_morphology_profiles(visual, radii)
        rad["label"] = label
        prof["label"] = label
        summary = read_last_metrics(run, args.metrics_rel) or metric_from_profile(prof, visual)
        summary["label"] = label
        labels.append(label); times.append(float(visual["time"]))
        face.append(hxy); edge.append(hxz); phase.append(ph); phase_extent = ext
        profile_series.append(rad); compare_series.append(prof); summaries.append(summary)
        print(f"[INFO] {label}: {snap.name} t={float(visual['time']):.3f}")

    if not labels:
        raise FileNotFoundError(f"No usable snapshots found under {group_root}")

    surface_data = {"labels": np.asarray(labels, dtype=object), "times": np.asarray(times), "faceon": np.stack(face), "edgeon": np.stack(edge)}
    jobs = {
        "visual_morphology_montage": {"data": surface_data, "config": {"lim": args.lim}},
        "morphology_profiles_compare": {"data": {"series": profile_series}},
        "phase_space_compare": {"data": {"labels": np.asarray(labels, dtype=object), "phase": np.stack(phase), "extent": np.asarray(phase_extent)}},
        "disk_dashboard": {"data": {
            "summary_labels": np.asarray(labels, dtype=object),
            "ca_final": np.asarray([s["ca_final"] for s in summaries], dtype=float),
            "thickness_final": np.asarray([s["thickness_final"] for s in summaries], dtype=float),
            "vrot_final": np.asarray([s["vrot_final"] for s in summaries], dtype=float),
            "ninteractions_final": np.asarray([s["ninteractions_final"] for s in summaries], dtype=float),
            "disk_score": np.asarray([s["disk_score"] for s in summaries], dtype=float),
        }},
    }
    if len(labels) >= 2:
        jobs["surface_density_residuals"] = {"data": surface_data, "config": {"lim": args.lim}}
        jobs["log_rho_compare"] = {"data": {"series": compare_series}, "config": {"filename": "06_log_rho_compare_final.png"}}
        jobs["rot_curve_compare"] = {"data": {"series": compare_series}, "config": {"filename": "07_rot_curve_compare_final.png"}}
    else:
        warnings.append("residual/profile delta plots skipped: need at least 2 usable runs")

    results = plotter.make_plots(jobs, output_dir=outdir)
    made = sorted({p for paths in results.values() for p in paths})
    summary_path = write_visual_summary(outdir, summaries, made, warnings)
    made.append(summary_path)

    print("=" * 72)
    print(f"VISUAL MORPHOLOGY DONE in {time.time() - t0:.1f}s -> {outdir}")
    for p in made:
        print(f"  - {p.name} ({p.stat().st_size:,} bytes)")
    if warnings:
        print("Warnings/skips:")
        for w in warnings:
            print(f"  - {w}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())