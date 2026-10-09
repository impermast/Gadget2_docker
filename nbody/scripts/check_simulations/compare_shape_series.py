#!/usr/bin/env python3
"""Compatibility CLI for grouped shape-series diagnostics.

The analysis loaders and registry-based renderer are implemented in the
``analysis`` package; this wrapper preserves the historical command shape.
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
    parser.add_argument("--group-root", "--group", dest="group_root", required=True)
    parser.add_argument("--runs", nargs="*", default=None)
    parser.add_argument("--metrics-rel", default="partial_analysis/metrics_series.csv")
    parser.add_argument("--tg", action="store_true")
    args = parser.parse_args()
    forwarded = ["--group-root", args.group_root,
                 "--campaign", Path(args.group_root).name,
                 "--member", "shape_compare",
                 "--metrics-rel", args.metrics_rel]
    if args.runs:
        forwarded.extend(("--runs", *args.runs))
    if args.tg:
        forwarded.append("--tg")
    sys.argv = [sys.argv[0], *forwarded]
    return prerun_main()


if __name__ == "__main__":
    raise SystemExit(main())