#!/usr/bin/env python3
"""Apply a calibrated, energy-preserving azimuthal sign bias to a halo IC.

The transformation flips only v_phi for a seeded subset of retrograde
particles across the whole halo (selection is by the conserved sign of Lz,
not current position). It calibrates Bullock spin inside an explicitly supplied
R200. It never edits the input file and refuses to
overwrite an existing output. All command-line lengths, masses and velocities
must use one consistent unit system; the default G is for kpc, 1e10 Msun and
km/s, as used by the project's GalIC/GIZMO ICs.
"""
from __future__ import annotations

import argparse
import hashlib
from pathlib import Path
import shutil

import h5py
import numpy as np

G_CODE = 43007.1  # kpc (km/s)^2 / (1e10 Msun)


def mass_array(group: h5py.Group, header: h5py.Group, ptype: int) -> np.ndarray:
    """Return particle masses, honoring Gadget's constant-mass Header table."""
    if "Masses" in group:
        masses = np.asarray(group["Masses"], dtype=np.float64)
    else:
        table = np.asarray(header.attrs.get("MassTable", []), dtype=np.float64)
        if ptype >= len(table) or not np.isfinite(table[ptype]) or table[ptype] <= 0:
            raise ValueError(f"PartType{ptype} has no usable Masses dataset/MassTable entry")
        masses = np.full(len(group["Coordinates"]), table[ptype], dtype=np.float64)
    if masses.ndim != 1 or not np.all(np.isfinite(masses)) or np.any(masses <= 0):
        raise ValueError("particle masses must be finite, positive, and one-dimensional")
    return masses


def halo_frame(positions: np.ndarray, velocities: np.ndarray, masses: np.ndarray):
    """Robust shrinking-sphere position center and mass-weighted bulk velocity."""
    if positions.ndim != 2 or positions.shape[1] != 3 or velocities.shape != positions.shape:
        raise ValueError("positions and velocities must both have shape (N, 3)")
    if len(positions) != len(masses) or len(masses) == 0:
        raise ValueError("positions, velocities, and masses must have the same nonzero N")
    if not np.all(np.isfinite(positions)) or not np.all(np.isfinite(velocities)):
        raise ValueError("positions and velocities must be finite")
    # Match the repository's established shrink_center convention: repeatedly
    # recenter on the innermost 10% (at least 100 particles when available).
    center = np.average(positions, axis=0, weights=masses)
    for _ in range(10):
        radius = np.linalg.norm(positions - center, axis=1)
        ncut = min(len(radius), max(1, max(100, int(0.10 * len(radius)))))
        cutoff = np.partition(radius, ncut - 1)[ncut - 1]
        selected = radius <= cutoff
        center = np.average(positions[selected], axis=0, weights=masses[selected])
    bulk_velocity = np.average(velocities, axis=0, weights=masses)
    return center, bulk_velocity


def angular_momentum(positions: np.ndarray, velocities: np.ndarray, masses: np.ndarray,
                     center: np.ndarray, bulk_velocity: np.ndarray, r200: float):
    """Return mass and angular-momentum vector inside spherical R200."""
    if not np.isfinite(r200) or r200 <= 0:
        raise ValueError("R200 must be finite and positive")
    dx = positions - center
    dv = velocities - bulk_velocity
    inside = np.linalg.norm(dx, axis=1) <= r200
    if not np.any(inside):
        raise ValueError("no particles lie inside R200")
    mass200 = float(np.sum(masses[inside]))
    jvec = np.sum(np.cross(dx[inside], dv[inside]) * masses[inside, None], axis=0)
    return mass200, jvec, inside


def bullock_lambda_prime(mass200: float, jvec: np.ndarray, r200: float, grav_const: float):
    """Bullock spin lambda'=|J|/(sqrt(2) M200 V200 R200), V200=sqrt(GM/R)."""
    if not np.isfinite(grav_const) or grav_const <= 0:
        raise ValueError("G must be finite and positive")
    v200 = np.sqrt(grav_const * mass200 / r200)
    denom = np.sqrt(2.0) * mass200 * v200 * r200
    return float(np.linalg.norm(jvec) / denom), float(v200)


def _flip_candidates(dx: np.ndarray, dv: np.ndarray, masses: np.ndarray, inside: np.ndarray):
    """Return all retrograde candidates and their R200 angular-momentum deltas.

    Candidate selection spans the whole halo and depends on sign(Lz), never the
    particle's instantaneous radius. Particles outside R200 therefore remain
    eligible for the phase-independent sign bias, but contribute zero to the
    initial-aperture target calibration.
    """
    R = np.hypot(dx[:, 0], dx[:, 1])
    safe_R = np.where(R > 0, R, 1.0)
    vphi = (-dx[:, 1] * dv[:, 0] + dx[:, 0] * dv[:, 1]) / safe_R
    lz = masses * R * vphi
    candidates = np.flatnonzero((R > 0) & (lz < 0))
    ephi = np.zeros((len(candidates), 3), dtype=np.float64)
    ephi[:, 0] = -dx[candidates, 1] / R[candidates]
    ephi[:, 1] = dx[candidates, 0] / R[candidates]
    delta_v = -2.0 * vphi[candidates, None] * ephi
    delta_j = masses[candidates, None] * np.cross(dx[candidates], delta_v)
    delta_j[~inside[candidates]] = 0.0
    delta_p = masses[candidates, None] * delta_v
    return candidates, delta_j, delta_p


