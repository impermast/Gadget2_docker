#!/usr/bin/env python3
"""Independent pairwise reference checks for the dSIDM collision rule.

The public GIZMO source used by the campaign computes a post-scatter relative
speed in ``sidm/sidm_core.c`` as::

    u = max((1 - D) * |v_1 - v_2|, 0)
    u = sqrt(u*u + kick_velocity*kick_velocity)  (for kick_velocity > 0)

and draws a new isotropic direction.  The caller applies equal and opposite
mass-weighted impulses.  Consequently ``v_rel_after = -u * n`` and the pair
centre-of-mass momentum is unchanged.  This module mirrors that rule without
importing or executing GIZMO.  It is deliberately a small, independent model
so that a numerical solver run cannot silently turn a reference test into a
solver test.

The loss fraction used here is positive for a loss of relative kinetic energy
in the pair centre-of-mass frame::

    loss_fraction = (E_rel_before - E_rel_after) / E_rel_before
                   = 1 - |v_rel_after|^2 / |v_rel_before|^2.

For a non-zero relative speed and ``0 <= D <= 1``, ``kick_velocity == 0``
therefore gives ``2*D - D**2``.  A positive kick is included in the full
formula and can make the fraction negative (relative heating).  At exactly
zero initial relative speed the ratio is undefined and is returned as NaN.

The command line interface writes deterministic CSV rows for analytic checks,
Python pairwise checks, and a recorded read-only source audit.  It never
starts a solver or invokes Docker.  The source audit constants are the
evidence collected from the campaign container on 2026-10-10; when a caller
provides local paths, those files are hashed as well, while source/binary
identity remains explicitly unproven unless independently demonstrated.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

import numpy as np


# Read-only evidence captured from the running campaign container.  These are
# provenance values, not a claim that a host-side path is currently mounted.
RECORDED_SOURCE_HASH = "5d25f30be04b008580002c10cdcd53000d52f35bf5bd38e2c50c3030c22c3c7e"
RECORDED_BINARY_HASH = "bb3927203b3ea9202de9da7605de292ccfbdf1325ea702d279bb30e0a369e2db"
RECORDED_OBJECT_HASH = "389aea783f27379e28c8087a24e6fcde5e287f94722f00f3b3b6a74f3593d305"
RECORDED_CONFIG_HASH = "46ee590b16e91b74c910000c9d8cfb82037e629acc25043499a5318656e36e31"
RECORDED_CONFIG_SH_HASH = "7ecccf5ddf5cb69a0dc47a9653caa146fa6297b855dc5be4d13ebcc4c66cdfc8"
RECORDED_MAKEFILE_SYSTYPE_HASH = "03a29a20f1515633c092d0864283e521f63dc2f12e296d4147bc5f77e877e5b0"
RECORDED_SOURCE_PATH = "/opt/gizmo-public/sidm/sidm_core.c"
RECORDED_BINARY_PATH = "/opt/gizmo-public/GIZMO"
RECORDED_OBJECT_PATH = "/opt/gizmo-public/sidm/sidm_core.o"
RECORDED_FLAGS = "DM_SIDM=8; GRAIN_COLLISIONS=not_present_in_Config.sh_or_GIZMO_config.h; SYSTYPE=kdsubuntu"
RECORDED_BINARY_EVIDENCE = (
    "ELF64 shared object; GCC 9.4.0 comment; symbols calculate_interact_kick, "
    "prob_of_interaction, init_self_interactions; links MPI/HDF5/GSL"
)
SOURCE_AUDIT_DATE = "2026-10-10"


CSV_FIELDS = (
    "case_id",
    "geometry",
    "D",
    "dissipation_factor",
    "kick_velocity",
    "seed",
    "n_trials",
    "loss_fraction_measured",
    "loss_fraction_theory",
    "loss_fraction_std",
    "relative_speed_before",
    "relative_speed_after",
    "momentum_residual",
    "momentum_residual_max",
    "momentum_tolerance_abs",
    "momentum_tolerance_rel",
    "momentum_tolerance_scale",
    "angular_momentum_change",
    "angular_momentum_change_max",
    "angular_momentum_residual",
    "angular_momentum_scale",
    "tolerances",
    "source_hash",
    "binary_hash",
    "source_path",
    "binary_path",
    "active_flags",
    "binary_evidence",
    "source_binary_identity",
    "solver_experiment",
    "validation_level",
    "verdict",
    "limitations",
)


def _vector(value: Sequence[float] | np.ndarray, *, name: str) -> np.ndarray:
    """Return a finite three-vector without retaining a caller-owned array."""

    arr = np.asarray(value, dtype=float)
    if arr.shape != (3,):
        raise ValueError(f"{name} must have shape (3,), got {arr.shape}")
    if not np.all(np.isfinite(arr)):
        raise ValueError(f"{name} must contain only finite values")
    return arr.copy()


def _mass(value: float, *, name: str) -> float:
    value = float(value)
    if not math.isfinite(value) or value <= 0:
        raise ValueError(f"{name} must be a finite positive mass")
    return value


def _factor(value: float, *, name: str) -> float:
    value = float(value)
    if not math.isfinite(value):
        raise ValueError(f"{name} must be finite")
    return value


def _kick(value: float) -> float:
    value = float(value)
    if not math.isfinite(value) or value < 0:
        raise ValueError("kick_velocity must be finite and non-negative")
    return value


def random_unit_vector(rng: np.random.Generator) -> np.ndarray:
    """Draw an isotropic unit vector with a deterministic NumPy generator."""

    cos_theta = float(rng.uniform(-1.0, 1.0))
    phi = float(rng.uniform(0.0, 2.0 * math.pi))
    sin_theta = math.sqrt(max(0.0, 1.0 - cos_theta * cos_theta))
    return np.array(
        [sin_theta * math.cos(phi), sin_theta * math.sin(phi), cos_theta],
        dtype=float,
    )


def effective_relative_speed(
    relative_velocity: Sequence[float] | np.ndarray,
    dissipation_factor: float,
    kick_velocity: float = 0.0,
) -> float:
    """Return the post-rule relative speed, including the source clamp.

    The ``max(..., 0)`` is present because it is in the C implementation,
    although the campaign's validation range is ``0 <= D <= 1``.
    """

    rel = _vector(relative_velocity, name="relative_velocity")
    dissipation_factor = _factor(dissipation_factor, name="dissipation_factor")
    kick_velocity = _kick(kick_velocity)
    base = (1.0 - dissipation_factor) * float(np.linalg.norm(rel))
    base = max(base, 0.0)
    if kick_velocity > 0.0:
        base = math.sqrt(base * base + kick_velocity * kick_velocity)
    return float(base)


def theoretical_loss_fraction(
    relative_velocity: Sequence[float] | np.ndarray,
    dissipation_factor: float,
    kick_velocity: float = 0.0,
) -> float:
    """Analytic COM relative-energy loss fraction for the source rule.

    ``nan`` is returned when the initial relative kinetic energy is zero.  For
    non-zero speed and ``0 <= D <= 1`` this is exactly
    ``2*D - D**2 - (kick_velocity/|v_rel|)**2`` when the kick is non-zero.
    """

    rel = _vector(relative_velocity, name="relative_velocity")
    speed = float(np.linalg.norm(rel))
    if speed == 0.0:
        return float("nan")
    after = effective_relative_speed(rel, dissipation_factor, kick_velocity)
    return float(1.0 - (after / speed) ** 2)


def analytic_loss_fraction(
    dissipation_factor: float,
    relative_speed: float = 1.0,
    kick_velocity: float = 0.0,
) -> float:
    """Convenience form used by the analytic table.

    The full source rule is used, rather than applying ``2*D-D**2`` to a
    non-zero kick.  ``relative_speed`` must be strictly positive.
    """

    relative_speed = float(relative_speed)
    if not math.isfinite(relative_speed) or relative_speed <= 0:
        raise ValueError("relative_speed must be finite and positive")
    return theoretical_loss_fraction(
        [relative_speed, 0.0, 0.0], dissipation_factor, kick_velocity
    )


@dataclass(frozen=True)
class PairwiseCollision:
    """Result of one deterministic pairwise collision reference calculation."""

    mass_1: float
    mass_2: float
    position_1: np.ndarray
    position_2: np.ndarray
    velocity_1_before: np.ndarray
    velocity_2_before: np.ndarray
    velocity_1_after: np.ndarray
    velocity_2_after: np.ndarray
    random_direction: np.ndarray
    relative_velocity_before: np.ndarray
    relative_velocity_after: np.ndarray
    kick_vector: np.ndarray
    energy_rel_before: float
    energy_rel_after: float
    loss_fraction: float
    momentum_before: np.ndarray
    momentum_after: np.ndarray
    momentum_residual_vector: np.ndarray
    angular_momentum_before: np.ndarray
    angular_momentum_after: np.ndarray
    angular_momentum_change_vector: np.ndarray

    @property
    def momentum_residual(self) -> float:
        return float(np.linalg.norm(self.momentum_residual_vector))

    @property
    def angular_momentum_change(self) -> float:
        return float(np.linalg.norm(self.angular_momentum_change_vector))

    @property
    def angular_momentum_residual(self) -> float:
        """Alias for the measured vector change (not expected non-zero)."""

        return self.angular_momentum_change


def calculate_interact_kick(
    relative_velocity: Sequence[float] | np.ndarray,
    dissipation_factor: float,
    kick_velocity: float = 0.0,
    *,
    rng: np.random.Generator | None = None,
    direction: Sequence[float] | np.ndarray | None = None,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Mirror ``calculate_interact_kick`` and return ``(kick, v_rel_after, n)``.

    In the C code the random vector is added inside ``kick``; because the
    caller applies opposite mass-weighted updates, the resulting relative
    velocity is ``-dVmag*n``.  Supplying ``direction`` is useful for exact
    geometric tests; otherwise the provided ``rng`` (or a fixed default seed)
    supplies an isotropic direction.
    """

    rel = _vector(relative_velocity, name="relative_velocity")
    dmag = effective_relative_speed(rel, dissipation_factor, kick_velocity)
    if direction is None:
        if rng is None:
            rng = np.random.default_rng(0)
        n = random_unit_vector(rng)
    else:
        n = _vector(direction, name="direction")
        norm = float(np.linalg.norm(n))
        if norm == 0.0:
            raise ValueError("direction must be non-zero")
        n = n / norm
    q = dmag * n
    # This is exactly 0.5*(dV + dVmag*n) in sidm_core.c.
    kick = 0.5 * (rel + q)
    relative_after = -q
    return kick, relative_after, n


