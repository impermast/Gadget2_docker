#!/usr/bin/env python3
"""make_prerun_plots.py — канонический CLI блока prerun (3 режима).

Режимы (математика гейтов дословно, рисования в гейтах нет):
  --ic/--snap            ранний гейт IC->snapshot (run_early_gate +
                         early_cusp_compare);
  --run-root             диагностика серии (metrics_series.csv +
                         series_metadata.json + summary + series_evolution +
                         contact_sheet faceon/edgeon);
  --group-root/--runs    сравнение shape-серий группы (shape_summary.csv/txt +
                         shape_panel ×5).

Выход ТОЛЬКО AnalysisPaths (prerun_dir/campaign_dir) — флага --outdir НЕТ.
"""
from __future__ import annotations

import argparse
import csv
import json
import shlex
import sys
import time
from pathlib import Path

import numpy as np

_HERE = Path(__file__).resolve().parent
for _p in (_HERE.parent.parent, _HERE.parent):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))
_CHECK_SCRIPTS = _HERE.parents[1] / "check_simulations"
if str(_CHECK_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_CHECK_SCRIPTS))

from analysis.loaders import (  # noqa: E402
    classify_series,
    build_series_metadata,
    discover_shape_runs,
    find_galic_dir,
    list_series_snapshots,
    prepare_early_figure_data,
    prepare_series_frames,
    prepare_shape_figure_data,
    read_snapshot_time,
    read_series_metric,
    run_early_gate,
    scan_sync_points,
    summarize_shape_run,
    write_metrics_csv,
    write_series_metadata,
    write_series_summary,
    write_shape_summary_csv,
    write_shape_text_report,
)
from analysis.paths import AnalysisPaths  # noqa: E402
from analysis.plotter import NbodyPlotter  # noqa: E402
from analysis.registry import by_block, find  # noqa: E402
from analysis.style import PlotSettings  # noqa: E402


def check(cond: bool, msg: str) -> None:
    if not cond:
        print(f"[FAIL] {msg}")
        raise SystemExit(1)
    print(f"[OK] {msg}")


def _wanted(args_plots):
    wanted = None
    if args_plots:
        wanted = set()
        for raw in args_plots.split(","):
            n = raw.strip()
            if n:
                wanted.add(find(n).name)
    names = [s.name for s in by_block("prerun")]
    if wanted is not None:
        unknown = sorted(wanted - set(names))
        if unknown:
            raise SystemExit(f"[FAIL] не prerun-plots для этого runner'а: {unknown}")
        names = [n for n in names if n in wanted]
    return names


def _plotter(outdir: Path) -> NbodyPlotter:
    plotter = NbodyPlotter(settings=PlotSettings(), renderer="matplotlib",
                           output_dir=outdir)
    plotter.register_defaults()
    return plotter


def _series_output_dir(run_root: Path, artifact_name: str | None = None) -> Path:
    """Resolve the canonical series artifact through ``AnalysisPaths``.

    The default remains ``run_root.name`` for compatibility.  A caller with
    duplicate basenames in different groups can provide a validated one-
    segment ``--artifact-name`` without introducing a free-form output path.
    """
    identity = artifact_name or Path(run_root).name
    return AnalysisPaths().prerun_dir(identity)


def _check_artifact_collision(outdir: Path, run_root: Path) -> None:
    """Reject an existing metadata identity belonging to another run."""
    metadata_path = outdir / "series_metadata.json"
    if not metadata_path.exists():
        return
    try:
        with metadata_path.open(encoding="utf-8") as fh:
            metadata = json.load(fh)
    except (OSError, ValueError) as exc:
        raise SystemExit(
            f"[FAIL] refusing to overwrite unreadable artifact metadata: "
            f"{metadata_path} ({exc})") from exc
    existing_root = metadata.get("run_root")
    if not existing_root or Path(existing_root).resolve() != Path(run_root).resolve():
        raise SystemExit(
            f"[FAIL] artifact collision: {outdir} belongs to "
            f"{existing_root!r}, requested {run_root}")


