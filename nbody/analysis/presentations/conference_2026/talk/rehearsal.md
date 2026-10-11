# M8 rehearsal and handoff

Статус handoff: `science_partial` · `visual_review_pending` ·
`rehearsal_pending`; предыдущий PDF export verified, свежий export patched exporter pending.

Этот документ описывает передачу и пользовательскую репетицию текущего
evidence-aware каркаса. Он не меняет статусы runs и не объявляет научный вывод
завершённым. Три matched k08 T=5 M5 rows приняты; D0.50 incomplete (30 snapshots,
no metrics path) и не frozen для claims;
deferred runs не следует молча включать в controls. Числа для доклада берутся только после
evidence freeze из versioned CSV/manifest и explicit locator'ов.

## Что передаётся

- [slides.md](slides.md) — editable slide source, 11 основных слайдов + backup.
- [slides.pdf](slides.pdf) — сохранённый 16-страничный экспорт для проверки;
  SHA-256 `22fbec44e277d8c1ffd0c1360e3963809c262e822eba5bea82a3a976b7f4e239`.
- [export_slides.py](export_slides.py) — воспроизводимый системный PPTX-exporter;
  структурная проверка даёт 11 основных + 5 backup и 4 embedded PNG.
- Для M5 lifecycle перед post-run анализом используется
  `nbody/scripts/conference/post_run_gate.py`; он читает только bounded tail
  лога и имена snapshot-файлов и не заменяет научную проверку.
- [speaker_notes.md](speaker_notes.md) — финальные evidence-aware notes и
  переходы; [speaker_notes_draft.md](speaker_notes_draft.md) сохранён как
  исходный черновик.
- [qa.md](qa.md) — финальные методические Q&A; [qa_draft.md](qa_draft.md)
  сохранён как исходный черновик, ответы без locator остаются `pending`.
- [deck_outline.md](deck_outline.md) — claim-by-claim skeleton и ограничения.
- [claims.csv](../claims.csv), [campaign_metrics.csv](../campaign_metrics.csv),
  [run_manifest.csv](../run_manifest.csv),
  [figure_manifest.csv](../figs/figure_manifest.csv) — source ledgers.
- [reproduce.md](../reproduce.md) — воспроизводимость и команды анализа.

## Evidence freeze checklist (до экспорта)

- [ ] Зафиксировать analysis revision и дату freeze; не подменять их текущей
  датой файла.
- [ ] Для каждого claim в `slides.md` сверить `claim_id`, статус и locator с
  `claims.csv`; `pending`/`provisional`/`withdrawn` сохранить явно.
- [ ] Для каждого числа указать run_id, metric key, фактическое окно и путь к
  CSV/metadata; не реконструировать значения из PNG или памяти.
- [ ] Сверить lifecycle (`status`), health/pathology и `metrics_status` как
  независимые поля. Missing/pathological/incomplete не превращать в нули или
  общий `failed`.
- [ ] Проверить, что T=2 и legacy k05 T=5 не выданы за matched k08 T=5 M5;
  deferred/M5 runs остаются отдельными pending/absent entries.
- [ ] Проверить определения `Jz`, `jz`, массы, фиксированной оси z и апертуры
  `r<5 kpc`; `spin_k` не называть измеренным spin.
- [ ] Сверить каждый показанный figure с `figure_manifest.csv`, входным
  revision и разрешённым locator'ом; старые PNG — candidate-only до проверки.
- [ ] Зафиксировать QA-ответы и ограничения в [qa.md](qa.md), сверив их с
  исходным [qa_draft.md](qa_draft.md).

## Export and visual review gate

Текущий export status: старый PDF export verified (16-page PDF; `pdfinfo` и
`pdftoppm` first/last checks passed), но свежий PDF для patched exporter ещё pending.
Полный deck visual freeze и пользовательская
репетиция ещё не проведены: badges остаются `visual_review_pending` и
`rehearsal_pending`; `science_partial` сохраняется.

Для структурного smoke test из корня:

```sh
/usr/bin/python3 nbody/analysis/presentations/conference_2026/talk/export_slides.py \
  --slides nbody/analysis/presentations/conference_2026/talk/slides.md \
  --output /tmp/conference-2026-slides.pptx \
  --asset-root nbody/analysis/presentations/conference_2026/talk
```

Экспортированный PDF уже проверен через `pdfinfo`; первый и последний слайды
отрендерированы через `pdftoppm`. Это не заменяет полный visual freeze.

После freeze пользователь должен проверить в экспортированном PDF/слайдах:

- [ ] все 11 слайдов открываются и имеют правильный порядок;
- [ ] `pending`, `science_partial`, pathology и deferred badges читаемы;
- [ ] ось времени, единицы, legend и locator footers не обрезаны;
- [ ] ни один старый/candidate-only asset не выглядит как frozen evidence;
- [ ] backup/Q&A доступны, но не считаются основными слайдами.

## Пользовательский rehearsal checklist

1. Открыть `slides.md` и `speaker_notes.md` рядом; проговорить вопрос,
   scope и method без добавления чисел, которых нет в locator'ах.
2. Для S07–S10 вслух назвать evidence status и limitation: незавершённый
   M5 не скрывать, а узкий вывод не расширять до «dSIDM не образует диск».
3. Проверить переходы S06→S07 и S08→S09: controls, pathology и aperture
   transfer должны быть различены.
4. Использовать [qa.md](qa.md) для вопросов про D, равновесие IC,
   угловой момент, апертуру и solver validation; неизвестное отвечать как
   `pending`, а не угадывать.
5. Отметить фактическое время, вопросы и места, требующие правки, в отдельном
   rehearsal log. До такой записи статус остаётся `rehearsal_pending`.

## Locators and read-only commands

Из корня репозитория:

```sh
cd /home/kds/sci/gadget2_docker
sed -n '1,220p' nbody/analysis/presentations/conference_2026/talk/slides.md
sed -n '1,220p' nbody/analysis/presentations/conference_2026/talk/speaker_notes.md
sed -n '1,220p' nbody/analysis/presentations/conference_2026/talk/qa.md
rg -n 'M7-C|science_partial|visual_review_pending|rehearsal_pending|export_blocked' \
  nbody/analysis/presentations/conference_2026/talk \
  nbody/analysis/presentations/conference_2026/claims.csv
head -n 2 nbody/analysis/presentations/conference_2026/run_manifest.csv
head -n 2 nbody/analysis/presentations/conference_2026/campaign_metrics.csv
```

Канонические relative locators для текущей проверки: `claims.csv`,
`campaign_metrics.csv`, `run_manifest.csv`, `figs/figure_manifest.csv`,
`m4_series/processing_report.md` и соответствующие
`m4_series/prerun/*/{metrics_series.csv,series_metadata.json}`. Перед freeze
их revision/hash и фактическое покрытие должны быть записаны в claim/figure
ledger; этот handoff не утверждает новые значения.

## Acceptance handoff

Приёмка root: проверить только этот документ и связанные talk-файлы; не менять
`RUN_STATE`, планы или run artifacts. После пользовательской репетиции и
визуального review root может отдельно обновить badges и export status на
основании фактических записей.
