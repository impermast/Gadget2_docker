#!/usr/bin/env python3
"""make_campaign_plots.py — runner блока campaigns: profile-compare группа.

Перенос plot_scripts/compare_runs.py (логика дословно): сравнение нескольких
прогонов на финальных snapshot'ах — density_compare, log_slope_compare,
sigma_v_compare, log_rho_compare, rot_curve_compare, core_density_vs_sigma
(последний — только при >=2 SIDM-прогонах с sigma>0).

Морфологические plots блока (visual_morphology_montage, surface_density_
residuals, morphology_profiles_compare, phase_space_compare, disk_dashboard)
строит make_campaign_morphology_plots.py, DIAG-панели (diag_eloss_vs_f,
criteria_time_panel, runaway_timestep_panel) — make_campaign_diag_plots.py.

Отличия от предка:
  --campaign      ОБЯЗАТЕЛЬНО: имя кампании (валидированный сегмент пути);
  --member        подкаталог внутри кампании (дефолт compare_<N>runs);
  --plots         подмножество имён реестра ИЗ ЭТОЙ группы;
  выход           ТОЛЬКО AnalysisPaths.campaign_dir(campaign, member) —
                  флага --outdir НЕТ (guard-тест test_runners_have_no_outdir_flags).

Пример:
    docker exec gadget-gizmo python3 /nbody/scripts/analysis/runners/make_campaign_plots.py \\
        /nbody/runs/corecusp_cdm_N1e7_T5 /nbody/runs/corecusp_sidm2_N1e7_T5 \\
        --labels CDM SIDM_sigma2 --campaign corecusp --rcore 1.0
ВНИМАНИЕ: позиционные run-каталоги указывать ДО --labels (nargs='*' у
--labels жадно поглощает всё, что стоит после него). Подписи серий берутся из
--labels (по порядку) или из имени каталога. core_density_vs_sigma строится,
если среди прогонов есть >=2 SIDM (sigma>0).
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

from analysis.loaders import prepare_profile_data  # noqa: E402
from analysis.paths import AnalysisPaths  # noqa: E402
from analysis.plotter import NbodyPlotter  # noqa: E402
from analysis.registry import find  # noqa: E402
from analysis.style import PlotSettings, RunPaths, SimulationInfo  # noqa: E402

# Plots, которые строит именно этот runner (profile-compare группа).
# Остальные plots блока campaigns имеют собственные runner'ы
# (реестр: spec.runner) — см. registry.BLOCK_RUNNERS и runner-атрибуты классов.
PROFILE_PLOTS = (
    "density_compare",
    "log_slope_compare",
    "sigma_v_compare",
    "log_rho_compare",
    "rot_curve_compare",
    "core_density_vs_sigma",
)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("runs", nargs="+", help="run root directories")
    ap.add_argument("--labels", nargs="*", default=None,
                    help="подписи серий (по порядку; default: имя каталога)")
    ap.add_argument("--campaign", required=True,
                    help="имя кампании (один сегмент пути)")
    ap.add_argument("--member", default=None,
                    help="подкаталог внутри кампании (default: compare_<N>runs)")
    ap.add_argument("--plots", default=None,
                    help="подмножество имён реестра (дефолт: все campaigns-plots)")
    ap.add_argument("--rcore", type=float, default=50.0)
    ap.add_argument("--ptype", type=int, default=3)
    args = ap.parse_args()

    t0 = time.time()
    member = args.member or f"compare_{len(args.runs)}runs"
    outdir = AnalysisPaths().campaign_dir(args.campaign, member)
    print(f"[INFO] campaign={args.campaign}/{member} -> {outdir}")

    labels = args.labels or []
    if len(labels) < len(args.runs):
        labels += [Path(r).resolve().name for r in args.runs[len(labels):]]

    campaign_names = list(PROFILE_PLOTS)
    if args.plots:
        wanted = set()
        for raw in args.plots.split(","):
            name = raw.strip()
            if not name:
                continue
            spec = find(name)  # валидация имени + подсказка при опечатке
            if name not in PROFILE_PLOTS:
                raise SystemExit(
                    f"[FAIL] '{name}' строится не этим runner'ом, а {spec.runner}")
            wanted.add(name)
        campaign_names = [n for n in PROFILE_PLOTS if n in wanted]

    plotter = NbodyPlotter(PlotSettings(), renderer="matplotlib",
                           output_dir=outdir)
    plotter.register_defaults()

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

    # Все compare-plots из реестра: profile compare (3) + delta-графики
    # (log_rho_compare, rot_curve_compare); core_density_vs_sigma — отдельно.
    profile_plot_names = [n for n in campaign_names
                          if n != "core_density_vs_sigma"]
    jobs = {name: {"data": {"series": series}} for name in profile_plot_names}
    results = plotter.make_plots(jobs, output_dir=outdir)

    if "core_density_vs_sigma" in campaign_names:
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
