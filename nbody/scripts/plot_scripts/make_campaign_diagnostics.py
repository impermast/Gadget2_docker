#!/usr/bin/env python3
"""make_campaign_diagnostics.py — DIAG-графики для группы runs (презентация).

Тонкий integration-слой поверх registry plotting-архитектуры (как в
compare_visual_morphology.py). Данные готовятся через loaders.py, рендер —
через NbodyPlotter. Три новых графика:

- `diag_eloss_vs_f`         — заданная диссипация f (DM_DissipationFactor) vs
                              измеренная относительная потеря кинетической
                              энергии рассеявшихся частиц dE/E;
- `criteria_time_panel`     — c/a(t), z_rms/R_rms(t), |Vrot|/sigma(t) с порогами
                              для выбранных кандидатов (metrics_series.csv);
- `runaway_timestep_panel`  — N_interactions(t) vs min dt(t) для патологического
                              run (metrics_series.csv).

Пример:
    docker exec gadget-gizmo python3 \\
        /nbody/scripts/plot_scripts/make_campaign_diagnostics.py \\
        --group-root /nbody/runs/dsidm_spin_k08_transition \\
        --eloss-runs dsidm_s2p5_D0p10_N1e5_T2 dsidm_s2p5_D0p25_N1e5_T2 \\
            dsidm_s2p5_D0p50_N1e5_T2 \\
        --eloss-baseline sidm_s2p5_N1e5_T2 \\
        --criteria-runs dsidm_s2p5_D0p10_N1e5_T2 dsidm_s2p5_D0p25_N1e5_T2 \\
            dsidm_s2p5_D0p50_N1e5_T2 \\
        --runaway-runs dsidm_s2p5_D0p75_N1e5_T2 \\
        --metrics-rel partial_analysis/metrics_series.csv
"""
from __future__ import annotations

import argparse
import math
import re
import sys
import time
from pathlib import Path
from typing import Dict, List, Optional

import numpy as np

_HERE = Path(__file__).resolve().parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

from loaders import (  # noqa: E402
    interacted_kinetic_energy,
    load_metrics_series,
    prepare_visual_snapshot,
)
from plotter import create_plotter  # noqa: E402
from settings import PlotSettings, RunPaths  # noqa: E402



def _dissipation_factor(run: Path) -> Optional[float]:
    """Прочитать DM_DissipationFactor из .gizmo_run.param / configs param."""
    candidates = [run / ".gizmo_run.param", run / ".gizmo_run.param-usedvalues"]
    for path in candidates:
        if not path.exists():
            continue
        text = path.read_text(errors="replace")
        m = re.search(r"^DM_DissipationFactor\s+([\d.eE+-]+)", text, re.M)
        if m:
            return float(m.group(1))
    return None


def _kinetic_loss(run: Path, baseline_k: Optional[float], ptype: int) -> Optional[tuple]:
    """k (kinetic energy interacted subset), потеря vs baseline (0..1)."""
    try:
        rp = RunPaths(run)
        snap = rp.latest_snapshot()
    except Exception:
        return None
    try:
        visual = prepare_visual_snapshot(snap, ptype=ptype)
    except Exception:
        return None
    k = interacted_kinetic_energy(visual)
    if not math.isfinite(k):
        return None
    if baseline_k is None or baseline_k <= 0:
        loss = 0.0
    else:
        loss = min(1.0, (baseline_k - k) / baseline_k)
    return (k, loss)


def _find_metrics(run: Path, metrics_rel: str) -> Optional[Dict[str, np.ndarray]]:
    path = run / metrics_rel
    if not path.exists():
        return None
    try:
        data = load_metrics_series(path)
    except Exception:
        return None
    if not data or "time" not in data or len(data["time"]) == 0:
        return None
    return data


def _pick_metric_key(data: Dict[str, np.ndarray], names: List[str]) -> Optional[str]:
    for n in names:
        if n in data:
            return n
    return None



