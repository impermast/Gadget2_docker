# Conference figures evidence package

Exact command:

    python3 nbody/scripts/analysis/runners/make_conference_figures.py --package-root nbody/analysis/presentations/conference_2026

Inputs are package-relative `campaign_metrics.csv`, `m4_series/series_index.csv`, the 12 explicit mapped `metrics_series.csv` paths named by that index, and `validation/dissipation_check.csv`. Outputs are `figs/*.png`, `figs/figure_manifest.csv`, and `claims.csv`. The runner uses registry plots through `NbodyPlotter`/`PlotSettings`; it performs no interpolation, fallback discovery, HDF5 or run.log reads, and has no general outdir flag.

Schema/method versions are taken from the committed CSVs (`series-jz-v2` and campaign metadata fields). The package contains 12 mapped rows: three matched k08 T=5 M5 rows are accepted, while `dsidm_s2p5_D0p50_N1e5_T5_k08` is incomplete (30 snapshots, no metrics path). Two legacy rows remain deferred/missing evidence and are not negative evidence. The package remains `science_partial` while claims freeze is pending. T2/T5 late windows and Jz normalization are method claims only.

Visual review record: all four PNG assets were inspected in the final 16-page PDF
for readable axes, labels, legends, units, clipping, series identity/order, and
manifest correspondence; `visual_review_pending=false` is recorded in the
figure manifest. User rehearsal remains a separate pending gate.

## Editable slide export

The evidence-aware `slides.md` source has a deterministic PPTX exporter:

    /usr/bin/python3 nbody/analysis/presentations/conference_2026/talk/export_slides.py \
      --slides nbody/analysis/presentations/conference_2026/talk/slides.md \
      --output /tmp/conference-2026-slides.pptx \
      --asset-root nbody/analysis/presentations/conference_2026/talk

The exporter requires the already available system `python-pptx`, validates the
11 main sections plus five backup sections (`S01`–`S11`, `B01`–`B05`), resolves
the four explicit figure assets, and retains the current status badges. A
structural smoke check passed with 16 slides, four embedded images, valid PPTX
ZIP contents, and no out-of-bounds shapes. This does not replace visual review.

Fresh PDF conversion succeeded with LibreOffice 24.2.7.2 using an isolated
writable profile; `pdfinfo` reports 16 pages and `pdftoppm` rendered all pages.
The final PDF was checked with a full-deck contact sheet and targeted full-size
views of S05, S07, S08 and S11. `export_blocked` is not set; user rehearsal is
still pending.

## M5 post-run lifecycle gate

After (and only after) a run has reached a terminal state, use the bounded
lifecycle gate before generating canonical metrics:

    .venv/bin/python nbody/scripts/conference/post_run_gate.py \
      --run-root nbody/runs/<group>/<run_id> \
      --expected-time 5 \
      --min-snapshots 1

The gate reads only the last 64 KiB of `run.log` and snapshot filenames. Its JSON
fields keep terminal marker, final time, error markers, snapshot count and
used-values provenance independent; `active_or_unknown` is never promoted to a
scientific verdict. It does not read HDF5 datasets or modify a run/package.