def _verify(outdir: Path, created: list, metadata_path: Path | None = None) -> None:
    check(len(created) > 0, f"files were created ({len(created)})")
    for p in sorted(set(created)):
        check(p.exists() and p.stat().st_size > 0,
              f"{p.name}: exists, size={p.stat().st_size:,} bytes")
        check(p.parent == outdir, f"{p.name}: located directly in {outdir}")
    if metadata_path is not None:
        check(metadata_path.exists() and metadata_path.stat().st_size > 0,
              f"{metadata_path.name}: metadata exists")
        try:
            with metadata_path.open(encoding="utf-8") as fh:
                metadata = json.load(fh)
        except (OSError, ValueError) as exc:
            raise SystemExit(f"[FAIL] invalid series metadata: {exc}") from exc
        check(metadata.get("schema") == "series-metadata-v1",
              "series metadata schema is supported")
        check(bool(metadata.get("analysis_schema_version")),
              "series metadata has analysis schema version")
        check(bool(metadata.get("run_id")),
              "series metadata has run identity")
        check(bool(metadata.get("artifact_identity")),
              "series metadata has artifact identity")
        # ``_verify`` is also used by callers validating an artifact copied
        # out of its canonical AnalysisPaths directory.  Identity collision
        # protection belongs to ``_check_artifact_collision`` (before writes);
        # requiring the directory basename here would reject such valid
        # relocated/copy-only validation while adding no safety.
        check(metadata_path.parent == outdir,
              f"{metadata_path.name}: located directly in {outdir}")

def do_gate(args, names: list) -> int:
    t0 = time.time()
    from analysis.loaders import read_state
    t_snap = float(read_state(args.snap)["header"].get("Time", float("nan")))
    run_name = Path(args.run_name).name if args.run_name \
        else Path(args.snap).parent.parent.name
    outdir = _series_output_dir(Path(args.snap).parent.parent,
                                args.artifact_name or run_name)
    print(f"[INFO] IC -> {args.snap} (t={t_snap:.4g}) -> {outdir}")
    galic_dir = args.galic_dir or find_galic_dir(args.ic)
    res = run_early_gate(args.ic, args.snap, galic_dir=galic_dir,
                         outdir=str(outdir), run_log=args.run_log,
                         nmin=args.nmin, rlo=args.rlo, rhi=args.rhi)
    print(f"[INFO] EARLY GATE: {'PASS' if res['gate_pass'] else 'FAIL'}")
    created = [outdir / "report.txt", outdir / "gate.json", outdir / "profiles.csv"]
    if "early_cusp_compare" in names:
        fig_data = prepare_early_figure_data(outdir / "profiles.csv")
        jobs = {"early_cusp_compare": {
            "data": fig_data,
            "config": {"gate_range": (args.rlo, args.rhi),
                       "time": t_snap,
                       "title": f"Early gate: IC vs snapshot (t={t_snap:.4g})"}}}
        for paths in _plotter(outdir).make_plots(jobs, output_dir=outdir).values():
            created.extend(paths)
    _verify(outdir, created)
    print(f"ALL CHECKS PASSED in {time.time() - t0:.1f}s -> {outdir}")
    return 0


def do_series(args, names: list) -> int:
    t0 = time.time()
    run_root = Path(args.run_root)
    outdir = _series_output_dir(run_root, args.artifact_name)
    _check_artifact_collision(outdir, run_root)
    print(f"[INFO] series {run_root} -> {outdir}")
    snaps = list_series_snapshots(run_root)
    # Read only Header/Time first.  This gives one target per snapshot for the
    # single bounded log scan; particle arrays are opened only afterwards.
    snapshot_times = [read_snapshot_time(snap) for snap in snaps]
    sync_scan = scan_sync_points(run_root / "run.log", snapshot_times)
    metrics = [
        read_series_metric(snap, args.ptype,
                           [nearest] if nearest is not None else [])
        for snap, nearest in zip(snaps, sync_scan.nearest_points)
    ]
    csv_path = outdir / "metrics_series.csv"
    write_metrics_csv(metrics, csv_path)
    metadata_path = outdir / "series_metadata.json"
    metadata = build_series_metadata(
        run_root=run_root,
        artifact_identity=outdir.name,
        ptype=args.ptype,
        snapshot_times=snapshot_times,
        scan=sync_scan,
        command=" ".join(shlex.quote(value)
                       for value in [sys.executable, *sys.argv]),
    )
    write_series_metadata(metadata, metadata_path)
    created: list = [csv_path, metadata_path]
    verdict, notes = classify_series(metrics)
    print(f"[INFO] verdict: {verdict}")
    for n in notes:
        print(f"  - {n}")
    if "series_evolution" in names:
        rows = list(csv.DictReader(csv_path.open()))
        evo = {k: np.asarray([float(r[k]) for r in rows])
               for k in ("time", "rho_core_r2", "ca_r5",
                         "z_rms_over_R_rms_r5", "mean_vphi_r5",
                         "ninteractions_total")}
        jobs = {"series_evolution": {
            "data": evo,
            "config": {"filename": "shape_evolution.png"}}}
        for paths in _plotter(outdir).make_plots(jobs, output_dir=outdir).values():
            created.extend(paths)
    if "contact_sheet" in names:
        frames = prepare_series_frames(run_root, args.ptype, args.max_frames)
        for plane, key in (("xy", "faceon"), ("xz", "edgeon")):
            jobs = {"contact_sheet": {
                "data": {"frames": frames, "plane": plane},
                "config": {"plane": plane, "title": f"Contact sheet {key}",
                           "filename": f"contact_{key}.png"}}}
            for paths in _plotter(outdir).make_plots(
                    jobs, output_dir=outdir).values():
                created.extend(paths)
    summary_path = outdir / "summary_partial_series.txt"
    write_series_summary(metrics, verdict, notes, summary_path,
                         created + [summary_path])
    created.append(summary_path)
    _verify(outdir, created, metadata_path=metadata_path)
    print(f"ALL CHECKS PASSED in {time.time() - t0:.1f}s -> {outdir}")
    return 0

