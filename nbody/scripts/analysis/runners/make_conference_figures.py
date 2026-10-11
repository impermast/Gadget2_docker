#!/usr/bin/env python3
"""Build the bounded conference-2026 evidence figures from committed CSVs."""
from __future__ import annotations
import argparse, csv, sys
from pathlib import Path
import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent.parent))
from analysis.plotter import NbodyPlotter
from analysis.style import PlotSettings

REQUIRED_CAMPAIGN = {"run_id", "series_metrics_csv", "series_mapping_status", "campaign_interpretation",
                     "ca_r5_final", "z_rms_over_R_rms_r5_final", "vrot_over_sigma_r5_final",
                     "ninteractions_total_final", "nearest_systemstep_final", "screening_candidate"}
REQUIRED_INDEX = {"group", "run_id", "metrics_csv", "status", "window_label", "window_start", "window_end"}

def rows(path):
    with path.open(newline="") as f:
        r = csv.DictReader(f); data = list(r)
    if not r.fieldnames: raise ValueError(f"empty CSV: {path}")
    return r.fieldnames, data

def num(v, name):
    try: return float(v)
    except Exception as e: raise ValueError(f"non-numeric {name}: {v!r}") from e

def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--package-root", default="nbody/analysis/presentations/conference_2026")
    a = ap.parse_args(argv); root = Path(a.package_root).resolve(); out = root / "figs"; out.mkdir(exist_ok=True)
    cf, campaign = rows(root / "campaign_metrics.csv"); ix, index = rows(root / "m4_series/series_index.csv")
    if not REQUIRED_CAMPAIGN <= set(cf): raise ValueError("campaign_metrics schema mismatch")
    if not REQUIRED_INDEX <= set(ix): raise ValueError("series_index schema mismatch")
    if len(index) != 9: raise ValueError(f"expected 9 mapped series, got {len(index)}")
    if len({r["run_id"] for r in index}) != len(index): raise ValueError("duplicate series identity")
    byid = {r["run_id"]: r for r in campaign}
    if not {r["run_id"] for r in index} <= set(byid): raise ValueError("campaign/index identity mismatch")
    series=[]; summary=[]
    for i, ir in enumerate(index):
        if ir["run_id"] not in byid: raise ValueError("missing campaign row")
        mp = (root / "m4_series" / ir["metrics_csv"]).resolve()
        if not mp.exists(): raise ValueError(f"missing explicit metrics path: {mp}")
        mf, mr = rows(mp)
        needed={"time","ca_r5","z_rms_over_R_rms_r5","vrot_over_sigma_r5","ninteractions_total","nearest_systemstep"}
        if not needed <= set(mf): raise ValueError(f"series schema mismatch: {mp}")
        if not mr: raise ValueError(f"empty series: {mp}")
        t=[num(x["time"],"time") for x in mr]
        s={k:[num(x[k],k) for x in mr] for k in needed-{"time"}}
        label=ir["run_id"].replace("_N1e5","")
        series.append({"times":t,"ca":s["ca_r5"],"thickness":s["z_rms_over_R_rms_r5"],"vrot_over_sigma":s["vrot_over_sigma_r5"],"ninteractions":s["ninteractions_total"],"dt_min":s["nearest_systemstep"],"label":label})
        cr=byid[ir["run_id"]]; summary.append({"summary_labels":label,"ca_final":num(cr["ca_r5_final"],"ca"),"thickness_final":num(cr["z_rms_over_R_rms_r5_final"],"thick"),"vrot_final":num(cr["vrot_over_sigma_r5_final"],"vrot"),"ninteractions_final":num(cr["ninteractions_total_final"],"ni"),"disk_score":0.0})
    for x in summary: x["disk_score"] = max(0,.75-x["ca_final"])+max(0,.55-x["thickness_final"])+.5*max(0,x["vrot_final"]-.15)
    p=NbodyPlotter(settings=PlotSettings(), output_dir=out).register_defaults()
    made=[]
    for name,data,fn in [("criteria_time_panel",{"series":series},"criteria_time_panel.png"),("runaway_timestep_panel",{"series":series},"runaway_timestep_panel.png"),("disk_dashboard",{k:[x[k] for x in summary] for k in summary[0]},"disk_dashboard.png")]:
        made += p.make_plot(name,data,{"filename":fn},output_dir=out)
    # Validation contract is explicit and independent of the series figures.
    vf, vr=rows(root/"validation/dissipation_check.csv"); need={"dissipation_factor","loss_fraction_measured"}
    if not need <= set(vf): raise ValueError("validation schema mismatch")
    valid=[x for x in vr if x.get("validation_level")=="analytic" and x.get("verdict")=="pass_with_limitations"]
    if valid: made += p.make_plot("diag_eloss_vs_f", {"f_set":[num(x["dissipation_factor"],"D") for x in valid],"measured":[num(x["loss_fraction_measured"],"loss") for x in valid],"labels":[x["case_id"] for x in valid]}, {"filename":"diag_eloss_vs_f.png"},output_dir=out)
    manifest=out/"figure_manifest.csv"
    with manifest.open("w",newline="") as f:
        w=csv.DictWriter(f,fieldnames=["figure_id","filename","source_locators","exact_command","claim_ids","units","visual_review_pending"]); w.writeheader()
        cmd="python3 nbody/scripts/analysis/runners/make_conference_figures.py --package-root nbody/analysis/presentations/conference_2026"
        for name,path in zip(["criteria_time_panel","runaway_timestep_panel","disk_dashboard","diag_eloss_vs_f"],made): w.writerow({"figure_id":name,"filename":path.name,"source_locators":"campaign_metrics.csv; m4_series/series_index.csv" if name!="diag_eloss_vs_f" else "validation/dissipation_check.csv","exact_command":cmd,"claim_ids":"C4" if name=="diag_eloss_vs_f" else "C1;C2;C3","units":"code time; dimensionless; interactions; code timestep","visual_review_pending":"true"})
    return made

if __name__ == "__main__":
    main()