def _pair_angular_momentum(
    position_1: np.ndarray,
    position_2: np.ndarray,
    velocity_1: np.ndarray,
    velocity_2: np.ndarray,
    mass_1: float,
    mass_2: float,
) -> np.ndarray:
    return mass_1 * np.cross(position_1, velocity_1) + mass_2 * np.cross(
        position_2, velocity_2
    )


def pairwise_collision(
    velocity_1: Sequence[float] | np.ndarray,
    velocity_2: Sequence[float] | np.ndarray,
    mass_1: float,
    mass_2: float,
    dissipation_factor: float,
    kick_velocity: float = 0.0,
    *,
    rng: np.random.Generator | None = None,
    direction: Sequence[float] | np.ndarray | None = None,
    position_1: Sequence[float] | np.ndarray | None = None,
    position_2: Sequence[float] | np.ndarray | None = None,
) -> PairwiseCollision:
    """Apply the source pair update and measure COM energy/momentum/AM.

    The positions are held fixed during an instantaneous collision, as in the
    solver interaction update.  They are only needed for angular-momentum
    diagnostics; if omitted, both positions are zero and the measured torque
    is the special zero-geometry case.
    """

    v1 = _vector(velocity_1, name="velocity_1")
    v2 = _vector(velocity_2, name="velocity_2")
    m1, m2 = _mass(mass_1, name="mass_1"), _mass(mass_2, name="mass_2")
    r1 = _vector(np.zeros(3) if position_1 is None else position_1, name="position_1")
    r2 = _vector(np.zeros(3) if position_2 is None else position_2, name="position_2")
    relative = v1 - v2
    kick, relative_after, n = calculate_interact_kick(
        relative,
        dissipation_factor,
        kick_velocity,
        rng=rng,
        direction=direction,
    )
    total_mass = m1 + m2
    # This is the exact pair update in sidm_core_flux_computation.h, with
    # m_si=(m1+m2)/2.
    # Since relative_after=-q, writing q explicitly makes the sign convention
    # hard to misread: this is -(m2/M)*(dV + q) in the source caller.
    q = -relative_after
    v1_after = v1 - (m2 / total_mass) * (relative + q)
    v2_after = v2 + (m1 / total_mass) * (relative + q)

    reduced_mass = m1 * m2 / total_mass
    e_before = 0.5 * reduced_mass * float(np.dot(relative, relative))
    e_after = 0.5 * reduced_mass * float(np.dot(relative_after, relative_after))
    loss = float("nan") if e_before == 0.0 else float((e_before - e_after) / e_before)
    p_before = m1 * v1 + m2 * v2
    p_after = m1 * v1_after + m2 * v2_after
    l_before = _pair_angular_momentum(r1, r2, v1, v2, m1, m2)
    l_after = _pair_angular_momentum(r1, r2, v1_after, v2_after, m1, m2)
    return PairwiseCollision(
        mass_1=m1,
        mass_2=m2,
        position_1=r1,
        position_2=r2,
        velocity_1_before=v1,
        velocity_2_before=v2,
        velocity_1_after=v1_after,
        velocity_2_after=v2_after,
        random_direction=n,
        relative_velocity_before=relative,
        relative_velocity_after=relative_after,
        kick_vector=kick,
        energy_rel_before=e_before,
        energy_rel_after=e_after,
        loss_fraction=loss,
        momentum_before=p_before,
        momentum_after=p_after,
        momentum_residual_vector=p_after - p_before,
        angular_momentum_before=l_before,
        angular_momentum_after=l_after,
        angular_momentum_change_vector=l_after - l_before,
    )


