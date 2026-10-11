# Q&A M7 — evidence-aware handoff

Статус пакета: `science_partial` · `visual_review_pending` ·
`rehearsal_pending` · `export_blocked`. Первый CDM k08 T5 run прошёл
terminal/post-run gate и интегрирован; остальные M5 runs pending, claims ещё не
frozen. Deferred runs — missing evidence, не отрицательный результат. Ответы ниже не объявляют
`science_complete`.

## Вопросы и ответы

1. **Как нормирован D?**
   `D` — параметр диссипативного изменения скорости, не измеренная доля потери
   энергии гало. При нулевом kick `2D-D^2` относится к относительной энергии в
   СЦМ. Solver validation указывается отдельно; для числа нужен locator.

2. **Находится ли IC в равновесии?**
   Это отдельная проверка provenance, ранней релаксации и controls, не следствие
   `spin_k`. Без неё это ограничение, а не подтверждение равновесия.

3. **Сохраняется ли угловой момент?**
   `Jz` считается после общего центра и bulk velocity с фиксированной осью z.
   Изменение внутри `r<5 kpc` может быть aperture transfer; апертурный `Jz` не
   заменяет глобальный контроль.

4. **Почему выбрана эта апертура?**
   `r<5 kpc` — заранее заданный методический frame для сопоставимых метрик.
   Покрытие, массу и вход/выход частиц нужно показывать; sensitivity к другой
   апертуре остаётся ограничением.

5. **Какие controls matched?**
   k08 T=2 и legacy k05 T=5 — разные контексты; legacy k05 не заменяет matched
   k08 T=5. Первый CDM run прошёл terminal/post-run gate и интегрирован; остальные
   M5 runs pending, поэтому статус `science_partial` сохраняется.

6. **Достаточны ли N и softening?**
   Это ограниченная серия; фактически применённые softening и timestep берутся
   из manifest, а не восстанавливаются по имени run. Без seed/resolution study
   нельзя заявлять статистическую или численную сходимость.

7. **Проверена ли сходимость?**
   Completed не означает converged. Нужны явные resolution/softening/seed
   controls; при их отсутствии ответ — limitation.

8. **Может ли структура сформироваться позднее?**
   Да, если окно и coverage её не исключают. Отсутствующий late-time участок
   нельзя интерполировать; ранний результат не превращается в общий запрет.

9. **Что означает отрицательный результат?**
   Только отсутствие кандидата по объявленным критериям в исследованном окне и
   при данных controls, если это подтверждено M6. `insufficient_coverage` и
   pathology — отдельные исходы; универсальный запрет не заявляется.

10. **Каковы ограничения solver?**
    Analytic/Python reference и source audit проверяют свои уровни, но не
    доказывают корректность исполняемого GIZMO. Solver-level evidence остаётся
    `not_validated_in_solver` без отдельной проверки.

11. **Почему `spin_k` нельзя читать как момент?**
    Это nominal parameter генерации IC. Измеренные `Jz`, `jz`, знак, frame и
    масса должны быть отдельными полями; `_k0` означает нулевой kick, не
    отсутствие вращения.

12. **Что делать, если run завершён, но метрики плохи?**
    Разделять lifecycle, health и `metrics_status`: `completed` может сочетаться
    с `pathological` или `invalid`. Missing/NaN нельзя заменять нулём или
    скрывать в итоговом verdict.

## Если вопрос требует числа или нового verdict

Ответ: «Число берётся только из versioned M6
`campaign_metrics.csv`/metadata с `run_id`, metric key, окном, analysis
revision и locator». При отсутствии такой записи ответ остаётся `pending`;
старые figures не являются новым evidence.

## Locators

- Claims/status: [claims.csv](../claims.csv)
- Metrics and windows: [campaign_metrics.csv](../campaign_metrics.csv)
- Lifecycle/provenance/deferred: [run_manifest.csv](../run_manifest.csv) и
  `run_manifest_metadata.json`
- Figures: [figure_manifest.csv](../figs/figure_manifest.csv)
- Reproduction contract: [reproduce.md](../reproduce.md)
- Validation scope: [validation/README.md](../validation/README.md)
- Processing caveats: [processing_report.md](../m4_series/processing_report.md)

Actual user rehearsal и visual review ещё не проведены; до их фактической
фиксации статусы `rehearsal_pending`, `visual_review_pending` и
`export_blocked` сохраняются.