def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--group-root", required=True)
    ap.add_argument("--outdir", default=None,
                    help="default: <group-root>/diagnostics")
    ap.add_argument("--ptype", type=int, default=3)
    ap.add_argument("--eloss-runs", nargs="*", default=[])
    ap.add_argument("--eloss-baseline", default=None,
                    help="run с elastic SIDM (D=0) той же sigma — baseline кинетики")
    ap.add_argument("--criteria-runs", nargs="*", default=[])
    ap.add_argument("--runaway-runs", nargs="*", default=[])
    ap.add_argument("--metrics-rel", default="partial_analysis/metrics_series.csv")
    args = ap.parse_args()

    t0 = time.time()
    group = Path(args.group_root)
    outdir = Path(args.outdir) if args.outdir else group / "diagnostics"
    outdir.mkdir(parents=True, exist_ok=True)

    def resolve(name_or_path: str) -> Path:
        p = Path(name_or_path)
        return p if p.is_absolute() else group / p

    plotter = create_plotter(PlotSettings(), output_dir=outdir)
    jobs = {}

    # ---- 1) diag_eloss_vs_f ----
    if args.eloss_runs:
        eloss_runs = [resolve(r) for r in args.eloss_runs]
        baseline_k = None
        if args.eloss_baseline:
            bl = resolve(args.eloss_baseline)
            mv = _kinetic_loss(bl, None, args.ptype)
            if mv is not None:
                baseline_k = mv[0]
                print(f"[INFO] eloss baseline {bl.name}: K_interacted={baseline_k:.6e}")
            else:
                print(f"[WARN] baseline {bl.name} не подготовлен; потеря vs 0")
        f_set, measured, labels = [], [], []
        for run in eloss_runs:
            if not run.is_dir():
                print(f"[WARN] no run dir: {run.name}")
                continue
            d = _dissipation_factor(run)
            if d is None:
                print(f"[WARN] {run.name}: нет DM_DissipationFactor -> skip")
                continue
            mv = _kinetic_loss(run, baseline_k, args.ptype)
            if mv is None:
                print(f"[WARN] {run.name}: без снапшота -> skip")
                continue
            f_set.append(d)
            measured.append(mv[1])
            labels.append(run.name.replace("_N1e5_T2", ""))
            print(f"[INFO] eloss {run.name}: D={d:.3f} dE/E={mv[1]:.4f}")
        if f_set:
            jobs["diag_eloss_vs_f"] = {
                "data": {"f_set": np.asarray(f_set),
                         "measured": np.asarray(measured),
                         "labels": np.asarray(labels, dtype=object)},
            }

    # ---- 2) criteria_time_panel ----
    if args.criteria_runs:
        times, ca, thick, vrot = None, None, None, None
        label_texts = []
        for name in args.criteria_runs:
            run = resolve(name)
            mdata = _find_metrics(run, args.metrics_rel)
            if mdata is None:
                print(f"[WARN] criteria {name}: нет metrics series -> skip")
                continue
            t = mdata["time"]
            ca_k = _pick_metric_key(mdata, ["ca_r5", "ca"])
            th_k = _pick_metric_key(mdata, ["z_rms_over_R_rms_r5", "thickness"])
            vr_k = _pick_metric_key(mdata, ["vrot_over_sigma_r5", "vrot_over_sigma"])
            if not (ca_k and th_k and vr_k):
                print(f"[WARN] criteria {name}: неполные metrics -> skip")
                continue
            times = t if times is None else times
            if len(t) != len(times):
                print(f"[WARN] criteria {name}: длина серии != первая -> skip")
                continue
            ca = mdata[ca_k] if ca is None else ca
            thick = mdata[th_k] if thick is None else thick
            vrot = mdata[vr_k] if vrot is None else vrot
            label_texts.append(name.replace("_N1e5_T2", ""))
        if times is not None and len(times) > 1:
            jobs["criteria_time_panel"] = {
                "data": {"times": times, "ca": ca, "thickness": thick,
                         "vrot_over_sigma": vrot,
                         "labels": np.asarray(label_texts, dtype=object)},
            }

    # ---- 3) runaway_timestep_panel ----
    if args.runaway_runs:
        for name in args.runaway_runs:
            run = resolve(name)
            mdata = _find_metrics(run, args.metrics_rel)
            if mdata is None:
                print(f"[WARN] runaway {name}: нет metrics series -> skip")
                continue
            ni_k = _pick_metric_key(mdata, ["ninteractions_total", "ninteractions"])
            dt_k = _pick_metric_key(mdata, ["nearest_systemstep", "systemstep", "dt_min"])
            if not (ni_k and dt_k):
                print(f"[WARN] runaway {name}: неполные metrics -> skip")
                continue
            jobs["runaway_timestep_panel"] = {
                "data": {"times": mdata["time"], "ninteractions": mdata[ni_k],
                         "dt_min": mdata[dt_k],
                         "labels": np.asarray([name.replace("_N1e5_T2", "")],
                                              dtype=object)},
            }

    if not jobs:
        print("[ERROR] нет данных для построения DIAG-графиков")
        print("Проверьте --eloss-runs/--criteria-runs/--runaway-runs и metrics.")
        return 2

    results = plotter.make_plots(jobs, output_dir=outdir)
    made = sorted({p for paths in results.values() for p in paths})
    print("=" * 72)
    print(f"CAMPAIGN DIAGNOSTICS DONE in {time.time() - t0:.1f}s -> {outdir}")
    for p in made:
        print(f"  - {p.name} ({p.stat().st_size:,} bytes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
