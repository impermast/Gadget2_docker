# M4/M6 processing report

The explicit series index contains 9 mapped rows, with the pilot first. It
uses manifest identities and relative `metrics_csv` and
`series_metadata_json` paths. All mapped artifacts are `series-jz-v2`, have
`parsed_sync_status=ok`, and passed finite Jz/mass checks.

The canonical manifest was generated with:

```text
.venv/bin/python nbody/scripts/conference/manifest.py --roots <nine explicit safe run roots> --out nbody/analysis/presentations/conference_2026/run_manifest.csv --metadata-out nbody/analysis/presentations/conference_2026/run_manifest_metadata.json
```

Exit code: 0. The manifest has 11 rows: 9 safely scanned rows and 2 explicit
deferred rows. The deferred rows are
`dsidm_spin_k08_transition/dsidm_s2p5_D0p75_N1e5_T2` and
`dissipation/test_dissipation_focused_T5/dsidm10_f01_k0_N1e5_T5`; both have
`status=unknown`, `health=pathological`, `metrics_status=missing`, and notes
`deferred:resource/pathology gate; log_scan_not_run`. Their logs were not
scanned. Manifest metadata records `row_count=11`, `deferred_log_scan=true`,
and the nine safe scan roots.

Campaign summary command:

```text
.venv/bin/python nbody/scripts/conference/summarize_campaign.py --manifest nbody/analysis/presentations/conference_2026/run_manifest.csv --series-index nbody/analysis/presentations/conference_2026/m4_series/series_index.csv --out nbody/analysis/presentations/conference_2026/campaign_metrics.csv --metadata-out nbody/analysis/presentations/conference_2026/campaign_metrics_metadata.json
```

Exit code: 0; output has 11 rows: 9 `ok` mapped summaries and 2 `missing`
deferred summaries. Explicit windows are T2 `[1, 2]` and T5 `[2.5, 5]`,
encoded in the series index; no interpolation or fallback path search is
used.

No new simulations, solver runs, or Telegram actions were performed. This M6
task itself did not create a commit or push; prior-stage checkpoint commits
exist. No plan Markdown was edited, and source run directories were not
modified.
