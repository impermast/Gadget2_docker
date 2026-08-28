#!/usr/bin/env python3
"""Partial-series diagnostics for stopped/pathological GIZMO runs.

This is a reusable check-run tool. It analyzes a snapshot sequence, not just the
latest snapshot, and writes quantitative CSV/TXT plus static PNG diagnostics.
GIFs are intentionally not required for agent verdicts.
"""
from __future__ import annotations

import argparse
import csv
import math
import re
import sys
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple

import h5py
import numpy as np

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.colors import LogNorm

SCRIPT_DIR = Path(__file__).resolve().parent
PLOT_DIR = SCRIPT_DIR.parent / "plot_scripts"
for p in [SCRIPT_DIR, PLOT_DIR]:
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

from gizmo_log import SYNC_RE, SyncPoint  # noqa: E402
try:
    from loaders import shrink_center, _snapshot_number  # noqa: E402
except Exception:  # pragma: no cover
    shrink_center = None
    def _snapshot_number(path: str) -> int:
        m = re.search(r"snapshot_?(\d+)\.hdf5$", Path(path).name)
        return int(m.group(1)) if m else -1


GYR_PER_CODE = 0.9777923542981722


@dataclass
class SeriesMetric:
    snapshot: int
    file: str
    time: float
    particles: int
    rho_core_r1: float
    rho_core_r2: float
    rho_core_r5: float
    ba_r2: float
    ca_r2: float
    ba_r5: float
    ca_r5: float
    ba_r10: float
    ca_r10: float
    z_rms_over_R_rms_r5: float
    z_p68_over_R_p68_r5: float
    mean_vphi_r5: float
    median_vphi_r5: float
    sigma_vphi_r5: float
    vrot_over_sigma_r5: float
    ninteractions_total: int
    interacted_fraction: float
    ninteractions_mean_nonzero: float
    ninteractions_p90_nonzero: float
    ninteractions_max: int
    nearest_sync_point: int
    nearest_systemstep: float


def list_snapshots(run_root: Path) -> List[Path]:
    files = sorted((run_root / "output").glob("snapshot_*.hdf5"), key=lambda p: _snapshot_number(str(p)))
    if not files:
        raise FileNotFoundError(f"No snapshots in {run_root / 'output'}")
    return files


def read_all_sync_points(log_path: Path) -> List[SyncPoint]:
    """Read all Sync-Point entries without loading the whole log into memory."""
    points: List[SyncPoint] = []
    if not log_path.exists():
        return points
    with log_path.open("r", errors="replace") as f:
        for line in f:
            m = SYNC_RE.search(line)
            if not m:
                continue
            points.append(SyncPoint(
                int(m.group("sync")),
                float(m.group("time")),
                float(m.group("step")),
            ))
    return points


def weighted_center(pos: np.ndarray, mass: np.ndarray) -> np.ndarray:
    if shrink_center is not None:
        return shrink_center(pos, mass, niter=6)
    return np.average(pos, axis=0, weights=mass)


def shape_ratios(pos: np.ndarray, mass: np.ndarray, radius: float) -> Tuple[float, float]:
    r = np.linalg.norm(pos, axis=1)
    m = r < radius
    if int(m.sum()) < 20:
        return math.nan, math.nan
    x = pos[m]
    w = mass[m]
    cov = (x * w[:, None]).T @ x / np.sum(w)
    vals = np.linalg.eigvalsh(cov)
    vals = np.sort(np.clip(vals, 0.0, None))[::-1]
    if vals[0] <= 0:
        return math.nan, math.nan
    axes = np.sqrt(vals)
    return float(axes[1] / axes[0]), float(axes[2] / axes[0])


def core_density(r: np.ndarray, mass: np.ndarray, radius: float) -> float:
    return float(mass[r < radius].sum() / (4.0 / 3.0 * np.pi * radius ** 3))


def thickness(pos: np.ndarray, mass: np.ndarray, radius: float = 5.0) -> Tuple[float, float]:
    R = np.linalg.norm(pos[:, :2], axis=1)
    r = np.linalg.norm(pos, axis=1)
    m = r < radius
    if int(m.sum()) < 20:
        return math.nan, math.nan
    z = pos[m, 2]
    Rm = R[m]
    z_rms = math.sqrt(float(np.average(z * z, weights=mass[m])))
    R_rms = math.sqrt(float(np.average(Rm * Rm, weights=mass[m])))
    pz = float(np.percentile(np.abs(z), 68))
    pR = float(np.percentile(Rm, 68))
    return (z_rms / R_rms if R_rms > 0 else math.nan,
            pz / pR if pR > 0 else math.nan)


