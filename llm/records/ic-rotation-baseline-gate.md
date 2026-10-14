# Read-only baseline gate for rotating-halo IC

**Why/when to use:** reproduce the historical 1e5 diagnostic only; its thresholds/status do not automatically validate the separate N=1e6 IC or authorize a run.

**Status:** diagnostic only; no IC was written or changed, and no simulation was started.

## Input and method

- Input: `nbody/ics/dwarf_rot_N1e5/dwarf_rot_N1e5.hdf5`, `PartType3`, 100,000 particles.
- Input SHA-256: `2b706d42e760e47fb465c2e4a696ab6835162074963b4d07e41331ee8b1a2371`.
- Units: kpc, km/s, `1e10 Msun`; `G=43007.1` in these units.
- The center was found using the script's shrinking-sphere estimator; velocities were measured relative to the mass-weighted bulk velocity.
- Provisional SO-200 reference: `H0=0.1 km/s/kpc`, giving
  `mean_density/critical_density = 2 G M(<r)/(H0^2 r^3) = 200`.
  This is an aperture convention for the diagnostic, not a cosmological evolution setting.

## Baseline measurements

| Quantity | Measured |
|---|---:|
| Total particle mass | `0.627633881` code mass = `6.27634e9 Msun` |
| Measured `R200` (provisional `H0=0.1`) | `27.540864 kpc` |
| `M200` inside measured radius | `0.485725860` code mass = `4.85726e9 Msun` |
| `V200 = sqrt(G M200/R200)` | `27.540823 km/s` |
| Initial Bullock `lambda'_200` | `0.000837451` |
| Mass outside measured `R200` | `22.61%` of total IC mass |

Basic data/shape checks: all coordinates and velocities are finite; all 100,000
particle IDs are unique; particle masses are exactly constant at
`6.27633881e-6` code mass. The shrinking-sphere center is
`(0.01490, -0.01504, 0.00116) kpc`; mass-weighted bulk velocity is
`(0.12668, 0.03900, -0.09554) km/s`. Inside measured R200, the simple
mass-weighted position second-moment axes have `b/a=0.9963`, `c/a=0.9929`;
Cartesian velocity component dispersions are `(22.08, 22.12, 22.18) km/s`.
Across radial shells, cylindrical/radial/vertical dispersions are comparable,
and shell mean azimuthal speeds are small compared with the dispersions.
These checks support a nearly spherical, nearly nonrotating snapshot, but do
not establish dynamical equilibrium or collisionless stability.

The GalIC setup is labelled `V200=30 km/s`, conventionally implying `R200=30 kpc` for `H0=0.1`. The measured SO-200 crossing is instead `27.54 kpc`; the enclosed mass there is about 22.6% below `V200^2 R200/G` for the nominal 30/30 values. This model-versus-realized-profile discrepancy is **unresolved**. Do not silently treat nominal `30 kpc` and measured SO-200 as interchangeable. Before writing a transformed IC, document whether to use measured SO-200 at the adopted H0 or the nominal GalIC aperture; only the former is the conventional measured `lambda'_200` under the provisional reference density.

The measured initial spin is also much smaller than the GalIC `k=0.5` label might suggest. This confirms that `k` must not be used as the physical spin target; it does not, on its own, establish a GalIC defect.

## In-memory feasibility dry-run (not an IC)

The updated `nbody/scripts/halo_spin_bias.py` was applied to arrays in memory only, using seed `12345`, target `lambda'_200=0.035`, and the provisional measured `R200=27.540864 kpc`:

- Final measured `lambda'_200`: `0.03495565`; target-vector error: `0.000478` in dimensionless lambda units.
- `19,355` of `49,722` retrograde candidates were selected across the whole halo; `15,080` were currently inside `R200` and `4,275` outside.
- Candidate selection is a seeded random thinning of all retrograde particles, not a cut on instantaneous radius. Only `v_phi` is reversed. This avoids creating a phase-dependent boundary at `R200`; the aperture is used only for target measurement.
- Mass-weighted bulk-velocity change in this finite realization: `(-0.0440, -0.0212, 0.0000) km/s`.
- Maximum squared-speed change among flipped particles, in the original bulk frame: `6.4e-12 (km/s)^2` (roundoff).

The resulting profile is not spatially uniform: approximate mass-weighted `v_phi` values in radial shells are `8.20, 8.79, 8.30, 6.46, 5.48, 4.38 km/s` for `r=[0,1), [1,2), [2,5), [5,10), [10,20), [20,R200) kpc`. These are diagnostics from a hypothetical in-memory operation, not measured properties of a saved IC.

## Gate disposition (historical N=1e5 diagnostic)

This report records the first feasibility dry-run on the N=1e5 IC; its in-memory
numbers are **not** the final N=1e6 IC values. The later selected source and
prepared output are documented in `llm/records/ic-rotation-recommendation.md` and
`nbody/ics/dwarf_rot_N1e6_lambda0035/spin_bias_manifest.json`.

- This earlier source's geometric checks and spin feasibility: **provisional pass**.
- The user later confirmed N=1e6 and requested preparation of an IC. The new
  derivative was written separately from the existing NFW source; no source or
  simulation data was overwritten.
- The N=1e6 output uses measured SO-200 at provisional `H0=0.1`, while preserving
  nominal GalIC `CC=15`, `V200=30`, and the exact original particle positions and
  masses. Nominal-versus-measured radii remain distinct provenance values.
- Collisionless equilibrium/stability is **not established**; the new IC has not
  been run through GIZMO. A separate, explicitly approved stability run is still
  required before dSIDM production runs.
