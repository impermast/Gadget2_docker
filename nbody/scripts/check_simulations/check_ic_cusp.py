#!/usr/bin/env python3
"""check_ic_cusp.py — IC-gate CLI (этап 3 рефакторинга анализа).

Математика гейта и вердикт живут в `analysis.loaders.ic.run_ic_gate`
(дословный порт этого же скрипта, сверка побайтно с baseline ic_gate/*).
График строится ТОЛЬКО через реестр (`plots/ic.py`: ic_gate_profile);
прямой matplotlib/savefig в check_simulations запрещён guard-тестом.

Usage:
  python3 check_ic_cusp.py <ic.hdf5> [--galic-dir DIR] [--outdir DIR]
                           [--nmin 200] [--rlo 0.3] [--rhi 3.0]

Exit code: 0 = PASS, 2 = FAIL, 1 = ошибка входных данных.
"""
import argparse
import os
import sys

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
SCRIPTS_DIR = os.path.dirname(SCRIPT_DIR)
for _p in (SCRIPT_DIR, SCRIPTS_DIR):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from analysis.loaders import (  # noqa: E402
    find_galic_dir,
    prepare_ic_figure_data,
    run_ic_gate,
)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("ic")
    ap.add_argument("--galic-dir", default=None)
    ap.add_argument("--outdir", default=None)
    ap.add_argument("--nmin", type=int, default=200)
    ap.add_argument("--rlo", type=float, default=0.3)
    ap.add_argument("--rhi", type=float, default=3.0)
    args = ap.parse_args()

    outdir = args.outdir or os.path.dirname(os.path.abspath(args.ic))
    galic_dir = find_galic_dir(args.ic, args.galic_dir)

    # Ввод-ошибки поднимают исключение -> незахваченный traceback = exit 1
    # (как в оригинале: ошибка входных данных != FAIL гейта).
    res = run_ic_gate(args.ic, galic_dir=galic_dir, outdir=outdir,
                      nmin=args.nmin, rlo=args.rlo, rhi=args.rhi)

    with open(os.path.join(outdir, "ic_gate_report.txt")) as fh:
        print(fh.read(), end="")

    # График — best-effort (не должен ломать gate), как и раньше.
    try:
        from analysis.plotter import NbodyPlotter
        plotter = NbodyPlotter(output_dir=outdir)
        plotter.register_defaults()
        plotter.make_plot(
            "ic_gate_profile",
            prepare_ic_figure_data(os.path.join(outdir, "ic_profiles.csv")),
            config={"gate_range": (args.rlo, args.rhi), "nmin": args.nmin})
    except Exception as exc:  # noqa: BLE001 - plot не должен ломать gate
        print(f"(plot skipped: {exc})")

    sys.exit(0 if res["gate_pass"] else 2)


if __name__ == "__main__":
    main()
