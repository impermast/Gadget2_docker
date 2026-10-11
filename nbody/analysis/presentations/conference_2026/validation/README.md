# Dissipation validation

This artifact is an independent pairwise reference check for the dSIDM
interaction rule used by the campaign. It is not a run of GIZMO and it does
not compare the one-collision result with a full halo energy budget.

## Definition and reference formula

For two particles with masses `m1`, `m2` and relative velocity
`v_rel = v1 - v2`, the relative kinetic energy in the pair centre-of-mass
frame is

```text
E_rel = 1/2 * (m1*m2/(m1+m2)) * |v_rel|^2.
```

The source implementation first computes

```text
u = max((1 - D) * |v_rel|, 0)
u = sqrt(u^2 + kick_velocity^2)   if kick_velocity > 0
```

and draws an isotropic unit vector `n`. The caller applies the two
mass-weighted kicks so that `v_rel_after = -u*n`, while the pair COM momentum
is unchanged. Therefore the positive loss fraction used in this CSV is

```text
loss_fraction = (E_rel_before - E_rel_after) / E_rel_before
              = 1 - |v_rel_after|^2 / |v_rel_before|^2.
```

For non-zero initial relative speed, zero kick and `0 <= D <= 1` this reduces
to `2*D - D^2`. With a non-zero kick the full expression is used:
`2*D - D^2 - (kick_velocity/|v_rel|)^2` (within the same D range). A negative
loss is heating, not a failed sign convention. At zero initial relative speed
the fractional ratio is undefined and the reference function returns `nan`.

The angular-momentum columns report the measured change for fixed collision
positions. A collinear separation/impulse is a valid zero-residual special
geometry; random-direction cases are not required to be non-zero one by one.

## CSV schema and deterministic generation

`dissipation_check.csv` has 15 deterministic rows generated with
`seed=20261010`, `n_trials=32` by:

```bash
docker exec gadget-gizmo python3 \
  /nbody/scripts/conference/dissipation_check.py \
  --out /nbody/analysis/presentations/conference_2026/validation/dissipation_check.csv \
  --seed 20261010 --trials 32
```

The rows are labelled `validation_level=analytic`, `python_reference`, or
`source_audit`. The Python reference rows include equal/unequal masses,
`D=0`/`D=1`, representative zero-kick values, a positive-kick loss case, a
positive-kick heating case, and special/general angular-momentum geometries.

Momentum acceptance is scale-aware: absolute tolerance `1e-13` plus relative
tolerance `1e-12` times a velocity/mass scale. Energy comparison uses
absolute and relative tolerances `2e-13`.

The command is a pure Python reference CLI. It does not call `docker exec`
itself, start `GIZMO`, launch MPI, read snapshots, or run a solver experiment.
By default it uses the recorded audit hashes verbatim, so host and container
generation are byte-for-byte deterministic. Explicit `--source-path`/
`--binary-path` (and related config options) opt into hashing files that are
actually mounted; this still does not assert source-binary identity.

## Source audit evidence (read-only)

On 2026-10-10 the following commands were run against the already-running
`gadget-gizmo` container; no build or solver command was run:

```bash
docker exec gadget-gizmo bash -lc \
  'sha256sum /opt/gizmo-public/sidm/sidm_core.c \
             /opt/gizmo-public/sidm/sidm_core.o \
             /opt/gizmo-public/GIZMO \
             /opt/gizmo-public/GIZMO_config.h \
             /opt/gizmo-public/Config.sh \
             /opt/gizmo-public/Makefile.systype'
docker exec gadget-gizmo bash -lc \
  'sed -n "1,260p" /opt/gizmo-public/sidm/sidm_core.c'
docker exec gadget-gizmo bash -lc \
  'sed -n "1,220p" /opt/gizmo-public/sidm/sidm_core_flux_computation.h'
docker exec gadget-gizmo bash -lc \
  'nm -C /opt/gizmo-public/GIZMO | grep calculate_interact_kick'
```

Recorded hashes:

| item | SHA-256 |
|---|---|
| `/opt/gizmo-public/sidm/sidm_core.c` | `5d25f30be04b008580002c10cdcd53000d52f35bf5bd38e2c50c3030c22c3c7e` |
| `/opt/gizmo-public/sidm/sidm_core.o` | `389aea783f27379e28c8087a24e6fcde5e287f94722f00f3b3b6a74f3593d305` |
| `/opt/gizmo-public/GIZMO` | `bb3927203b3ea9202de9da7605de292ccfbdf1325ea702d279bb30e0a369e2db` |
| `/opt/gizmo-public/GIZMO_config.h` | `46ee590b16e91b74c910000c9d8cfb82037e629acc25043499a5318656e36e31` |
| `/opt/gizmo-public/Config.sh` | `7ecccf5ddf5cb69a0dc47a9653caa146fa6297b855dc5be4d13ebcc4c66cdfc8` |
| `/opt/gizmo-public/Makefile.systype` | `03a29a20f1515633c092d0864283e521f63dc2f12e296d4147bc5f77e877e5b0` |

The source contains `calculate_interact_kick` with the `D` rescaling, optional
quadrature kick, isotropic direction, and `0.5*(dV + dVmag*n)` expression.
The caller in `sidm_core_flux_computation.h` uses
`m_si=0.5*(local.Mass+P[j].Mass)` and applies opposite updates weighted by the
other particle's mass. `Config.sh`/`GIZMO_config.h` show `DM_SIDM=8`; no
`GRAIN_COLLISIONS` flag is active in those configuration files. The ELF binary
contains the SIDM symbols and reports GCC 9.4.0, with MPI/HDF5/GSL links.

These observations establish source and active-configuration evidence, but
they do **not** prove source-binary identity: there is no retained build log or
link map tying this exact C file to the executable. Accordingly every row
records `source_binary_identity=not_proven`, and the solver status is honestly
`solver_experiment=not_validated`. A Python reference pass is not a validation
of the executing GIZMO binary.
