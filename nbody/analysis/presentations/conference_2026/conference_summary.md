# Conference 2026 evidence-aware summary

Статус пакета: `science_partial`. Это краткий handoff M6/M7, а не заявление
`science_complete` и не новый analysis result. Три matched k08 T=5 M5 rows
приняты; `dsidm_s2p5_D0p50_N1e5_T5_k08` incomplete (30 snapshots, no metrics
path), claims ещё не frozen; два legacy rows остаются missing evidence и не
трактуются как отрицательный физический результат.

## Область и текущая evidence base

Пакет рассматривает ограниченную серию изолированных вращающихся NFW-гало с
сравнением CDM/SIDM/dSIDM. Определения, окна и ограничения берутся из
[claims.csv](claims.csv), [run_manifest.csv](run_manifest.csv),
[campaign_metrics.csv](campaign_metrics.csv) и
[reproduce.md](reproduce.md). В текущем manifest указаны 12 mapped rows: три
matched rows приняты, D0.50 incomplete; два legacy rows deferred. Deferred
классифицируются как отсутствие evidence, а не как
failures. Их `status`, `health` и `metrics_status` нельзя сворачивать в один
вердикт.

Методические окна — T=2 `[1,2]` и T=5 `[2.5,5]`; это определения анализа, не
новые физические claims. `Jz`, `jz`, масса, фиксированная ось z и апертура
`r<5 kpc` должны читаться по схеме и metadata конкретного ряда. `spin_k` не
является измеренным spin, а апертурный `Jz` не заменяет глобальную проверку
сохранения углового момента.

## Claims and interpretation boundary

- Supported claims ограничены scope, методикой, provenance и правилами
  классификации из `claims.csv`.
- Результатные формулировки остаются `pending`/`provisional`, пока claim не
  связан с run_id, metric key, фактическим окном, analysis revision и явным
  locator'ом в CSV/metadata.
- Патология, неполное покрытие, перенос массы через апертуру и отсутствие
  seed/resolution checks ограничивают интерпретацию; они не должны превращаться
  в универсальное утверждение «dSIDM не образует диск».
- Старые PNG являются candidate-only до независимой проверки через
  [figure_manifest.csv](figs/figure_manifest.csv); наличие файла не означает
  frozen evidence.

## Handoff state

Editable talk source и Q&A находятся в [talk/slides.md](talk/slides.md),
[talk/speaker_notes.md](talk/speaker_notes.md), [talk/qa.md](talk/qa.md) и
[talk/rehearsal.md](talk/rehearsal.md); исходные draft-файлы сохранены рядом.
Структурный PPTX-exporter сохранён в
[talk/export_slides.py](talk/export_slides.py); 16-страничный PDF экспортирован
и проверен через `pdfinfo` и `pdftoppm` (первый/последний слайды). До evidence
freeze сохраняются `visual_review_pending` и `rehearsal_pending`; полный deck
visual freeze и пользовательская репетиция ещё pending. Следующий
безопасный шаг — сверить claims/figures/manifest одной analysis revision,
провести visual review и пользовательскую репетицию; запусков и RUN_STATE этот
summary не изменяет.

## Source and reproducibility locators

- Claims/status ledger: [claims.csv](claims.csv)
- Run lifecycle/provenance: [run_manifest.csv](run_manifest.csv),
  [run_manifest_metadata.json](run_manifest_metadata.json)
- Metrics and series index: [campaign_metrics.csv](campaign_metrics.csv),
  [m4_series/series_index.csv](m4_series/series_index.csv)
- Processing caveats: [m4_series/processing_report.md](m4_series/processing_report.md)
- Reproduction contract: [reproduce.md](reproduce.md)
- Validation scope: [validation/README.md](validation/README.md)

Числа и verdicts в этом summary намеренно не дублируются из metrics: при
подготовке финальных слайдов их нужно брать из versioned source с locator'ом,
а не копировать из этого handoff.
