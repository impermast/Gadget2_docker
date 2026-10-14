# dSIDM dissipation-parameter audit

**Why/when to use:** translate literature `f_diss` to audited local GIZMO `D_code` and interpret the 22-run inventory without overstating thresholds. Scope is the documented solver revision and runs in the tables; revalidate code/locators before new use.

Date: 2026-10-13. Read-only inventory of `/nbody/runs/**/.gizmo_run.param`.
Included only nonzero `DM_DissipationFactor` runs with evidence the solver was
actually entered (`.gizmo_run.param-usedvalues` or at least one output snapshot).
This does not assert that the run reached its requested `TimeMax`; wrapper state
and solver completion are not equivalent.

## Convention conversion

The local GIZMO implementation in `/opt/gizmo-public/sidm/sidm_core.c` uses
`v_rel' = (1 - D_code) v_rel` (with a random outgoing direction). With
`DM_KickPerCollision=0`, the pair-relative kinetic-energy loss fraction is
therefore

`f_diss = 1 - (1 - D_code)^2 = 2 D_code - D_code^2`.

The values below are the literature-equivalent `f_diss` implied by the code
value actually written into each run's `.gizmo_run.param`; they were not the
input values used when launching. The `dsidm10_f05_k15...` run has a nonzero
kick (15 code velocity units), so its net energy change cannot be represented
by `f_diss` from `D_code` alone; its tabulated `f_diss` is only the D-only
component.

## Inventory (22 launched runs with D > 0)

| `D_code` actually used | Equivalent `f_diss` if kick=0 | Runs | `sigma/m` values | Run paths relative to `nbody/runs/` |
|---:|---:|---:|---|---|
| 0.05 | 0.0975 | 6 | 1, 5, 10 | `dissipation/test_dissipation/dsidm5_f005_k0_N1e5_T2_np4`; `dissipation/test_dissipation_focused_T5/dsidm10_f005_k0_N1e5_T5`; `dissipation/test_dissipation_focused_T5/dsidm5_f005_k0_N1e5_T5`; `dissipation/test_dissipation_grid_sigma1/dsidm10_f005_k0_N1e5_T2`; `dissipation/test_dissipation_grid_sigma1/dsidm1_f005_k0_N1e5_T2`; `dissipation/test_dissipation_grid_sigma1/dsidm5_f005_k0_N1e5_T2` |
| 0.10 | 0.1900 | 4 | 1, 2.5, 10 | `dissipation/test_dissipation_focused_T5/dsidm10_f01_k0_N1e5_T5`; `dissipation/test_dissipation_grid_sigma1/dsidm10_f01_k0_N1e5_T2`; `dissipation/test_dissipation_grid_sigma1/dsidm1_f01_k0_N1e5_T2`; `dsidm_spin_k08_transition/dsidm_s2p5_D0p10_N1e5_T2` |
| 0.20 | 0.3600 | 1 | 1 | `dissipation/test_dissipation_grid_sigma1/dsidm1_f02_k0_N1e5_T2` |
| 0.25 | 0.4375 | 2 | 2.5 | `dsidm_spin_k08_transition/dsidm_s2p5_D0p25_N1e5_T2`; `dsidm_spin_k08_transition/dsidm_s2p5_D0p25_N1e5_T5_k08` |
| 0.50 | 0.7500* | 8 | 2.5, 10 | `dissipation/test_dissipation/dsidm10_f05_k15_N1e5_T2` (kick=15; see caveat); `dsidm_spin_k08_transition/dsidm_s2p5_D0p50_N1e5_T2`; `dsidm_spin_k08_transition/dsidm_s2p5_D0p50_N1e5_T3p5_k08_dt001`; `dsidm_spin_k08_transition/dsidm_s2p5_D0p50_N1e5_T3p5_k08_dt001_np10`; `dsidm_spin_k08_transition/dsidm_s2p5_D0p50_N1e5_T5_k08`; `dsidm_spin_k08_transition/dsidm_s2p5_D0p50_N1e5_T5_k08_retry1`; `dsidm_spin_k08_transition/dsidm_s2p5_D0p50_N1e5_T5_k08_retry2`; `20261012_dsidm_s2p5_D0p5_rotN1e6_T1_mpi10` |
| 0.75 | 0.9375 | 1 | 2.5 | `dsidm_spin_k08_transition/dsidm_s2p5_D0p75_N1e5_T2` |

`*` For `dsidm10_f05_k15_N1e5_T2`, 0.75 is the energy-loss fraction from
`D_code=0.5` before the separate positive kick. Net energy per collision
varies with incoming relative velocity and the kick, so no single `f_diss`
conversion applies to that run.

## Simulation outcomes

Outcomes were rechecked with the canonical `check_run.py` JSON report and
existing prerun partial-series diagnostics. “Reached target, no numerical
pathology detected” does not assert a dark disk or otherwise validate the
physical model. A run with a pathology flag remains classified as pathological
even if it reached `TimeMax` or the wrapper says `COMPLETED`.

