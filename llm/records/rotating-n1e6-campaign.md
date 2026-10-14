# Rotating N=1e6, f_diss=0.5 campaign — verified T=1 status

Status: scoped historical campaign record; audited 2026-10-13/14. This is not permission to rerun, archive, or delete outputs. Canonical run outputs remain under `/nbody/runs/`; series analyses under `/nbody/analysis/prerun/` and `core/`. Parameters and coverage must be rechecked before reuse.

## Matched T=1 outcomes

Input IC: `/nbody/ics/dwarf_rot_N1e6_lambda0035/dwarf_rot_N1e6_lambda0035.hdf5`. Nominal literature parameter `f_diss=0.5` maps at `DM_KickPerCollision=0` to GIZMO `DM_DissipationFactor D_code=1-sqrt(1-f_diss)=0.2928932188`.

- CDM `20261013_cdm_rotN1e6_fdiss0p5_sigma0_T1_mpi10`: T=1, 101/101 snapshots.
- SIDM `20261013_sidm_s1_fdiss0p5_rotN1e6_T1_mpi10`: σ/m=1, T=1, 101/101, no flags; `NInteractions=135610`, 7.22% particles interacted. A retry gate falsely rejected this run because rounded `used-values` was compared with absolute tolerance 1e-8; canonical JSON stored D=0.2928932188 and the manually checked gate passed at 1e-6. Future validation must account for representation precision and inspect canonical used parameters.
- SIDM `20261013_sidm_s2_fdiss0p5_rotN1e6_T1_mpi10`: σ/m=2, stopped at t=0.5659/1, 57/101. Terminal error: `No domain decomposition that stays within memory bounds is possible.` At t≈0.55→0.56, NInteractions 213,730→2,147,508, maximum collisions/particle 35→2,472, minimum systemstep fell to 2.38e-7 (log included ≈4e-16); density within 1 kpc rose ≈56%, within 5 kpc ≈3%. Morphology remained spherical (`c/a≈0.998`, `z/R≈0.707`, `|vrot|/sigma≈0.339`). This is consistent with central contraction/timestep pathology, but the central-resolution limit prevents claiming it is physical. Wrapper rc=0, `run.state=COMPLETED`, and tail health are not proof of T=1 completion.

SIDM-2 runs/analyses: `nbody/analysis/prerun/20261013_sidm_s2_fdiss0p5_rotN1e6_T1_mpi10/` and `nbody/analysis/core/20261013_sidm_s2_fdiss0p5_rotN1e6_T1_mpi10/`. Logs under `/nbody/runs/20261013_rotN1e6_fdiss0p5_sigma1_2_retry_batch.log` and `/nbody/runs/20261013_rotN1e6_fdiss0p5_sigma2_retry.log`.

## Interpretation and safety

A T=1 initial-state comparison is not evidence about long-term disk formation. Distinguish terminally incomplete SIDM-2 from completed CDM/SIDM-1; do not pool as three complete results. No rerun, cleanup, or data deletion is implied. Historical archive work (six other pathologies, four uncertain legacy cases) is documented in `/nbody/runs/pathological/README.md`; verify actual contents before action.

## Evidence

Original audit: `llm/records/dissipation-parameter-audit.md`; source manifests/logs and run outputs above. Values summarized from read-only source audit on 2026-10-14; revalidate locators and hashes before consequential claims.
