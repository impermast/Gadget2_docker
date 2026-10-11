# M4 series processing report

## Acceptance scope

Pilot: `cdm_N1e5_T2` (`m4-k08-cdm-t2`), retained as the first entry in
`series_index.csv`.

Eight existing runs were processed successfully, sequentially, with exit code
0. Every output has `analysis_schema_version=series-jz-v2`,
`parsed_sync_status=ok`, and finite `jz_total_r5`, `jz_mass_r5`, and
`jz_per_mass_r5` fields.

| run | artifact | expected rows | checks |
|---|---|---:|---|
| `nbody/runs/dsidm_spin_k08_transition/sidm_s2p5_N1e5_T2` | `m4-k08-sidm-t2` | 21 (T2) | passed |
| `nbody/runs/dsidm_spin_k08_transition/dsidm_s2p5_D0p10_N1e5_T2` | `m4-k08-dsidm-d010-t2` | 21 (T2) | passed |
| `nbody/runs/dsidm_spin_k08_transition/dsidm_s2p5_D0p25_N1e5_T2` | `m4-k08-dsidm-d025-t2` | 21 (T2) | passed |
| `nbody/runs/dsidm_spin_k08_transition/dsidm_s2p5_D0p50_N1e5_T2` | `m4-k08-dsidm-d050-t2` | 21 (T2) | passed |
| `nbody/runs/dissipation/test_dissipation_focused_T5/cdm_N1e5_T5` | `m4-k05-cdm-t5` | 52 (T5) | passed |
| `nbody/runs/dissipation/test_dissipation_focused_T5/sidm10_N1e5_T5` | `m4-k05-sidm10-t5` | 52 (T5) | passed |
| `nbody/runs/dissipation/test_dissipation_focused_T5/dsidm5_f005_k0_N1e5_T5` | `m4-k05-dsidm5-d005-t5` | 52 (T5) | passed |
| `nbody/runs/dissipation/test_dissipation_focused_T5/dsidm10_f005_k0_N1e5_T5` | `m4-k05-dsidm10-d005-t5` | 52 (T5) | passed |

## Deferred runs

The following runs were not launched, by the resource/pathology gate:

- `nbody/runs/dsidm_spin_k08_transition/dsidm_s2p5_D0p75_N1e5_T2`
- `nbody/runs/dissipation/test_dissipation_focused_T5/dsidm10_f01_k0_N1e5_T5`

## Scope exclusions

No new simulations, solver runs, Telegram actions, commits, or pushes were
performed. Planned Markdown files were not edited. This report was added
without rerunning the analysis runner and without modifying existing outputs,
`series_index.csv`, or source run directories.