def apply_spin_bias(positions: np.ndarray, velocities: np.ndarray, masses: np.ndarray,
                    r200: float, target_lambda_prime: float, seed: int = 12345,
                    grav_const: float = G_CODE, lambda_tolerance: float = 5e-4):
    """Flip a reproducible subset of retrograde v_phi to approach target lambda'.

    The target is a positive-z-aligned Bullock spin magnitude inside R200.
    A seeded random ordering is applied to *all* retrograde particles in the
    halo; selection does not depend on current radius, so it is a particle tag
    coupled to the conserved sign of Lz rather than orbital phase. Each selected
    particle has only v_phi reversed. The closest discrete target vector is
    chosen; if it misses lambda_tolerance, fail instead of silently accepting.
    Returns a copied velocity array and a report containing achieved metrics.
    """
    positions = np.asarray(positions, dtype=np.float64)
    velocities = np.asarray(velocities, dtype=np.float64)
    masses = np.asarray(masses, dtype=np.float64)
    if not np.isfinite(target_lambda_prime) or target_lambda_prime < 0:
        raise ValueError("target lambda_prime must be finite and nonnegative")
    if not np.isfinite(lambda_tolerance) or lambda_tolerance <= 0:
        raise ValueError("lambda_tolerance must be finite and positive")
    if not np.all(np.isfinite(masses)) or np.any(masses <= 0):
        raise ValueError("particle masses must be finite and positive")
    center, bulk = halo_frame(positions, velocities, masses)
    dx, dv = positions - center, velocities - bulk
    mass200, j_initial, inside = angular_momentum(positions, velocities, masses,
                                                   center, bulk, r200)
    lambda_initial, v200 = bullock_lambda_prime(mass200, j_initial, r200, grav_const)
    target_j = np.sqrt(2.0) * target_lambda_prime * mass200 * v200 * r200
    if float(j_initial[2]) > target_j + 1e-12 * max(target_j, 1.0):
        raise ValueError("current positive Jz already exceeds the requested aligned target")
    candidates, delta_j, delta_p = _flip_candidates(dx, dv, masses, inside)
    if len(candidates) == 0:
        raise ValueError("no retrograde particles available for sign-bias")
    rng = np.random.default_rng(seed)
    order = rng.permutation(len(candidates))
    candidates, delta_j, delta_p = candidates[order], delta_j[order], delta_p[order]

    # Calibrate the R200 angular-momentum vector for every random-prefix size.
    # Include the bulk-velocity change caused by finite-sample asymmetric flips.
    cumulative_j = np.vstack((np.zeros(3), np.cumsum(delta_j, axis=0)))
    cumulative_p = np.vstack((np.zeros(3), np.cumsum(delta_p, axis=0)))
    total_mass = float(np.sum(masses))
    aperture_offset = np.sum(dx[inside] * masses[inside, None], axis=0)
    bulk_shifts = cumulative_p / total_mass
    trial_j = (j_initial[None, :] + cumulative_j
               - np.cross(aperture_offset[None, :], bulk_shifts))
    target_vector = np.array([0.0, 0.0, target_j])
    trial_errors = np.linalg.norm(trial_j - target_vector[None, :], axis=1)
    nflip = int(np.argmin(trial_errors))
    target_error_lambda = float(trial_errors[nflip] / (
        np.sqrt(2.0) * mass200 * v200 * r200))
    if target_error_lambda > lambda_tolerance:
        raise ValueError(
            f"target vector is not attainable within lambda tolerance: "
            f"best error={target_error_lambda:.6g}, tolerance={lambda_tolerance:.6g}"
        )
    selected = candidates[:nflip]

    out = velocities.copy()
    R = np.hypot(dx[selected, 0], dx[selected, 1])
    ephi = np.zeros((len(selected), 3), dtype=np.float64)
    ephi[:, 0] = -dx[selected, 1] / R
    ephi[:, 1] = dx[selected, 0] / R
    vphi = np.einsum("ij,ij->i", dv[selected], ephi)
    out[selected] -= (2.0 * vphi)[:, None] * ephi

    final_bulk = np.average(out, axis=0, weights=masses)
    mass_final, j_final, _ = angular_momentum(positions, out, masses, center, final_bulk, r200)
    lambda_final, _ = bullock_lambda_prime(mass_final, j_final, r200, grav_const)
    speed0 = np.sum(dv[selected] ** 2, axis=1)
    speed1 = np.sum((out[selected] - bulk) ** 2, axis=1)
    flipped_inside = np.linalg.norm(positions[selected] - center, axis=1) <= r200
    report = {
        "center": center,
        "bulk_velocity_initial": bulk,
        "bulk_velocity_final": final_bulk,
        "bulk_velocity_delta": final_bulk - bulk,
        "mass200": mass200,
        "r200": float(r200),
        "v200": v200,
        "j_initial": j_initial,
        "j_final": j_final,
        "lambda_prime_initial": lambda_initial,
        "lambda_prime_target": float(target_lambda_prime),
        "lambda_prime_final": lambda_final,
        "particles_inside_r200": int(np.count_nonzero(inside)),
        "retrograde_candidates": int(len(candidates)),
        "retrograde_candidates_inside_r200": int(np.count_nonzero(inside[candidates])),
        "particles_flipped": int(nflip),
        "particles_flipped_inside_r200": int(np.count_nonzero(flipped_inside)),
        "particles_flipped_outside_r200": int(nflip - np.count_nonzero(flipped_inside)),
        "target_vector_error_lambda": target_error_lambda,
        "flipped_speed_squared_max_abs_error": float(np.max(np.abs(speed1 - speed0))) if nflip else 0.0,
        "seed": int(seed),
    }
    return out, report


