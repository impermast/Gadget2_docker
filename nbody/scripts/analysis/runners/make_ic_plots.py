#!/usr/bin/env python3
"""make_ic_plots.py — канонический CLI блока ic: IC-gate + gate-профиль.

Метрики считает loaders/ic.run_ic_gate() (математика check_ic_cusp.py
дословно, рисования в гейте нет); графики — реестр (plots/ic.py).
Выход ТОЛЬКО AnalysisPaths().ic_dir(<ic_name>) — флага --outdir НЕТ
(guard-тест test_runners_have_no_outdir_flags).

Пример:
    docker exec gadget-gizmo python3 /nbody/scripts/analysis/runners/make_ic_plots.py \\
        --ic /nbody/ics/corecusp_N1e7/corecusp_N1e7.hdf5
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

from analysis.loaders import (  # noqa: E402
    find_galic_dir, prepare_ic_figure_data, run_ic_gate)
from analysis.paths import AnalysisPaths  # noqa: E402
from analysis.plotter import NbodyPlotter  # noqa: E402
from analysis.registry import by_block, find  # noqa: E402
from analysis.style import PlotSettings  # noqa: E402


def check(cond: bool, msg: str) -> None:
    if not cond:
        print(f"[FAIL] {msg}")
        raise SystemExit(1)
    print(f"[OK] {msg}")


def _resolve_ic(path: Path) -> Path:
    """IC-файл: сам путь или единственный *.hdf5 внутри каталога."""
    if path.is_file():
        return path
    if path.is_dir():
        cands = sorted(path.glob("*.hdf5"))
        if len(cands) == 1:
            return cands[0]
        raise SystemExit(
            f"[FAIL] --ic каталог {path}: нужен 1 *.hdf5, найдено {len(cands)} "
            f"(укажите файл явно)")
    raise SystemExit(f"[FAIL] --ic {path} не существует")


def _ic_name(ic_file: Path) -> str:
    """Имя IC: каталог-родитель (nbody/ics/<name>/x.hdf5) или stem файла."""
    if ic_file.parent.name not in ("ics", "nbody", ""):
        return ic_file.parent.name
    return ic_file.stem


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--ic", required=True,
                    help="IC-файл .hdf5 или каталог с одним .hdf5")
    ap.add_argument("--galic-dir", default=None,
                    help="каталог вывода GalIC (rotcurve.txt); дефолт: авто-поиск")
    ap.add_argument("--plots", default=None,
                    help="подмножество имён реестра через запятую (дефолт: все ic)")
    ap.add_argument("--nmin", type=int, default=200)
    ap.add_argument("--rlo", type=float, default=0.3)
    ap.add_argument("--rhi", type=float, default=3.0)
    args = ap.parse_args()

    t0 = time.time()
    ic_file = _resolve_ic(Path(args.ic))
    name = _ic_name(ic_file)
    galic_dir = args.galic_dir or find_galic_dir(str(ic_file))

    wanted = None
    if args.plots:
        wanted = set()
        for raw in args.plots.split(","):
            n = raw.strip()
            if n:
                wanted.add(find(n).name)
    ic_names = [s.name for s in by_block("ic")]
    if wanted is not None:
        unknown = sorted(wanted - set(ic_names))
        if unknown:
            raise SystemExit(f"[FAIL] не ic-plots для этого runner'а: {unknown}")
        ic_names = [n for n in ic_names if n in wanted]

    outdir = AnalysisPaths().ic_dir(name)
    print(f"[INFO] ic={ic_file} -> {outdir}")

    res = run_ic_gate(str(ic_file), galic_dir=galic_dir, outdir=str(outdir),
                      nmin=args.nmin, rlo=args.rlo, rhi=args.rhi)
    print(f"[INFO] GATE: {'PASS' if res['gate_pass'] else 'FAIL'}")
    created = [outdir / "ic_gate_report.txt", outdir / "ic_gate.json",
               outdir / "ic_profiles.csv"]

    settings = PlotSettings()
    plotter = NbodyPlotter(settings=settings, renderer="matplotlib",
                           output_dir=outdir)
    plotter.register_defaults()
    fig_data = prepare_ic_figure_data(outdir / "ic_profiles.csv")
    jobs = {"ic_gate_profile": {
        "data": fig_data,
        "config": {"gate_range": (args.rlo, args.rhi), "nmin": args.nmin}}}
    jobs = {n: j for n, j in jobs.items() if n in ic_names}
    for paths in plotter.make_plots(jobs, output_dir=outdir).values():
        created.extend(paths)

    check(len(created) > 0, f"files were created ({len(created)})")
    for p in sorted(set(created)):
        check(p.exists() and p.stat().st_size > 0,
              f"{p.name}: exists, size={p.stat().st_size:,} bytes")
        check(p.parent == outdir, f"{p.name}: located directly in {outdir}")

    dt = time.time() - t0
    print(f"ALL CHECKS PASSED in {dt:.1f}s -> {outdir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