| `D_code` | Equivalent `f_diss`* | Total | Reached `TimeMax`, no numerical pathology detected | Reached `TimeMax`, pathological | Incomplete, pathological | Incomplete/failed, pathology not confirmed |
|---:|---:|---:|---:|---:|---:|---:|
| 0.05 | 0.0975 | 6 | 6 | 0 | 0 | 0 |
| 0.10 | 0.1900 | 4 | 3 | 0 | 0 | 1 |
| 0.20 | 0.3600 | 1 | 1 | 0 | 0 | 0 |
| 0.25 | 0.4375 | 2 | 2 | 0 | 0 | 0 |
| 0.50 | 0.7500 | 8 | 1 | 1 | 5 | 1 |
| 0.75 | 0.9375 | 1 | 0 | 1 | 0 | 0 |
| **Total** | — | **22** | **13** | **2** | **5** | **2** |

Issue details:

- Pathological and incomplete (5): `dissipation/test_dissipation/dsidm10_f05_k15_N1e5_T2` (also kick=15); `dsidm_spin_k08_transition/dsidm_s2p5_D0p50_N1e5_T3p5_k08_dt001_np10`; `dsidm_spin_k08_transition/dsidm_s2p5_D0p50_N1e5_T5_k08`; `dsidm_spin_k08_transition/dsidm_s2p5_D0p50_N1e5_T5_k08_retry1`; `20261012_dsidm_s2p5_D0p5_rotN1e6_T1_mpi10`.
- Pathological despite reaching `TimeMax` (2): `dsidm_spin_k08_transition/dsidm_s2p5_D0p50_N1e5_T5_k08_retry2` and `dsidm_spin_k08_transition/dsidm_s2p5_D0p75_N1e5_T2`; their existing series diagnostics report `no-disk-before-pathology`.
- Incomplete/failed without confirmed pathology (2): `dissipation/test_dissipation_focused_T5/dsidm10_f01_k0_N1e5_T5` (48/51 snapshots; reason not established) and `dsidm_spin_k08_transition/dsidm_s2p5_D0p50_N1e5_T3p5_k08_dt001` (25/36; `run.state` says `FAILED`, while generated `experiment.md` incorrectly says completed normally).
- The D=0.5 T2 run `dsidm_spin_k08_transition/dsidm_s2p5_D0p50_N1e5_T2` reached its requested time and had no numerical-pathology flag; its morphology analysis was classified as ambiguous, not as a numerical failure.

## Interpretation limit

The inventory is suggestive, not a calibrated threshold study. All 13 runs at
`f_diss <= 0.4375` include 12 that reached target without numerical-pathology
flags and one incomplete `f_diss=0.19` run with unknown cause. At
`f_diss=0.75`, outcomes vary with duration and setup: one T=2 run reached target
without a numerical-pathology flag, while other T=3–5 and N=1e6 runs were
pathological or incomplete. The `f_diss=0.9375` run reached T=2 but was
pathology-flagged. There are no runs at `f_diss=0.5`; sampled values leave a
gap from 0.4375 to 0.75, and sigma, IC, N, run duration, and one extra kick
are not fully matched. Thus this table does not establish a universal
`f_diss < 0.5` stability bound.

## Proximity to a dark-disk candidate for f_diss < 0.4

The existing k=0.8 campaign uses preliminary candidate gates `c/a<0.75`,
`z_rms/R_rms<0.55`, and `|vrot|/sigma>0.15`, plus a coherent rotating
`R-vphi` branch. The closest matched long run just above this interval,
`dsidm_s2p5_D0p25_N1e5_T5_k08` (`f_diss=0.4375`, sigma/m=2.5), reaches T=5
without timestep pathology, but has `c/a_min=0.815` (`final=0.935`),
`(z_rms/R_rms)_min=0.590` (`final=0.671`), and final
`|vrot|/sigma=0.176`. Only the rotation-support gate is marginally crossed;
shape/thickness remain far from disk gates. The high initial rotation ratio
(0.536) decays and is not evidence of a newly formed disk.

For `f_diss=0.36` (`D_code=0.20`, sigma/m=1, T=2), canonical series metrics
are `c/a_min=0.836` (`final=0.949`), thickness min/final `0.603/0.676`, and
`|vrot|/sigma` initial/final `0.340/0.117`; this also fails the combined disk
gates. Its output is `nbody/analysis/prerun/dsidm1_f02_k0_N1e5_T2/`.
The longer matched run above is analyzed at
`nbody/analysis/prerun/dsidm_s2p5_D0p25_N1e5_T5_k08/`. Existing low-D visual
summaries at sigma/m=5–10 likewise report disk_score=0/no-clear-disk. Thus no
existing run with f_diss<0.4 is a convincing near-disk candidate; f=0.4375
shows at most marginal rotation support without disk-like shape.

`*` Except the kick=15 run, whose net energy change has no single D-only
conversion. No `DM_DissipationFactor=1` launched run was found. The legacy
GIZMO source/build was not modified.
