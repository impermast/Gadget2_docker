#!/usr/bin/env python3
"""make_run_plots.py — канонический CLI блока core: все core-plots одного run.

Логика перенесена из plot_scripts/run_full_test.py (фазы C/D/E дословно по
смыслу; фазы A/B-инфраструктуры покрыты pytest). Отличия от предка:
  --run-root            путь к прогону (обязателен, без дефолта-примера);
  --plots               подмножество имён реестра (дефолт: все core-plots);
  --frames/--nmax/--skip-analysis/--skip-animations — как раньше;
  выход                 ТОЛЬКО AnalysisPaths.run_dir(<run>) — флага --outdir НЕТ
                        (guard-тест test_runners_have_no_outdir_flags).

Пример:
    docker exec gadget-gizmo python3 /nbody/scripts/analysis/runners/make_run_plots.py \\
        --run-root /nbody/runs/corecusp_cdm_N1e7_T5 --plots density,log_slope
"""
from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

_HERE = Path(__file__).resolve().parent
for _p in (_HERE.parent.parent, _HERE.parent):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

from analysis.base import PlotValidationError  # noqa: E402
from analysis.loaders import (  # noqa: E402
    prepare_particle_snapshot, prepare_profile_data, prepare_series,
    write_summary)
from analysis.paths import AnalysisPaths  # noqa: E402
from analysis.plotter import NbodyPlotter  # noqa: E402
from analysis.registry import by_block, find  # noqa: E402
from analysis.style import PlotSettings, RunPaths, SimulationInfo  # noqa: E402


def check(cond: bool, msg: str) -> None:
    if not cond:
        print(f"[FAIL] {msg}")
        raise SystemExit(1)
    print(f"[OK] {msg}")


def verify_gif(path: Path) -> int:
    from PIL import Image
    with Image.open(path) as im:
        return getattr(im, "n_frames", 1)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--run-root", required=True)
    ap.add_argument("--plots", default=None,
                    help="подмножество имён реестра через запятую (дефолт: все core)")
    ap.add_argument("--frames", type=int, default=12)
    ap.add_argument("--nmax", type=int, default=80_000)
    ap.add_argument("--skip-analysis", action="store_true")
    ap.add_argument("--skip-animations", action="store_true")
    args = ap.parse_args()

    t0 = time.time()
    run = RunPaths(args.run_root)
    wanted = None
    if args.plots:
        wanted = set()
        for raw in args.plots.split(","):
            name = raw.strip()
            if name:
                wanted.add(find(name).name)  # валидация имени + подсказка при опечатке
    core_names = [s.name for s in by_block("core")]
    if wanted is not None:
        unknown = sorted(wanted - set(core_names))
        if unknown:
            raise SystemExit(f"[FAIL] не core-plots для этого runner'а: {unknown}")
        core_names = [n for n in core_names if n in wanted]

    outdir = AnalysisPaths().run_dir(run.root.name)
    print(f"[INFO] run={run.root} -> {outdir}")

    settings = PlotSettings()
    plotter = NbodyPlotter(settings=settings, renderer="matplotlib",
                           output_dir=outdir)
    plotter.register_defaults()

    info = SimulationInfo.from_snapshot(run.latest_snapshot())
    print(f"[INFO] SimulationInfo: {info}")
    created: list = []

    if not args.skip_analysis:
        snap = run.latest_snapshot()
        print(f"[INFO] snapshot: {snap.name}")
        prof = prepare_profile_data(snap, rcore=2.0)
        part = prepare_particle_snapshot(snap, ptype=info.particle_type,
                                         nmax=200_000)
        summary_path = outdir / "summary_analysis.txt"
        write_summary(snap, summary_path, rcore=2.0)
        created.append(summary_path)
        jobs = {
            "density": {"data": prof},
            "log_slope": {"data": prof},
            "sigma_v": {"data": prof},
            "interactions_radial": {"data": prof},
            "disk_edgeon": {"data": part,
                            "config": {"title": f"Edge-on density, "
                                       f"t={part['time']:.2f}"}},
        }
        jobs = {n: j for n, j in jobs.items() if n in core_names}
        for name, paths in plotter.make_plots(jobs, output_dir=outdir).items():
            created.extend(paths)

    if not args.skip_animations:
        series = prepare_series(run.output, ptype=info.particle_type,
                                nmax=args.nmax, max_frames=args.frames)
        anim_jobs = {
            "particles_2d": {"data": series,
                             "config": {"sigma_label": info.cross_section}},
            "particles_3d": {"data": series,
                             "config": {"label": f"{info.model} sigma={info.cross_section:g}"
                                        if info.cross_section else info.model}},
        }
        anim_jobs = {n: j for n, j in anim_jobs.items() if n in core_names}
        for name, paths in plotter.make_plots(anim_jobs, output_dir=outdir).items():
            created.extend(paths)

    check(len(created) > 0, f"files were created ({len(created)})")
    for p in sorted(set(created)):
        check(p.exists() and p.stat().st_size > 0,
              f"{p.name}: exists, size={p.stat().st_size:,} bytes")
        check(p.parent == outdir, f"{p.name}: located directly in {outdir}")
        if p.suffix == ".gif":
            n = verify_gif(p)
            check(n > 1, f"{p.name}: GIF contains {n} frames (>1)")

    dt = time.time() - t0
    print(f"ALL CHECKS PASSED in {dt:.1f}s -> {outdir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