def do_shape(args, names: list) -> int:
    t0 = time.time()
    group_root = Path(args.group_root)
    runs = discover_shape_runs(group_root, args.runs)
    if not runs:
        raise SystemExit(f"[FAIL] нет analyzed runs под {group_root}")
    outdir = AnalysisPaths().campaign_dir(args.campaign, args.member)
    print(f"[INFO] shape {[r.name for r in runs]} -> {outdir}")
    summaries = [summarize_shape_run(r, args.metrics_rel) for r in runs]
    summaries.sort(key=lambda s: (s.disk_score, s.ninteractions_final), reverse=True)
    csv_path = outdir / "shape_summary.csv"
    txt_path = outdir / "shape_summary.txt"
    write_shape_summary_csv(summaries, csv_path)
    print(write_shape_text_report(summaries, txt_path, group_root), end="")
    created: list = [csv_path, txt_path]
    if "shape_panel" in names:
        fig_data = prepare_shape_figure_data(runs, args.metrics_rel)
        jobs = {"shape_panel": {"data": fig_data}}
        for paths in _plotter(outdir).make_plots(jobs, output_dir=outdir).values():
            created.extend(paths)
    _verify(outdir, created)
    print(f"ALL CHECKS PASSED in {time.time() - t0:.1f}s -> {outdir}")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--ic", default=None)
    ap.add_argument("--snap", default=None)
    ap.add_argument("--run-log", default=None)
    ap.add_argument("--run-name", default=None)
    ap.add_argument("--galic-dir", default=None)
    ap.add_argument("--run-root", "--run", dest="run_root", default=None)
    ap.add_argument("--artifact-name", default=None,
                    help="unique one-segment AnalysisPaths artifact identity")
    ap.add_argument("--ptype", type=int, default=3)
    ap.add_argument("--max-frames", type=int, default=None)
    ap.add_argument("--group-root", "--group", dest="group_root", default=None)
    ap.add_argument("--runs", nargs="*", default=None)
    ap.add_argument("--metrics-rel", default="partial_analysis/metrics_series.csv")
    ap.add_argument("--campaign", default=None)
    ap.add_argument("--member", default="shape_compare")
    ap.add_argument("--nmin", type=int, default=200)
    ap.add_argument("--rlo", type=float, default=0.3)
    ap.add_argument("--rhi", type=float, default=3.0)
    ap.add_argument("--plots", default=None)
    ap.add_argument("--tg", action="store_true",
                    help="send the shape-series text report to Telegram")
    args = ap.parse_args()

    names = _wanted(args.plots)
    modes = [bool(args.ic and args.snap), bool(args.run_root), bool(args.group_root)]
    if sum(modes) != 1:
        raise SystemExit(
            "[FAIL] укажите ровно один режим: (--ic + --snap) | --run-root | --group-root")
    if modes[0]:
        return do_gate(args, names)
    if modes[1]:
        return do_series(args, names)
    if not args.campaign:
        raise SystemExit("[FAIL] режим группы требует --campaign")
    result = do_shape(args, names)
    if args.tg and result == 0:
        from formatting import send_tg
        report = AnalysisPaths().campaign_dir(args.campaign, args.member) / "shape_summary.txt"
        if report.is_file():
            send_tg(report.read_text())
    return result


if __name__ == "__main__":
    raise SystemExit(main())