def rotation_metrics(pos: np.ndarray, vel: np.ndarray, radius: float = 5.0) -> Tuple[float, float, float, float]:
    r = np.linalg.norm(pos, axis=1)
    R = np.linalg.norm(pos[:, :2], axis=1)
    m = (r < radius) & (R > 1e-8)
    if int(m.sum()) < 20:
        return math.nan, math.nan, math.nan, math.nan
    x, y = pos[m, 0], pos[m, 1]
    vx, vy, vz = vel[m, 0], vel[m, 1], vel[m, 2]
    Rm = R[m]
    vphi = (-y * vx + x * vy) / Rm
    vR = (x * vx + y * vy) / Rm
    mean_vphi = float(np.mean(vphi))
    med_vphi = float(np.median(vphi))
    sig_vphi = float(np.std(vphi))
    sigma_3d = math.sqrt(float(np.var(vR) + np.var(vphi) + np.var(vz)))
    support = abs(mean_vphi) / sigma_3d if sigma_3d > 0 else math.nan
    return mean_vphi, med_vphi, sig_vphi, support


def ni_metrics(ni: Optional[np.ndarray]) -> Tuple[int, float, float, float, int]:
    if ni is None or len(ni) == 0:
        return 0, 0.0, math.nan, math.nan, 0
    total = int(np.sum(ni))
    nz_mask = ni > 0
    nz = int(np.count_nonzero(nz_mask))
    frac = float(nz / len(ni))
    if nz == 0:
        return total, frac, math.nan, math.nan, 0
    vals = ni[nz_mask].astype(float)
    return total, frac, float(np.mean(vals)), float(np.percentile(vals, 90)), int(np.max(vals))


def nearest_log_health(points, time: float) -> Tuple[int, float]:
    if not points:
        return -1, math.nan
    p = min(points, key=lambda q: abs(q.time - time))
    return int(p.sync_point), float(p.systemstep)


def read_metric(snapshot: Path, ptype: int, log_points) -> Tuple[SeriesMetric, Dict[str, np.ndarray]]:
    with h5py.File(snapshot, "r") as f:
        h = f["Header"].attrs
        time = float(h.get("Time", 0.0))
        gname = f"PartType{ptype}"
        if gname not in f:
            groups = sorted(k for k in f.keys() if k.startswith("PartType"))
            if not groups:
                raise ValueError(f"No PartType groups in {snapshot}")
            gname = groups[-1]
        g = f[gname]
        pos0 = g["Coordinates"][:].astype(np.float64)
        vel0 = g["Velocities"][:].astype(np.float64)
        mass = (g["Masses"][:].astype(np.float64) if "Masses" in g else np.ones(len(pos0)))
        ni = (g["NInteractions"][:] if "NInteractions" in g else None)
    center = weighted_center(pos0, mass)
    pos = pos0 - center
    vel = vel0 - np.mean(vel0, axis=0)
    r = np.linalg.norm(pos, axis=1)
    ba2, ca2 = shape_ratios(pos, mass, 2.0)
    ba5, ca5 = shape_ratios(pos, mass, 5.0)
    ba10, ca10 = shape_ratios(pos, mass, 10.0)
    thick_rms, thick_p68 = thickness(pos, mass, 5.0)
    mv, medv, sv, supp = rotation_metrics(pos, vel, 5.0)
    nit, nifrac, nimean, nip90, nimax = ni_metrics(ni)
    sync, step = nearest_log_health(log_points, time)
    metric = SeriesMetric(
        snapshot=_snapshot_number(str(snapshot)), file=snapshot.name, time=time,
        particles=int(len(pos)),
        rho_core_r1=core_density(r, mass, 1.0),
        rho_core_r2=core_density(r, mass, 2.0),
        rho_core_r5=core_density(r, mass, 5.0),
        ba_r2=ba2, ca_r2=ca2, ba_r5=ba5, ca_r5=ca5, ba_r10=ba10, ca_r10=ca10,
        z_rms_over_R_rms_r5=thick_rms,
        z_p68_over_R_p68_r5=thick_p68,
        mean_vphi_r5=mv, median_vphi_r5=medv, sigma_vphi_r5=sv, vrot_over_sigma_r5=supp,
        ninteractions_total=nit, interacted_fraction=nifrac,
        ninteractions_mean_nonzero=nimean, ninteractions_p90_nonzero=nip90,
        ninteractions_max=nimax,
        nearest_sync_point=sync, nearest_systemstep=step,
    )
    return metric, {"pos": pos, "mass": mass, "time": np.asarray(time)}


def write_csv(metrics: List[SeriesMetric], out: Path) -> None:
    with out.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(asdict(metrics[0]).keys()))
        w.writeheader()
        for m in metrics:
            w.writerow(asdict(m))