def transform_ic(input_path: Path, output_path: Path, ptype: int, r200: float,
                 target_lambda_prime: float, seed: int, grav_const: float,
                 lambda_tolerance: float = 5e-4):
    input_path, output_path = input_path.resolve(), output_path.resolve()
    if input_path == output_path:
        raise ValueError("output path must differ from input path")
    if output_path.exists():
        raise FileExistsError(f"refusing to overwrite existing output: {output_path}")
    if not input_path.is_file():
        raise FileNotFoundError(input_path)
    with h5py.File(input_path, "r") as src:
        group = src[f"PartType{ptype}"]
        positions = np.asarray(group["Coordinates"], dtype=np.float64)
        velocities = np.asarray(group["Velocities"], dtype=np.float64)
        masses = mass_array(group, src["Header"], ptype)
    new_velocities, report = apply_spin_bias(positions, velocities, masses, r200,
                                              target_lambda_prime, seed, grav_const,
                                              lambda_tolerance)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(input_path, output_path)
    with h5py.File(output_path, "r+") as out:
        out[f"PartType{ptype}/Velocities"][:] = new_velocities.astype(out[f"PartType{ptype}/Velocities"].dtype)
        attrs = out["Header"].attrs
        attrs["HaloSpinBiasMethod"] = "retrograde_vphi_sign_flip_v1"
        attrs["HaloSpinBiasAxis"] = "z"
        attrs["HaloSpinBiasSeed"] = report["seed"]
        attrs["HaloSpinBiasR200"] = report["r200"]
        attrs["HaloSpinBiasTargetBullockLambdaPrime"] = report["lambda_prime_target"]
        attrs["HaloSpinBiasMeasuredBullockLambdaPrime"] = report["lambda_prime_final"]
        attrs["HaloSpinBiasParticlesFlipped"] = report["particles_flipped"]
        attrs["HaloSpinBiasInputSHA256"] = hashlib.sha256(input_path.read_bytes()).hexdigest()
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ic", type=Path, required=True, help="input HDF5 IC; never modified")
    parser.add_argument("--output", type=Path, required=True, help="new output path; must not exist")
    parser.add_argument("--ptype", type=int, default=3)
    parser.add_argument("--r200", type=float, required=True, help="R200 in IC length units")
    parser.add_argument("--lambda-prime", type=float, default=0.035, dest="lambda_prime")
    parser.add_argument("--lambda-tolerance", type=float, default=5e-4)
    parser.add_argument("--seed", type=int, default=12345)
    parser.add_argument("--G", type=float, default=G_CODE, dest="grav_const")
    args = parser.parse_args()
    report = transform_ic(args.ic, args.output, args.ptype, args.r200,
                          args.lambda_prime, args.seed, args.grav_const,
                          args.lambda_tolerance)
    print(f"[OK] wrote {args.output}")
    for key in ("r200", "mass200", "v200", "lambda_prime_initial", "lambda_prime_target",
                "lambda_prime_final", "particles_inside_r200", "retrograde_candidates",
                "retrograde_candidates_inside_r200", "particles_flipped",
                "particles_flipped_inside_r200", "particles_flipped_outside_r200",
                "target_vector_error_lambda", "flipped_speed_squared_max_abs_error", "seed"):
        print(f"{key}={report[key]}")


if __name__ == "__main__":
    main()
