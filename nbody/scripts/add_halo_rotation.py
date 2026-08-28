#!/usr/bin/env python3
"""
add_halo_rotation.py — наложить азимутальный поток (net rotation) на
существующий DM-only IC.

Механика: для каждой частицы v_phi_target = k * v_circ(r), к текущей
скорости добавляется приращение (v_phi_target - v_phi_current) в плоскости
xy — случайные скорости сохраняются, добавляется чистый поток вокруг оси z.
v_circ(r) берётся из rotcurve.txt (GalIC) или вычисляется из M(<r) частиц.

Использование:
    python3 add_halo_rotation.py --ic in.hdf5 --output out.hdf5 --k 0.5 \
        [--rotcurve rotcurve.txt] [--ptype 3]
"""
import argparse
import shutil
import sys

import h5py
import numpy as np

G_CODE = 43009.17  # kpc^3/(1e10 Msun (km/s)^2) — единицы GIZMO


def load_vcirc_from_particles(pos, vel, mass):
    """v_circ(r) из накопленной массы частиц (грубая самосогласованная оценка)."""
    c = np.average(pos, axis=0, weights=mass)
    vcm = np.average(vel, axis=0, weights=mass)
    d = pos - c
    r = np.linalg.norm(d, axis=1)
    order = np.argsort(r)
    m_cum = np.cumsum(mass[order])
    r_s = r[order]
    return c, vcm, r_s, m_cum


def vcirc_interp(r_query, r_s, m_cum):
    m_at = np.interp(r_query, r_s, m_cum)
    return np.sqrt(np.clip(G_CODE * m_at / np.clip(r_query, 1e-6, None), 0, None))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ic", required=True)
    ap.add_argument("--output", required=True)
    ap.add_argument("--k", type=float, required=True,
                    help="доля v_circ, задаваемая как азимутальный поток")
    ap.add_argument("--rotcurve", default=None,
                    help="rotcurve.txt от GalIC (r, v_circ, ...) [кпк, км/с]")
    ap.add_argument("--ptype", type=int, default=3)
    args = ap.parse_args()

    with h5py.File(args.ic, "r") as f:
        g = f[f"PartType{args.ptype}"]
        pos = g["Coordinates"][:].astype(np.float64)
        vel = g["Velocities"][:].astype(np.float64)
        mass = (g["Masses"][:].astype(np.float64)
                if "Masses" in g else None)

    if mass is None:
        mass = np.full(len(pos), 1.0)

    c = np.average(pos, axis=0, weights=mass)
    vcm = np.average(vel, axis=0, weights=mass)
    d = pos - c
    v = vel - vcm

    # цилиндрические координаты (ось вращения = z)
    R = np.hypot(d[:, 0], d[:, 1])
    vphi_cur = (-d[:, 0] * v[:, 1] + d[:, 1] * v[:, 0]) / np.clip(R, 1e-6, None)

    if args.rotcurve:
        rc = np.loadtxt(args.rotcurve, skiprows=1)
        vc_of_r = lambda rr: np.interp(rr, rc[:, 0], rc[:, 1])
    else:
        r_s, m_cum = load_vcirc_from_particles(pos, vel, mass)[2:4]
        vc_of_r = lambda rr: vcirc_interp(rr, r_s, m_cum)

    r_q = np.clip(R, 1e-4, None)
    vphi_target = args.k * vc_of_r(r_q)

    # приращение чистого потока: направлено по phi-hat
    e_phi = np.zeros_like(d)
    e_phi[:, 0] = -d[:, 1] / np.clip(R, 1e-6, None)
    e_phi[:, 1] = d[:, 0] / np.clip(R, 1e-6, None)
    dv = (vphi_target - vphi_cur)[:, None] * e_phi
    v_new = v + dv

    vphi_new = (-d[:, 0] * v_new[:, 1] + d[:, 1] * v_new[:, 0]) / np.clip(R, 1e-6, None)
    lz_frac = np.average(vphi_new * R, weights=mass) / np.average(
        vc_of_r(r_q) * r_q, weights=mass)
    print(f"[INFO] k={args.k}  <v_phi>_new = {np.mean(vphi_new):+.2f} km/s")
    print(f"[INFO] J_z fraction vs full circular support: {lz_frac:.3f}")

    shutil.copyfile(args.ic, args.output)
    with h5py.File(args.output, "r+") as f:
        f[f"PartType{args.ptype}/Velocities"][:] = (v_new + vcm).astype(np.float32)
        f["Header"].attrs.create("HaloRotationK", args.k)
        f["Header"].attrs.create("HaloRotationAxis", "z")
    print(f"[OK] сохранено: {args.output}")


if __name__ == "__main__":
    sys.exit(main())