def arr(metrics: List[SeriesMetric], name: str) -> np.ndarray:
    return np.asarray([getattr(m, name) for m in metrics], dtype=float)


def plot_lines(metrics: List[SeriesMetric], outdir: Path) -> List[Path]:
    t = arr(metrics, "time")
    made: List[Path] = []
    specs = [
        ("shape_evolution.png", "Shape evolution", [("c/a r<2", arr(metrics, "ca_r2")), ("c/a r<5", arr(metrics, "ca_r5")), ("c/a r<10", arr(metrics, "ca_r10")), ("b/a r<5", arr(metrics, "ba_r5"))], "axis ratio"),
        ("thickness_evolution.png", "Thickness evolution (r<5)", [("z_rms/R_rms", arr(metrics, "z_rms_over_R_rms_r5")), ("p68(|z|)/p68(R)", arr(metrics, "z_p68_over_R_p68_r5"))], "thickness ratio"),
        ("core_density_evolution.png", "Core density evolution", [("r<1", arr(metrics, "rho_core_r1")), ("r<2", arr(metrics, "rho_core_r2")), ("r<5", arr(metrics, "rho_core_r5"))], "rho_core"),
        ("ninteractions_evolution.png", "NInteractions evolution", [("total", arr(metrics, "ninteractions_total")), ("p90 nonzero", arr(metrics, "ninteractions_p90_nonzero"))], "NInteractions"),
        ("rotation_support_evolution.png", "Rotation support (r<5)", [("mean vphi", arr(metrics, "mean_vphi_r5")), ("median vphi", arr(metrics, "median_vphi_r5")), ("|vrot|/sigma", arr(metrics, "vrot_over_sigma_r5"))], "value"),
        ("timestep_health.png", "Nearest log health", [("Systemstep", arr(metrics, "nearest_systemstep")), ("SyncPoint/1e6", arr(metrics, "nearest_sync_point") / 1e6)], "log health"),
    ]
    for fname, title, series, ylabel in specs:
        fig, ax = plt.subplots(figsize=(8.0, 4.8))
        for label, y in series:
            ax.plot(t, y, marker="o", lw=1.8, label=label)
        ax.set_title(title)
        ax.set_xlabel("Time [code units]")
        ax.set_ylabel(ylabel)
        if "density" in fname or "ninteractions" in fname or "timestep" in fname:
            ax.set_yscale("log")
        ax.grid(True, alpha=0.3)
        ax.legend(frameon=False)
        fig.tight_layout()
        path = outdir / fname
        fig.savefig(path, dpi=180)
        plt.close(fig)
        made.append(path)
    return made