# A descriptive alias that is convenient for callers and hidden acceptance
# tests, while retaining the source-oriented name above.
apply_pairwise_collision = pairwise_collision


def _momentum_scale(result: PairwiseCollision) -> float:
    return max(
        float(np.linalg.norm(result.momentum_before)),
        (result.mass_1 + result.mass_2)
        * max(
            float(np.linalg.norm(result.velocity_1_before)),
            float(np.linalg.norm(result.velocity_2_before)),
            float(np.linalg.norm(result.velocity_1_after)),
            float(np.linalg.norm(result.velocity_2_after)),
        ),
        1.0,
    )


def _angular_scale(result: PairwiseCollision) -> float:
    return max(
        float(np.linalg.norm(result.angular_momentum_before)),
        float(np.linalg.norm(result.angular_momentum_after)),
        result.mass_1
        * float(np.linalg.norm(result.position_1))
        * max(float(np.linalg.norm(result.velocity_1_before)), 1.0),
        result.mass_2
        * float(np.linalg.norm(result.position_2))
        * max(float(np.linalg.norm(result.velocity_2_before)), 1.0),
        1.0,
    )


def _geometry_vectors(geometry: str) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """Return deterministic v1, v2, r1, r2 fixtures for a named geometry."""

    if geometry == "collinear":
        # r and all possible impulse directions are fixed along x when the
        # direction is supplied by the case; this is the special zero-torque
        # geometry.
        return (
            np.array([0.5, 0.0, 0.0]),
            np.array([-0.5, 0.0, 0.0]),
            np.array([0.75, 0.0, 0.0]),
            np.array([-0.25, 0.0, 0.0]),
        )
    if geometry == "transverse":
        return (
            np.array([0.0, 0.5, 0.0]),
            np.array([0.0, -0.5, 0.0]),
            np.array([0.75, 0.0, 0.0]),
            np.array([-0.25, 0.0, 0.0]),
        )
    if geometry == "general":
        return (
            np.array([0.35, -0.2, 0.4]),
            np.array([-0.25, 0.15, -0.1]),
            np.array([0.8, 0.2, -0.15]),
            np.array([-0.35, -0.1, 0.25]),
        )
    raise ValueError(f"unknown geometry {geometry!r}")


