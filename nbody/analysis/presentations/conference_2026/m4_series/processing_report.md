# M4/M6 processing report

The explicit series index contains a 9-row M4 baseline, with the pilot first,
plus the first integrated M5 CDM T5 row (10 mappings total). It
uses manifest identities and relative `metrics_csv` and
`series_metadata_json` paths. All mapped artifacts are `series-jz-v2`, have
`parsed_sync_status=ok`, and passed finite Jz/mass checks.

The canonical manifest was generated with:

```text
.venv/bin/python nbody/scripts/conference/manifest.py --roots <nine explicit M4 safe run roots> --out nbody/analysis/presentations/conference_2026/run_manifest.csv --metadata-out nbody/analysis/presentations/conference_2026/run_manifest_metadata.json
```

The first M5 CDM T5 row is integrated by the post-run staging step after this
M4 baseline command; it is not silently rediscovered by the nine-root command.

Exit code: 0. The manifest now has 12 rows: 10 completed/healthy rows (the 9
M4 baseline plus the first M5 CDM T5 run) and 2 explicit
deferred rows. The deferred rows are
`dsidm_spin_k08_transition/dsidm_s2p5_D0p75_N1e5_T2` and
`dissipation/test_dissipation_focused_T5/dsidm10_f01_k0_N1e5_T5`; both have
`status=unknown`, `health=pathological`, `metrics_status=missing`, and notes
`deferred:resource/pathology gate; log_scan_not_run`. Their logs were not
scanned. Manifest metadata records `row_count=12`, `deferred_log_scan=true`,
and the safe scan roots including the first M5 run.

Campaign summary command:

```text
.venv/bin/python nbody/scripts/conference/summarize_campaign.py --manifest nbody/analysis/presentations/conference_2026/run_manifest.csv --series-index nbody/analysis/presentations/conference_2026/m4_series/series_index.csv --out nbody/analysis/presentations/conference_2026/campaign_metrics.csv --metadata-out nbody/analysis/presentations/conference_2026/campaign_metrics_metadata.json
```

Exit code: 0; output has 12 rows: 10 `ok` mapped summaries and 2 `missing`
deferred summaries. Explicit windows are T2 `[1, 2]` and T5 `[2.5, 5]`,
encoded in the series index; no interpolation or fallback path search is
used.

No new simulations, solver runs, or Telegram actions were performed. This M6
task itself did not create a commit or push; prior-stage checkpoint commits
exist. No plan Markdown was edited, and source run directories were not
modified.
