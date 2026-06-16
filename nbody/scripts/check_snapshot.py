#!/usr/bin/env python3
"""
Unified snapshot checker for GIZMO/GADGET HDF5 snapshots.
Usage:
    python3 check_snapshot.py <snapshot.hdf5> [particle_type]

    particle_type: 1 for DM, 3 for SIDM (default: 3)
"""
import sys
import h5py
import numpy as np


def check_snapshot(path: str, ptype: int = 3):
    gname = f"PartType{ptype}"

    with h5py.File(path, "r") as f:
        # Header
        h = f["Header"].attrs
        print("=" * 55)
        print(f"  File: {path}")
        print(f"  Particle type: PartType{ptype}")
        print("=" * 55)

        time = float(h.get("Time", 0.0))
        redshift = float(h.get("Redshift", 0.0))
        boxsize = float(h.get("BoxSize", 0.0))
        sigma = float(h.get("DM_InteractionCrossSection", 0.0))
        npart = list(h.get("NumPart_ThisFile", [0] * 6))

        print(f"  Time:           {time:.4f}")
        print(f"  Redshift:       {redshift:.4f}")
        print(f"  BoxSize:        {boxsize:.4f}")
        print(f"  Cross-section:  {sigma}")
        print(f"  Particles/file: {npart}")
        print()

        # Check if requested type exists
        if gname not in f:
            available = [k for k in f if k.startswith("PartType")]
            print(f"  ERROR: {gname} not found in snapshot.")
            print(f"  Available: {available}")
            return False

        g = f[gname]

        # Coordinates
        pos = g["Coordinates"][:]
        r = np.linalg.norm(pos, axis=1)
        print("  --- Coordinates ---")
        print(f"    count:  {len(pos)}")
        print(f"    r_min:  {r.min():8.2f}")
        print(f"    r_max:  {r.max():8.2f}")
        print(f"    r_med:  {np.median(r):8.2f}")

        # Velocities
        vel = g["Velocities"][:]
        v = np.linalg.norm(vel, axis=1)
        print("  --- Velocities ---")
        print(f"    v_min:  {v.min():8.4f}")
        print(f"    v_max:  {v.max():8.4f}")
        print(f"    v_med:  {np.median(v):8.4f}")

        # Masses
        mass = g["Masses"][:]
        print("  --- Masses ---")
        print(f"    m_min:  {mass.min():8.4e}")
        print(f"    m_max:  {mass.max():8.4e}")
        print(f"    m_mean: {mass.mean():8.4e}")
        print(f"    m_sum:  {mass.sum():8.4e}")

        # Center of mass
        com = np.sum(pos * mass[:, None], axis=0) / mass.sum()
        com_offset = np.linalg.norm(com)
        print(f"  --- Centering ---")
        print(f"    COM:         ({com[0]:.4f}, {com[1]:.4f}, {com[2]:.4f})")
        print(f"    COM offset:  {com_offset:.4f}")

        # Potential (if present)
        if "Potential" in g:
            pot = g["Potential"][:]
            print(f"  --- Potential ---")
            print(f"    pot_min: {pot.min():10.2f}")
            print(f"    pot_max: {pot.max():10.2f}")

        # AGS kernel radius (if present)
        if "AGS-KernelRadius" in g:
            hsml = g["AGS-KernelRadius"][:]
            print(f"  --- AGS kernel radius ---")
            print(f"    hsml_min:  {hsml.min():.4f}")
            print(f"    hsml_max:  {hsml.max():.4f}")
            print(f"    hsml_med:  {np.median(hsml):.4f}")

        # Particle IDs
        if "ParticleIDs" in g:
            ids = g["ParticleIDs"][:]
            print(f"  --- IDs ---")
            print(f"    id_min:  {ids.min()}")
            print(f"    id_max:  {ids.max()}")
            print(f"    unique:  {np.unique(ids).size} / {ids.size}")

        # SIDM interactions (if present)
        if "NInteractions" in g:
            ni = g["NInteractions"][:]
            nz = np.count_nonzero(ni)
            print(f"  --- SIDM NInteractions ---")
            print(f"    total:         {int(ni.sum())}")
            print(f"    nonzero:       {nz} / {len(ni)} ({100 * nz / len(ni):.2f}%)")
        else:
            print(f"  --- SIDM NInteractions ---")
            print(f"    (not in snapshot)")

        print("=" * 55)
        return True


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    path = sys.argv[1]
    if len(sys.argv) >= 3:
        ptype = int(sys.argv[2])
    else:
        # Try to guess: if PartType3 exists, use 3; else try 1
        with h5py.File(path, "r") as f:
            if "PartType3" in f:
                ptype = 3
            else:
                ptype = 1

    ok = check_snapshot(path, ptype=ptype)
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()