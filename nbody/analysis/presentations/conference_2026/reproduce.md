# Conference figures evidence package

Exact command:

    python3 nbody/scripts/analysis/runners/make_conference_figures.py --package-root nbody/analysis/presentations/conference_2026

Inputs are package-relative `campaign_metrics.csv`, `m4_series/series_index.csv`, the 10 explicit `metrics_series.csv` paths named by that index, and `validation/dissipation_check.csv`. Outputs are `figs/*.png`, `figs/figure_manifest.csv`, and `claims.csv`. The runner uses registry plots through `NbodyPlotter`/`PlotSettings`; it performs no interpolation, fallback discovery, HDF5 or run.log reads, and has no general outdir flag.

Schema/method versions are taken from the committed CSVs (`series-jz-v2` and campaign metadata fields). The package contains 10 mapped series (9 M4 baseline plus the first integrated M5 CDM row); 2 deferred runs remain a limitation and are not negative evidence. The package remains `science_partial` while the remaining M5 runs and claims freeze are pending. T2/T5 late windows and Jz normalization are method claims only.

Visual review checklist: inspect every PNG for non-empty readable axes, labels, legends, units, clipping, consistent series identity/order, and correspondence to its manifest source locator. `visual_review_pending=true` until independently reviewed.

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

PDF conversion is still blocked in the current headless environment: LibreOffice
24.2.7.2 exits non-zero before writing a PDF even for a minimal valid PPTX, with
the observed `javaldx`/read-only dconf runtime failure. Do not change
`export_blocked` or `visual_review_pending` until a writable user LibreOffice
runtime produces a PDF that can be checked with `pdfinfo` and `pdftoppm`.

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
