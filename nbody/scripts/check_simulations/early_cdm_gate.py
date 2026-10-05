#!/usr/bin/env python3
"""early_cdm_gate.py — ранний гейт IC→первый snapshot (этап 3 рефакторинга).

Математика и вердикт: `analysis.loaders.prerun.run_early_gate` (дословный
порт main() этого же скрипта, сверка побайтно: report/gate.json/profiles.csv).
График строится ТОЛЬКО через реестр (`plots/prerun.py`: early_cusp_compare);
прямой matplotlib/savefig в check_simulations запрещён guard-тестом.

Usage:
  python3 early_cdm_gate.py --ic IC.hdf5 --snap snapshot_000.hdf5
      [--galic-dir DIR] [--run-log DIR/run.log] [--outdir DIR]

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
    prepare_early_figure_data,
    run_early_gate,
)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--ic", required=True)
    ap.add_argument("--snap", required=True)
    ap.add_argument("--galic-dir", default=None)
    ap.add_argument("--run-log", default=None)
    ap.add_argument("--outdir", default=None)
    ap.add_argument("--nmin", type=int, default=200)
    ap.add_argument("--rlo", type=float, default=0.3)
    ap.add_argument("--rhi", type=float, default=3.0)
    ap.add_argument("--drho-tol", type=float, default=0.05)    # 5% на центральную плотность
    ap.add_argument("--dslope-tol", type=float, default=0.20)  # размывание каспа
    args = ap.parse_args()

    outdir = args.outdir or os.path.dirname(os.path.abspath(args.snap))
    galic_dir = find_galic_dir(args.ic, args.galic_dir)

    res = run_early_gate(args.ic, args.snap, galic_dir=galic_dir,
                         outdir=outdir, run_log=args.run_log,
                         nmin=args.nmin, rlo=args.rlo, rhi=args.rhi,
                         drho_tol=args.drho_tol, dslope_tol=args.dslope_tol)

    with open(os.path.join(outdir, "report.txt")) as fh:
        print(fh.read(), end="")

    # График — best-effort (не должен ломать gate), как и раньше.
    try:
        from analysis.plotter import NbodyPlotter
        plotter = NbodyPlotter(output_dir=outdir)
        plotter.register_defaults()
        plotter.make_plot(
            "early_cusp_compare",
            prepare_early_figure_data(os.path.join(outdir, "profiles.csv")),
            config={"gate_range": (args.rlo, args.rhi),
                    "time": res.get("t_snap", 0.0),
                    "title": f"Early gate: IC vs snapshot "
                             f"(t={res.get('t_snap', 0.0):.4g})"})
    except Exception as exc:  # noqa: BLE001 - plot не должен ломать gate
        print(f"(plot skipped: {exc})")

    sys.exit(0 if res["gate_pass"] else 2)


if __name__ == "__main__":
    main()
