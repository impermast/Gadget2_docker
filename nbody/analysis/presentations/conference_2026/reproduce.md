# Conference figures evidence package

Exact command:

    python3 nbody/scripts/analysis/runners/make_conference_figures.py --package-root nbody/analysis/presentations/conference_2026

Inputs are package-relative `campaign_metrics.csv`, `m4_series/series_index.csv`, the 10 explicit `metrics_series.csv` paths named by that index, and `validation/dissipation_check.csv`. Outputs are `figs/*.png`, `figs/figure_manifest.csv`, and `claims.csv`. The runner uses registry plots through `NbodyPlotter`/`PlotSettings`; it performs no interpolation, fallback discovery, HDF5 or run.log reads, and has no general outdir flag.

Schema/method versions are taken from the committed CSVs (`series-jz-v2` and campaign metadata fields). The package contains 10 mapped series (9 M4 baseline plus the first integrated M5 CDM row); 2 deferred runs remain a limitation and are not negative evidence. The package remains `science_partial` while the remaining M5 runs and claims freeze are pending. T2/T5 late windows and Jz normalization are method claims only.

Visual review checklist: inspect every PNG for non-empty readable axes, labels, legends, units, clipping, consistent series identity/order, and correspondence to its manifest source locator. `visual_review_pending=true` until independently reviewed.
