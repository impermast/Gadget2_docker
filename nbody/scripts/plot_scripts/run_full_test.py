#!/usr/bin/env python3
"""
run_full_test.py — integration/test runner нового plotting-слоя.

Запускает ВСЕ зарегистрированные production plots на реальном run и
сохраняет результаты непосредственно в <run>/plots/:

    docker exec gadget-gizmo python3 \
        /nbody/scripts/plot_scripts/run_full_test.py \
        --run-root /nbody/runs/sidm20_dwarf_N1e6_T5

Опции:
    --frames N       кадров в анимациях (default 12)
    --nmax N         частиц на кадр анимации (default 80000)
    --skip-analysis / --skip-animations / --skip-negative
    --outdir PATH    куда сохранять (default <run>/plots)
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

from base import PlotValidationError          # noqa: E402
from loaders import prepare_profile_data, prepare_series, write_summary  # noqa: E402
from plotter import (ALL_PLOTS, ANALYSIS_PLOTS, ANIMATION_PLOTS,   # noqa: E402
                     COMPARE_PLOTS, NbodyPlotter, UnknownPlotError,
                     UnsupportedRendererError)
from settings import PlotSettings, RunPaths, SimulationInfo           # noqa: E402


def check(cond: bool, msg: str) -> None:
    if not cond:
        print(f"[FAIL] {msg}")
        raise SystemExit(1)
    print(f"[OK] {msg}")


def verify_gif(path: Path) -> int:
    from PIL import Image
    with Image.open(path) as im:
        return getattr(im, "n_frames", 1)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--run-root", default="/nbody/runs/sidm20_dwarf_N1e6_T5")
    ap.add_argument("--outdir", default=None,
                    help="default: <run-root>/plots")
    ap.add_argument("--frames", type=int, default=12)
    ap.add_argument("--nmax", type=int, default=80_000)
    ap.add_argument("--skip-analysis", action="store_true")
    ap.add_argument("--skip-animations", action="store_true")
    ap.add_argument("--skip-negative", action="store_true")
    args = ap.parse_args()

    t0 = time.time()
    run = RunPaths(args.run_root)
    outdir = Path(args.outdir) if args.outdir else run.plots
    outdir.mkdir(parents=True, exist_ok=True)

    # ── Phase A: инфраструктура и introspection ─────────────────────────────
    print("=" * 72)
    print("PHASE A: infrastructure + introspection")
    print("=" * 72)

    try:
        NbodyPlotter(renderer="plotly")
        raise AssertionError("unsupported renderer was accepted")
    except UnsupportedRendererError as e:
        print(f"[OK] unsupported renderer rejected: {e}")

    settings = PlotSettings()
    plotter = NbodyPlotter(settings=settings, renderer="matplotlib",
                           output_dir=outdir)
    plotter.register_defaults()

    names = plotter.available_plots()
    expected = sorted(set(ALL_PLOTS))
    check(names == expected, f"registry contains all standard plots: {names}")

    try:
        plotter.get("no_such_plot")
        raise AssertionError("unknown plot accepted")
    except UnknownPlotError as e:
        print(f"[OK] unknown plot rejected: {e}")

    try:
        from analysis_plots import DensityPlot
        plotter.register(DensityPlot(settings))
        raise AssertionError("duplicate registration accepted")
    except Exception as e:
        if isinstance(e, AssertionError):
            raise
        print(f"[OK] duplicate registration rejected: {type(e).__name__}: {e}")

    print("\n" + plotter.describe() + "\n")

    info = SimulationInfo.from_snapshot(run.latest_snapshot())
    print(f"[INFO] SimulationInfo: {info}")

    created: list = []

    # ── Phase B: negative validation tests ──────────────────────────────────
    if not args.skip_negative:
        print("=" * 72)
        print("PHASE B: negative validation smoke-tests")
        print("=" * 72)
        bad_cases = [
            ("density", {"r": [[1.0, 2.0]] * 100, "rho": [1.0] * 100},
             "wrong shape (N,2) instead of (R,)"),
            ("density", {"r": [1.0, 2.0]}, "missing required field 'rho'"),
            ("particles_3d", {"positions": [[[1.0, 2.0]]], "times": [0.0]},
             "positions last axis 2 instead of 3"),
            ("sigma_v", {"r": [1.0], "sigma_v": ["a"]}, "non-numeric dtype"),
        ]
        for plot_name, data, why in bad_cases:
            try:
                plotter.make_plot(plot_name, data,
                                  config={"filename": "_must_not_exist.png"},
                                  output_dir="/tmp")
                raise SystemExit(f"[FAIL] {plot_name}: bad data passed validation ({why})")
            except PlotValidationError as e:
                first = str(e).splitlines()[0]
                check(plot_name in first or plot_name in str(e),
                      f"{plot_name}: validation error names the plot ({why})")
                print(f"       -> {first}")
        print()

    # ── Phase C: analysis plots на финальном snapshot ───────────────────────
    if not args.skip_analysis:
        print("=" * 72)
        print(f"PHASE C: analysis plots on final snapshot of {run.root.name}")
        print("=" * 72)
        snap = run.latest_snapshot()
        print(f"[INFO] final snapshot: {snap.name}")
        prof = prepare_profile_data(snap, rcore=2.0)
        summary_path = outdir / "summary_analysis.txt"
        print(f"[INFO] writing text summary -> {summary_path.name}")
        write_summary(snap, summary_path, rcore=2.0)
        created.append(summary_path)
        jobs = {
            "density": {"data": prof},
            "log_slope": {"data": prof},
            "sigma_v": {"data": prof},
            "interactions_radial": {"data": prof},
        }
        for name, paths in plotter.make_plots(jobs, output_dir=outdir).items():
            for p in paths:
                created.append(p)

    # ── Phase D: animations на серии snapshots ──────────────────────────────
    if not args.skip_animations:
        print("=" * 72)
        print(f"PHASE D: animation plots ({args.frames} frames, nmax={args.nmax})")
        print("=" * 72)
        series = prepare_series(run.output, ptype=info.particle_type,
                                nmax=args.nmax, max_frames=args.frames)
        print(f"[INFO] series: T={series['positions'].shape[0]} frames, "
              f"N={series['positions'].shape[1]} particles/frame")
        anim_jobs = {
            "particles_2d": {"data": series,
                             "config": {"sigma_label": info.cross_section}},
            "particles_3d": {"data": series,
                             "config": {"label": f"{info.model} sigma={info.cross_section:g}"
                                        if info.cross_section else info.model}},
        }
        for name, paths in plotter.make_plots(anim_jobs, output_dir=outdir).items():
            for p in paths:
                created.append(p)

    # ── Phase E: verification ────────────────────────────────────────────────
    print("=" * 72)
    print("PHASE E: output verification")
    print("=" * 72)
    check(len(created) > 0, f"files were created ({len(created)})")
    for p in sorted(set(created)):
        check(p.exists() and p.stat().st_size > 0,
              f"{p.name}: exists, size={p.stat().st_size:,} bytes")
        check(p.parent == outdir, f"{p.name}: located directly in {outdir}")
        if p.suffix == ".gif":
            n = verify_gif(p)
            check(n > 1, f"{p.name}: GIF contains {n} frames (>1)")

    dt = time.time() - t0
    print("=" * 72)
    print(f"ALL CHECKS PASSED in {dt:.1f}s")
    print(f"Output directory: {outdir}")
    for p in sorted(set(created)):
        print(f"  - {p.name} ({p.stat().st_size:,} bytes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
