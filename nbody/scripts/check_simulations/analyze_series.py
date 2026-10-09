#!/usr/bin/env python3
"""Compatibility CLI for partial-series diagnostics.

Metric computation and plotting live in ``analysis.loaders`` and the canonical
``make_prerun_plots.py`` runner. Historical ``--run-root``/``--run`` and common
metric/plot options are forwarded; arbitrary ``--outdir`` is not supported.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
ANALYSIS_ROOT = SCRIPT_DIR.parent / "analysis"
SCRIPTS_ROOT = SCRIPT_DIR.parent
for _path in (ANALYSIS_ROOT, SCRIPTS_ROOT):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

from analysis.runners.make_prerun_plots import main as prerun_main  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-root", "--run", dest="run_root", required=True)
    parser.add_argument("--ptype", type=int, default=3)
    parser.add_argument("--max-frames", type=int, default=None)
    args = parser.parse_args()
    forwarded = ["--run-root", args.run_root, "--ptype", str(args.ptype)]
    if args.max_frames is not None:
        forwarded.extend(("--max-frames", str(args.max_frames)))
    sys.argv = [sys.argv[0], *forwarded]
    return prerun_main()


if __name__ == "__main__":
    raise SystemExit(main())