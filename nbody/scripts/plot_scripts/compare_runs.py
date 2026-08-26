#!/usr/bin/env python3
"""
compare_runs.py — сравнение нескольких прогонов через registry plot_scripts.

Замена legacy compare_all.py / analyze_halo.py --cdm --sidm:
строит density_compare, log_slope_compare, sigma_v_compare и
core_density_vs_sigma по финальным snapshot'ам указанных прогонов.

Пример:
    docker exec gadget-gizmo python3 /nbody/scripts/plot_scripts/compare_runs.py \
        --outdir /nbody/analyse/cdm_sidm_all --rcore 50 \
        /nbody/runs/cdm_N1e6 \
        /nbody/runs/sidm_sigma0.1_N1e6 \
        /nbody/runs/sidm_sigma1_N1e6 /nbody/runs/sidm_sigma2_N1e6 \
        /nbody/runs/sidm_sigma5_N1e6 \
        --labels CDM SIDM0.1 SIDM1 SIDM2 SIDM5

ВНИМАНИЕ: позиционные run-каталоги указывать ДО --labels (nargs='*' у
--labels жадно поглощает всё, что стоит после него).

Подписи серий берутся из --labels (по порядку) или из имени каталога.
core_density_vs_sigma строится, если среди прогонов есть SIDM (sigma>0).
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

_HERE = Path(__file__).resolve().parent
for _p in (_HERE, _HERE.parent):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

from loaders import prepare_profile_data                    # noqa: E402
from plotter import COMPARE_PLOTS, create_plotter           # noqa: E402
from settings import PlotSettings, RunPaths, SimulationInfo  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("runs", nargs="+", help="run root directories")
    ap.add_argument("--labels", nargs="*", default=None,
                    help="подписи серий (по порядку; default: имя каталога)")
    ap.add_argument("--outdir", default="/nbody/analyse/cdm_sidm_all")
    ap.add_argument("--rcore", type=float, default=50.0)
    ap.add_argument("--ptype", type=int, default=3)
    args = ap.parse_args()

    t0 = time.time()
    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    labels = args.labels or []
    if len(labels) < len(args.runs):
        labels += [Path(r).resolve().name for r in args.runs[len(labels):]]

    plotter = create_plotter(PlotSettings(), output_dir=outdir)

    series = []
    sigmas, rho_cores, used_labels = [], [], []
    for run_root, label in zip(args.runs, labels):
        run = RunPaths(run_root)
        snap = run.latest_snapshot()
        info = SimulationInfo.from_snapshot(snap, name=label,
                                            particle_type=args.ptype)
        prof = prepare_profile_data(snap, rcore=args.rcore)
        prof["label"] = label
        series.append(prof)
        print(f"[INFO] {label}: snap={snap.name} t={prof['time']:.3f} "
              f"sigma={prof['cross_section']:g} "
              f"rho_core(r<{args.rcore:g})={prof['rho_core']:.3e}")
        if info.cross_section and info.cross_section > 0:
            sigmas.append(info.cross_section)
            rho_cores.append(prof["rho_core"])
            used_labels.append(label)

    # Все compare-plots из registry: profile compare (3) + delta-графики
    # (log_rho_compare, rot_curve_compare) — последний элемент коллекции
    # (core_density_vs_sigma) обрабатывается отдельно ниже.
    profile_plot_names = [n for n in COMPARE_PLOTS
                          if n != "core_density_vs_sigma"]
    jobs = {name: {"data": {"series": series}} for name in profile_plot_names}
    results = plotter.make_plots(jobs, output_dir=outdir)

    if len(sigmas) >= 2:
        results["core_density_vs_sigma"] = plotter.make_plot(
            "core_density_vs_sigma",
            {"sigma": sigmas, "rho_core": rho_cores, "labels": used_labels},
            output_dir=outdir)
    else:
        print("[WARN] core_density_vs_sigma skipped: нужно >=2 SIDM-прогонов "
              "с sigma>0")

    created = sorted({p for paths in results.values() for p in paths})
    print("=" * 72)
    print(f"COMPARE DONE in {time.time() - t0:.1f}s -> {outdir}")
    for p in created:
        print(f"  - {p.name} ({p.stat().st_size:,} bytes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