def contact_sheet(frames: List[Dict[str, np.ndarray]], out: Path, projection: str, bins: int = 180) -> Path:
    n = len(frames)
    cols = min(5, n)
    rows = int(math.ceil(n / cols))
    fig, axs = plt.subplots(rows, cols, figsize=(3.0 * cols, 3.0 * rows), squeeze=False)
    all_pos = np.concatenate([f["pos"] for f in frames], axis=0)
    lim = max(float(np.percentile(np.abs(all_pos), 98)), 2.0)
    axes = (0, 1) if projection == "xy" else (0, 2)
    for i, fr in enumerate(frames):
        ax = axs[i // cols][i % cols]
        pos = fr["pos"]
        mass = fr["mass"]
        H, xe, ye = np.histogram2d(pos[:, axes[0]], pos[:, axes[1]], bins=bins,
                                   range=[[-lim, lim], [-lim, lim]], weights=mass)
        positive = H[H > 0]
        norm = LogNorm(vmin=max(float(positive.min()), 1e-12), vmax=float(positive.max())) if positive.size else None
        ax.imshow(H.T, origin="lower", extent=[-lim, lim, -lim, lim], cmap="inferno", norm=norm, aspect="equal")
        ax.set_title(f"snap {int(fr['snapshot'])}  t={float(fr['time']):.2f}", fontsize=9)
        ax.set_xlabel("x [kpc]")
        ax.set_ylabel(("y" if projection == "xy" else "z") + " [kpc]")
    for j in range(n, rows * cols):
        axs[j // cols][j % cols].axis("off")
    fig.tight_layout()
    fig.savefig(out, dpi=160)
    plt.close(fig)
    return out


def classify_series(metrics: List[SeriesMetric]) -> Tuple[str, List[str]]:
    notes: List[str] = []
    ca5 = arr(metrics, "ca_r5")
    rho2 = arr(metrics, "rho_core_r2")
    ni = arr(metrics, "ninteractions_total")
    step = arr(metrics, "nearest_systemstep")
    support = arr(metrics, "vrot_over_sigma_r5")
    finite_ca = ca5[np.isfinite(ca5)]
    min_ca = float(np.min(finite_ca)) if finite_ca.size else math.nan
    rho_growth = float(rho2[-1] / rho2[0]) if rho2[0] > 0 else math.nan
    ni_growth = int(ni[-1] - ni[0]) if len(ni) else 0
    step_pos = step[np.isfinite(step) & (step > 0)]
    min_step = float(np.min(step_pos)) if step_pos.size else math.nan
    max_support = float(np.nanmax(support)) if np.isfinite(support).any() else math.nan

    notes.append(f"snapshots={len(metrics)}, time={metrics[0].time:.3f}..{metrics[-1].time:.3f}")
    notes.append(f"min c/a(r<5)={min_ca:.3g}; rho_core(r<2) growth={rho_growth:.3g}; ΔNI={ni_growth}")
    notes.append(f"min Systemstep={min_step:.3g}; max |vrot|/sigma(r<5)={max_support:.3g}")

    if np.isfinite(min_step) and min_step < 1e-6 and np.isfinite(rho_growth) and rho_growth > 5:
        verdict = "catastrophic-collapse"
        notes.append("Interpretation: density growth and timestep collapse indicate catastrophic dissipative collapse rather than a stable disk.")
    elif np.isfinite(min_ca) and min_ca < 0.45 and np.isfinite(max_support) and max_support > 0.4 and (not np.isfinite(min_step) or min_step >= 1e-6):
        verdict = "promising-disk-like"
        notes.append("Interpretation: flattening with rotation support and no severe timestep collapse looks promising.")
    elif np.isfinite(min_step) and min_step < 1e-6 and (not np.isfinite(min_ca) or min_ca > 0.55):
        verdict = "no-disk-before-pathology"
        notes.append("Interpretation: numerical pathology appears before clear disk-like flattening.")
    else:
        verdict = "ambiguous-partial-series"
        notes.append("Interpretation: partial data are ambiguous; inspect static contact sheets and metrics before choosing next parameters.")
    return verdict, notes


def write_summary(metrics: List[SeriesMetric], verdict: str, notes: List[str], out: Path, made: Iterable[Path]) -> None:
    lines = [
        "PARTIAL SERIES DIAGNOSTIC SUMMARY",
        f"Verdict: {verdict}",
        "",
        "Key notes:",
    ]
    lines += [f"- {n}" for n in notes]
    lines += [
        "",
        "Generated files:",
    ]
    lines += [f"- {p.name} ({p.stat().st_size} bytes)" for p in made if p.exists()]
    lines += [
        "",
        "Agent note: GIF/animation viewing is not used for verdict; conclusions are based on CSV/TXT metrics and static PNG outputs.",
    ]
    out.write_text("\n".join(lines) + "\n")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--run-root", required=True)
    ap.add_argument("--outdir", default=None)
    ap.add_argument("--ptype", type=int, default=3)
    ap.add_argument("--max-frames", type=int, default=None, help="Optional cap for contact-sheet frames; metrics still use all snapshots")
    args = ap.parse_args()

    run_root = Path(args.run_root)
    outdir = Path(args.outdir) if args.outdir else run_root / "partial_analysis"
    outdir.mkdir(parents=True, exist_ok=True)

    snaps = list_snapshots(run_root)
    log_points = read_all_sync_points(run_root / "run.log")
    metrics: List[SeriesMetric] = []
    frames: List[Dict[str, np.ndarray]] = []
    frame_set = set(range(len(snaps)))
    if args.max_frames and len(snaps) > args.max_frames:
        frame_set = set(np.round(np.linspace(0, len(snaps) - 1, args.max_frames)).astype(int).tolist())

    for i, snap in enumerate(snaps):
        m, fr = read_metric(snap, args.ptype, log_points)
        metrics.append(m)
        if i in frame_set:
            fr["snapshot"] = np.asarray(m.snapshot)
            frames.append(fr)

    csv_path = outdir / "metrics_series.csv"
    write_csv(metrics, csv_path)
    made: List[Path] = [csv_path]
    made += plot_lines(metrics, outdir)
    made.append(contact_sheet(frames, outdir / "contact_faceon_xy.png", "xy"))
    made.append(contact_sheet(frames, outdir / "contact_edgeon_xz.png", "xz"))
    verdict, notes = classify_series(metrics)
    summary_path = outdir / "summary_partial_series.txt"
    write_summary(metrics, verdict, notes, summary_path, made + [summary_path])
    made.append(summary_path)

    print(f"PARTIAL SERIES ANALYSIS DONE: {run_root}")
    print(f"Output: {outdir}")
    print(f"Verdict: {verdict}")
    for n in notes:
        print(f"- {n}")
    print("Files:")
    for p in made:
        print(f"  - {p.name} ({p.stat().st_size:,} bytes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
