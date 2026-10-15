#!/usr/bin/env python3
"""make_campaign_morphology_plots.py — runner блока campaigns: морфология группы.

Перенос plot_scripts/compare_visual_morphology.py (логика дословно):
  visual_morphology_montage, surface_density_residuals,
  morphology_profiles_compare, phase_space_compare, disk_dashboard.

Отличия от предка:
  --campaign   ОБЯЗАТЕЛЬНО: имя кампании (валидированный сегмент пути);
  --member     подкаталог внутри кампании (дефолт morphology);
  --runs       имена прогонов внутри --group-root (дефолт: автопоиск output/);
  --plots      подмножество имён реестра (дефолт: все plots этого runner'а);
  выход        ТОЛЬКО AnalysisPaths.campaign_dir(campaign, member) — флага
               --outdir НЕТ (guard-тест test_runners_have_no_outdir_flags).
profile-compare plots (log_rho_compare/rot_curve_compare) строит
make_campaign_plots.py, чтобы не дублировать артефакты.

Пример:
    docker exec gadget-gizmo python3 \\
        /nbody/scripts/analysis/runners/make_campaign_morphology_plots.py \\
        --group-root /nbody/runs/dsidm_spin_k08_transition \\
        --campaign dsidm_spin --member morphology
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
for _p in (_HERE.parent.parent, _HERE.parent):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

from analysis.loaders import (  # noqa: E402
    phase_space_histogram,
    prepare_profile_data,
    prepare_visual_snapshot,
    projection_histograms,
    radial_morphology_profiles,
    resolve_metrics_path,
)
from analysis.labels import compact_run_label  # noqa: E402
from analysis.paths import AnalysisPaths  # noqa: E402
from analysis.plotter import NbodyPlotter  # noqa: E402
from analysis.registry import find  # noqa: E402
from analysis.style import PlotSettings, RunPaths  # noqa: E402

# Plots, которые строит именно этот runner.
OWN_PLOTS = (
    "visual_morphology_montage",
    "surface_density_residuals",
    "morphology_profiles_compare",
    "phase_space_compare",
    "disk_dashboard",
)

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
    return compact_run_label(name)


def discover_runs(group_root: Path, explicit: Optional[List[str]]) -> List[Path]:
    if explicit:
        runs = [group_root / r if not Path(r).is_absolute() else Path(r) for r in explicit]
    else:
        runs = [p for p in group_root.iterdir() if p.is_dir() and (p / "output").exists()]
    order = {name: i for i, name in enumerate(PREFERRED_ORDER)}
    return sorted(runs, key=lambda p: (order.get(p.name, 999), p.name))


def read_last_metrics(run: Path, metrics_rel: str) -> Optional[Dict[str, object]]:
    path = resolve_metrics_path(run, metrics_rel)
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
        "metrics_source": str(path),
    }


def metric_from_profile(profile: Dict[str, object],
                        visual: Dict[str, object]) -> Dict[str, float]:
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


def write_visual_summary(outdir: Path, rows: List[Dict[str, object]],
                         made: List[Path], warnings: List[str],
                         nmax: Optional[int]) -> Path:
    path = outdir / "visual_summary.txt"
    lines = [
        "VISUAL MORPHOLOGY PACKAGE SUMMARY",
        f"Runs used: {len(rows)}",
        "",
        "Final/available metrics:",
        "| run | plot label | metrics source | time | c/a r<5 | z/R r<5 | "
        "|vrot|/sigma | NInteractions | exploratory score (not classifier) |",
        "|---|---|---|---:|---:|---:|---:|---:|---:|",
    ]
    for r in rows:
        lines.append(
            f"| {r['run']} | {r['label']} | {r['metrics_source']} | "
            f"{float(r['time']):.3f} | {float(r['ca_final']):.3f} | "
            f"{float(r['thickness_final']):.3f} | {float(r['vrot_final']):.3f} | "
            f"{float(r['ninteractions_final']):.0f} | {float(r['disk_score']):.3f} |"
        )
    sample_note = "all particles" if not nmax else f"random sample, nmax={nmax}"
    lines += ["", "Generated files:"]
    lines += [f"- {p.name} ({p.stat().st_size} bytes)" for p in made if p.exists()]
    if warnings:
        lines += ["", "Warnings/skips:"] + [f"- {w}" for w in warnings]
    lines += [
        "",
        f"Morphology maps and radial profiles use {sample_note} from the latest snapshot.",
        "Dashboard metrics prefer the canonical metrics_series.csv resolved from "
        "the run-local or analysis/prerun location; the source is reported per run. "
        "If unavailable, they are recomputed from the plotted particle sample.",
        "Radial-profile curves use the separate radial_morphology_profiles estimator; "
        "do not read their vrot/sigma values as canonical series metrics. Use one "
        "estimator consistently for numerical comparisons.",
        "Surface-density residuals use 7x7-pixel box smoothing and a shared symmetric "
        "99th-percentile scale (bounded to 0.05-1 dex); exact zero-residual controls "
        "are omitted from that panel only.",
        "The disk_score column is an exploratory rank, not a detector or acceptance test. "
        "Reference cuts c/a<0.75, z/R<0.55, vrot/sigma>0.15 are provisional guides "
        "and are not calibrated for this IC. A dark-disk claim also requires thin "
        "edge-on morphology, a coherent R-vphi branch, and comparison with controls.",
    ]
    path.write_text("\n".join(lines) + "\n")
    return path


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--group-root", required=True)
    ap.add_argument("--campaign", required=True,
                    help="имя кампании (один сегмент пути)")
    ap.add_argument("--member", default="morphology",
                    help="подкаталог внутри кампании (default: morphology)")
    ap.add_argument("--runs", nargs="*", default=None,
                    help="Run names relative to group root; default: discover output dirs")
    ap.add_argument("--plots", default=None,
                    help="подмножество имён реестра (дефолт: все plots этого runner'а)")
    ap.add_argument("--ptype", type=int, default=3)
    ap.add_argument("--nmax", type=int, default=None,
                    help="Optional particle subsample for maps/phase-space")
    ap.add_argument("--lim", type=float, default=12.0)
    ap.add_argument("--bins", type=int, default=220)
    ap.add_argument("--phase-bins", type=int, default=180)
    ap.add_argument("--metrics-rel", default="partial_analysis/metrics_series.csv")
    args = ap.parse_args()

    t0 = time.time()
    outdir = AnalysisPaths().campaign_dir(args.campaign, args.member)
    print(f"[INFO] campaign={args.campaign}/{args.member} -> {outdir}")

    wanted = set(OWN_PLOTS)
    if args.plots:
        wanted = set()
        for raw in args.plots.split(","):
            name = raw.strip()
            if not name:
                continue
            spec = find(name)  # валидация имени + подсказка при опечатке
            if name not in OWN_PLOTS:
                raise SystemExit(
                    f"[FAIL] '{name}' строится не этим runner'ом, а {spec.runner}")
            wanted.add(name)

    group_root = Path(args.group_root)
    plotter = NbodyPlotter(PlotSettings(), renderer="matplotlib",
                           output_dir=outdir)
    plotter.register_defaults()

    labels, times, face, edge, phase, summaries = [], [], [], [], [], []
    warnings: List[str] = []
    phase_extent = None
    radii = np.logspace(np.log10(0.5), np.log10(args.lim), 28)
    profile_series = []

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
            warnings.append(f"skip {run.name}: could not prepare data from "
                            f"{snap.name}: {exc}")
            continue
        label = short_label(run.name)
        hxy, hxz = projection_histograms(visual, bins=args.bins, lim=args.lim)
        ph, ext = phase_space_histogram(visual, rlim=args.lim,
                                        bins_r=args.phase_bins,
                                        bins_v=args.phase_bins)
        rad = radial_morphology_profiles(visual, radii)
        rad["label"] = label
        prof["label"] = label
        summary = read_last_metrics(run, args.metrics_rel)
        if summary is None:
            summary = metric_from_profile(prof, visual)
            summary["metrics_source"] = f"visual particle sample (n={len(visual['positions'])})"
        else:
            summary["metrics_source"] = f"canonical series: {summary['metrics_source']}"
        summary["run"] = run.name
        summary["label"] = label
        labels.append(label)
        times.append(float(visual["time"]))
        face.append(hxy)
        edge.append(hxz)
        phase.append(ph)
        phase_extent = ext
        profile_series.append(rad)
        summaries.append(summary)
        print(f"[INFO] {label}: {snap.name} t={float(visual['time']):.3f}")

    if not labels:
        raise SystemExit(f"[FAIL] No usable snapshots found under {group_root}")

    surface_data = {
        "labels": np.asarray(labels, dtype=object),
        "times": np.asarray(times),
        "faceon": np.stack(face),
        "edgeon": np.stack(edge),
    }
    all_jobs = {
        "visual_morphology_montage": {"data": surface_data,
                                     "config": {"lim": args.lim}},
        "morphology_profiles_compare": {"data": {"series": profile_series}},
        "phase_space_compare": {
            "data": {"labels": np.asarray(labels, dtype=object),
                     "phase": np.stack(phase),
                     "extent": np.asarray(phase_extent)}},
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
        all_jobs["surface_density_residuals"] = {
            "data": surface_data, "config": {"lim": args.lim}}
    else:
        warnings.append("residual maps skipped: need at least 2 usable runs")

    jobs = {n: j for n, j in all_jobs.items() if n in wanted}
    if not jobs:
        raise SystemExit("[FAIL] не осталось plots после фильтра --plots")
    results = plotter.make_plots(jobs, output_dir=outdir)
    made = sorted({p for paths in results.values() for p in paths})
    summary_path = write_visual_summary(outdir, summaries, made, warnings,
                                        nmax=args.nmax)
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