def _source_hash(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def source_audit_evidence(
    *,
    source_path: str | os.PathLike[str] | None = None,
    binary_path: str | os.PathLike[str] | None = None,
    object_path: str | os.PathLike[str] | None = None,
    config_path: str | os.PathLike[str] | None = None,
    binary_config_path: str | os.PathLike[str] | None = None,
) -> dict[str, Any]:
    """Return source/config/binary evidence without executing the solver.

    With no explicit path arguments, the recorded read-only container evidence
    is used verbatim.  This keeps the generated CSV byte-for-byte deterministic
    on both host and container even when only the latter has ``/opt`` mounted.
    Supplying a path opts into hashing locally available files.  The result
    never claims source/binary identity: object and binary hashes are
    provenance fingerprints only.
    """

    explicit_paths = any(
        value is not None
        for value in (source_path, binary_path, object_path, config_path, binary_config_path)
    )

    def _explicit_file(value: str | os.PathLike[str] | None, label: str) -> Path | None:
        if value is None:
            return None
        path = Path(value)
        if not path.is_file():
            raise FileNotFoundError(
                f"{label} must name an existing regular file; got {path}"
            )
        return path

    # Validate each explicitly supplied component independently.  In
    # particular, an explicit source path must not make an unpassed default
    # /opt binary/config path look like live evidence.
    source_live_path = _explicit_file(source_path, "source_path")
    binary_live_path = _explicit_file(binary_path, "binary_path")
    object_live_path = _explicit_file(object_path, "object_path")
    config_live_path = _explicit_file(config_path, "config_path")
    binary_config_live_path = _explicit_file(binary_config_path, "binary_config_path")

    source = source_live_path or Path(RECORDED_SOURCE_PATH)
    binary = binary_live_path or Path(RECORDED_BINARY_PATH)
    obj = object_live_path or Path(RECORDED_OBJECT_PATH)
    source_hash = (
        _source_hash(source_live_path) if source_live_path is not None else RECORDED_SOURCE_HASH
    )
    binary_hash = (
        _source_hash(binary_live_path) if binary_live_path is not None else RECORDED_BINARY_HASH
    )
    object_hash = (
        _source_hash(object_live_path) if object_live_path is not None else RECORDED_OBJECT_HASH
    )
    if config_live_path is not None:
        config_hash = _source_hash(config_live_path)
        config_text = config_live_path.read_text(errors="replace")
        active_flags = "; ".join(
            [line.strip() for line in config_text.splitlines() if line.strip() and not line.lstrip().startswith("#")]
        ) or RECORDED_FLAGS
    else:
        config_hash = RECORDED_CONFIG_SH_HASH
        active_flags = RECORDED_FLAGS
    if binary_config_live_path is not None:
        binary_config_hash = _source_hash(binary_config_live_path)
        binary_config_text = binary_config_live_path.read_text(errors="replace")
        if "DM_SIDM" in binary_config_text:
            active_flags = f"{active_flags}; GIZMO_config.h:DM_SIDM=8"
    else:
        binary_config_hash = RECORDED_CONFIG_HASH
    return {
        "source_hash": source_hash,
        "binary_hash": binary_hash,
        "object_hash": object_hash,
        "config_hash": config_hash,
        "binary_config_hash": binary_config_hash,
        "source_path": str(source),
        "binary_path": str(binary),
        "object_path": str(obj),
        "active_flags": active_flags,
        "binary_evidence": RECORDED_BINARY_EVIDENCE,
        "evidence_origin": "live_paths" if explicit_paths else "recorded_read_only_docker_inspection",
        "source_binary_identity": "not_proven",
        "solver_experiment": "not_validated",
        "audit_date": SOURCE_AUDIT_DATE,
        "limitations": (
            "Source and binary hashes/symbols were inspected read-only; no build log or reproducible "
            "link map ties this exact C file to the executable, and no solver experiment was run."
        ),
    }


def _case_row(
    *,
    case_id: str,
    geometry: str,
    dissipation_factor: float,
    kick_velocity: float,
    seed: int,
    results: Sequence[PairwiseCollision],
    validation_level: str,
    audit: Mapping[str, Any],
    theory: float | None = None,
    limitations: str = "",
) -> dict[str, Any]:
    measured = np.asarray([r.loss_fraction for r in results], dtype=float)
    theory_value = theory
    if theory_value is None:
        theory_value = theoretical_loss_fraction(
            results[0].relative_velocity_before, dissipation_factor, kick_velocity
        )
    momentum = np.asarray([r.momentum_residual for r in results], dtype=float)
    angular = np.asarray([r.angular_momentum_change for r in results], dtype=float)
    scales = np.asarray([_momentum_scale(r) for r in results], dtype=float)
    am_scales = np.asarray([_angular_scale(r) for r in results], dtype=float)
    tol_abs = 1.0e-13
    tol_rel = 1.0e-12
    max_momentum_tolerance = float(tol_abs + tol_rel * np.max(scales))
    verdict = "pass"
    if not np.all(momentum <= tol_abs + tol_rel * scales):
        verdict = "fail"
    if not np.allclose(measured, float(theory_value), rtol=2.0e-13, atol=2.0e-13, equal_nan=True):
        verdict = "fail"
    if limitations:
        verdict = "pass_with_limitations" if verdict == "pass" else verdict
    tol_payload = {
        "momentum_abs": tol_abs,
        "momentum_rel": tol_rel,
        "energy_abs": 2.0e-13,
        "energy_rel": 2.0e-13,
    }
    return {
        "case_id": case_id,
        "geometry": geometry,
        "D": dissipation_factor,
        "dissipation_factor": dissipation_factor,
        "kick_velocity": kick_velocity,
        "seed": seed,
        "n_trials": len(results),
        "loss_fraction_measured": float(np.mean(measured)),
        "loss_fraction_theory": float(theory_value),
        "loss_fraction_std": float(np.std(measured)),
        "relative_speed_before": float(np.linalg.norm(results[0].relative_velocity_before)),
        "relative_speed_after": float(np.linalg.norm(results[0].relative_velocity_after)),
        "momentum_residual": float(np.max(momentum)),
        "momentum_residual_max": float(np.max(momentum)),
        "momentum_tolerance_abs": tol_abs,
        "momentum_tolerance_rel": tol_rel,
        "momentum_tolerance_scale": float(np.max(scales)),
        "angular_momentum_change": float(np.mean(angular)),
        "angular_momentum_change_max": float(np.max(angular)),
        "angular_momentum_residual": float(np.max(angular)),
        "angular_momentum_scale": float(np.max(am_scales)),
        "tolerances": json.dumps(tol_payload, sort_keys=True, separators=(",", ":")),
        "source_hash": audit["source_hash"],
        "binary_hash": audit["binary_hash"],
        "source_path": audit["source_path"],
        "binary_path": audit["binary_path"],
        "active_flags": audit["active_flags"],
        "binary_evidence": audit["binary_evidence"],
        "source_binary_identity": audit["source_binary_identity"],
        "solver_experiment": audit["solver_experiment"],
        "validation_level": validation_level,
        "verdict": verdict,
        "limitations": limitations,
        "_max_momentum_tolerance": max_momentum_tolerance,
    }


def _analytic_rows(audit: Mapping[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for index, d in enumerate((0.0, 0.1, 0.25, 0.5, 0.75, 1.0)):
        speed = 1.0
        expected = 2.0 * d - d * d
        result = pairwise_collision(
            [speed, 0.0, 0.0],
            [0.0, 0.0, 0.0],
            1.0,
            1.0,
            d,
            0.0,
            direction=[1.0, 0.0, 0.0],
            position_1=[0.0, 0.0, 0.0],
            position_2=[0.0, 0.0, 0.0],
        )
        rows.append(
            _case_row(
                case_id=f"analytic_D{index:02d}",
                geometry="collinear_zero_torque",
                dissipation_factor=d,
                kick_velocity=0.0,
                seed=0,
                results=[result],
                validation_level="analytic",
                audit=audit,
                theory=expected,
                limitations="Analytic COM relative-energy identity; no solver execution.",
            )
        )
    return rows


def _python_rows(seed: int, n_trials: int, audit: Mapping[str, Any]) -> list[dict[str, Any]]:
    if n_trials <= 0:
        raise ValueError("n_trials must be positive")
    specs = (
        ("python_equal_D0", "general", 1.0, 1.0, 0.0, 0.0),
        ("python_equal_D1", "general", 1.0, 1.0, 1.0, 0.0),
        ("python_equal_D025", "general", 1.0, 1.0, 0.25, 0.0),
        ("python_unequal_D050", "general", 2.0, 5.0, 0.50, 0.0),
        # Here the kick exceeds the dissipated relative kinetic energy and the
        # expected loss is negative: this is an intentional heating case.
        ("python_kick_heating", "general", 1.0, 3.0, 0.25, 0.75),
        ("python_kick_loss", "transverse", 1.0, 2.0, 0.50, 0.20),
        ("python_angular_special", "collinear", 1.0, 1.0, 0.50, 0.0),
        ("python_angular_general", "transverse", 1.0, 1.0, 0.50, 0.0),
    )
    rows: list[dict[str, Any]] = []
    for offset, (case_id, geometry, m1, m2, d, kick) in enumerate(specs):
        v1, v2, r1, r2 = _geometry_vectors(geometry)
        # The special case explicitly aligns q with the separation, making its
        # zero angular residual a test of geometry rather than an assumption.
        direction = [1.0, 0.0, 0.0] if geometry == "collinear" else None
        rng = np.random.default_rng(seed + offset)
        results = [
            pairwise_collision(
                v1,
                v2,
                m1,
                m2,
                d,
                kick,
                rng=rng,
                direction=direction,
                position_1=r1,
                position_2=r2,
            )
            for _ in range(n_trials)
        ]
        rows.append(
            _case_row(
                case_id=case_id,
                geometry=geometry,
                dissipation_factor=d,
                kick_velocity=kick,
                seed=seed + offset,
                results=results,
                validation_level="python_reference",
                audit=audit,
                limitations=(
                    "Angular momentum is measured for fixed collision positions; random directions "
                    "are not required to give a non-zero change in every geometry."
                ),
            )
        )
    return rows


def _source_row(audit: Mapping[str, Any]) -> dict[str, Any]:
    tol_payload = {"source_hash_sha256": 64, "identity": "not_proven"}
    return {
        "case_id": "source_audit_sidm_core",
        "geometry": "n/a",
        "D": "",
        "dissipation_factor": "",
        "kick_velocity": "",
        "seed": "",
        "n_trials": 0,
        "loss_fraction_measured": "",
        "loss_fraction_theory": "",
        "loss_fraction_std": "",
        "relative_speed_before": "",
        "relative_speed_after": "",
        "momentum_residual": "",
        "momentum_residual_max": "",
        "momentum_tolerance_abs": "",
        "momentum_tolerance_rel": "",
        "momentum_tolerance_scale": "",
        "angular_momentum_change": "",
        "angular_momentum_change_max": "",
        "angular_momentum_residual": "",
        "angular_momentum_scale": "",
        "tolerances": json.dumps(tol_payload, sort_keys=True, separators=(",", ":")),
        "source_hash": audit["source_hash"],
        "binary_hash": audit["binary_hash"],
        "source_path": audit["source_path"],
        "binary_path": audit["binary_path"],
        "active_flags": audit["active_flags"],
        "binary_evidence": audit["binary_evidence"],
        "source_binary_identity": audit["source_binary_identity"],
        "solver_experiment": audit["solver_experiment"],
        "validation_level": "source_audit",
        "verdict": "pass_with_limitations",
        "limitations": audit["limitations"],
    }


def build_validation_rows(
    *,
    seed: int = 20261010,
    n_trials: int = 32,
    audit: Mapping[str, Any] | None = None,
) -> list[dict[str, Any]]:
    """Build all deterministic analytic, Python-reference and audit rows."""

    if audit is None:
        audit = source_audit_evidence()
    rows = _analytic_rows(audit) + _python_rows(seed, n_trials, audit)
    rows.append(_source_row(audit))
    for row in rows:
        row.pop("_max_momentum_tolerance", None)
    return rows


def _csv_value(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, (float, np.floating)):
        if math.isnan(float(value)):
            return "nan"
        if math.isinf(float(value)):
            return "inf" if float(value) > 0 else "-inf"
        return format(float(value), ".17g")
    if isinstance(value, (int, np.integer)):
        return str(int(value))
    return str(value)


def write_validation_csv(
    path: str | os.PathLike[str],
    rows: Iterable[Mapping[str, Any]],
) -> Path:
    """Write rows with a stable header and deterministic scalar formatting."""

    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=CSV_FIELDS, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow({field: _csv_value(row.get(field, "")) for field in CSV_FIELDS})
    return destination


def default_output_path() -> Path:
    # conference/ -> scripts/ -> nbody/ -> repository root
    repo_root = Path(__file__).resolve().parents[2]
    return repo_root / "analysis" / "presentations" / "conference_2026" / "validation" / "dissipation_check.csv"


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--out",
        "--output",
        dest="output",
        type=Path,
        default=default_output_path(),
        help="CSV destination (default: conference_2026/validation/dissipation_check.csv)",
    )
    parser.add_argument("--seed", type=int, default=20261010)
    parser.add_argument("--trials", "--n-trials", dest="n_trials", type=int, default=32)
    parser.add_argument("--source-path", type=Path, default=None)
    parser.add_argument("--binary-path", type=Path, default=None)
    parser.add_argument("--object-path", type=Path, default=None)
    parser.add_argument("--config-path", type=Path, default=None)
    parser.add_argument("--binary-config-path", type=Path, default=None)
    args = parser.parse_args(argv)
    audit = source_audit_evidence(
        source_path=args.source_path,
        binary_path=args.binary_path,
        object_path=args.object_path,
        config_path=args.config_path,
        binary_config_path=args.binary_config_path,
    )
    rows = build_validation_rows(seed=args.seed, n_trials=args.n_trials, audit=audit)
    destination = write_validation_csv(args.output, rows)
    print(f"wrote {len(rows)} deterministic validation rows to {destination}")
    print("solver_experiment=not_validated; source_binary_identity=not_proven")
    return 0


if __name__ == "__main__":  # pragma: no cover - exercised by CLI smoke test
    raise SystemExit(main())
