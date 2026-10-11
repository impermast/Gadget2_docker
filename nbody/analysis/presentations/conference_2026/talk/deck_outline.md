# Черновой каркас доклада M7: dSIDM и вращающаяся структура

Статус документа: evidence-neutral skeleton, подготовлен до завершения M4/M6.
Это исходник структуры, а не готовые слайды и не утверждённый научный вывод.

## Рамка и соглашения

- **Язык/формат (предположение):** русский, физическая аудитория, около 15 минут
  вместе с небольшим запасом на вопросы; дата конференции неизвестна. Это рабочее
  предположение, а не подтверждённое требование.
- **Область:** ограниченный численный эксперимент изолированного карликового
  NFW-гало при `N=10^5`, существующие вращающиеся IC, сравнение CDM/SIDM/dSIDM.
  Вывод не является общим запретом или доказательством образования тёмных дисков.
- **Доказательная база:** итоговые численные значения для основных слайдов
  появятся только из M4/M6 и явных locator'ов. До этого все result-поля ниже —
  placeholders. M5 отсутствует/не одобрен; при его отсутствии итоговый пакет
  должен оставаться `science_partial`.
- **Статусы claim:** `supported` здесь означает подтверждённое определение,
  условие или границу метода из плана, а не эмпирический результат; `provisional`
  означает ограничение/инвентарный контекст, требующий финальной проверки;
  `pending` означает отсутствие разрешённого результата; `withdrawn` оставлен
  для отзыва claim в будущей версии.
- **Locator convention:** записи с `[placeholder: ...]` нужно заменить на путь,
  hash/версию входа и, если применимо, окно времени из M4/M6. Старые PNG не
  используются как evidence; `candidate-only` означает лишь возможный locator
  после независимой проверки.

## Основная последовательность (11 слайдов)

### S01 — Вопрос и область вывода

- `claim_id: M7-C01`
- `thesis: Проверяется, может ли dSIDM в ограниченной серии изолированных вращающихся гало создать устойчивую тонкую структуру до численной патологии.`
- `evidence_locator: [placeholder: M6/claims.csv:M7-C01; final question and scope]`
- `status: pending`
- `visual_intent: чистый титульный слайд с одной схемой вопроса; asset_status=no asset selected`
- `time_estimate_min: 0.7`

На титуле не указывать дату, которой ещё нет. Подзаголовок должен явно говорить
«ограниченный численный эксперимент», а не обещать общий ответ.

### S02 — Почему этот вопрос остаётся узким

- `claim_id: M7-C02`
- `thesis: Диссипация может менять форму и вращение гало, но из этих механизмов ещё не следует образование устойчивого тёмного диска.`
- `evidence_locator: [placeholder: CONFERENCE_TWO_WEEK_PLAN.md §1; final wording in M6/claims.csv]`
- `status: supported`
- `visual_intent: причинная схема «взаимодействия → форма/момент → проверяемый критерий»; без старых результатов`
- `time_estimate_min: 0.9`

На слайде развести гипотезу, проверяемый критерий и широкий физический вопрос.
Не помещать сюда числа из старой презентации или итоговую фразу «диска нет».

### S03 — Модель, dSIDM и исходные условия

- `claim_id: M7-C03`
- `thesis: Сравнение строится на одной процедуре анализа изолированного NFW-гало с вращающимися IC и режимами CDM, SIDM и dSIDM.`
- `evidence_locator: [placeholder: CONFERENCE_TWO_WEEK_PLAN.md §2; M1 manifest group/run_id; IC provenance in M4]
- `status: supported`
- `visual_intent: блок-схема модели и provenance IC; candidate-only locator для IC/hash, не старое изображение`
- `time_estimate_min: 1.1`

`spin_k` — номинальный параметр генерации вращающейся IC; он не равен измеренному
`Jz`, безразмерному spin `lambda` и не доказывает равновесие IC. `kick_velocity` —
параметр `DM_KickPerCollision`; суффикс `_k0` в старом имени run не означает
невращающуюся IC. Эти два параметра будут показаны раздельно в финальной таблице.

### S04 — Что измеряется и в какой системе отсчёта

- `claim_id: M7-C04`
- `thesis: Форма, вращение и масса измеряются согласованно внутри физической апертуры `r<5 kpc` для `PartType3` с фиксированной исходной осью z.`
- `evidence_locator: [placeholder: CONFERENCE_TWO_WEEK_PLAN.md §4A; M2 metric schema/metadata; M4 series CSV]`
- `status: supported`
- `visual_intent: один annotated schematic апертуры и осей; no data asset selected`
- `time_estimate_min: 1.3`

Показать определения: `Jz = sum m_i (x_i v_y,i - y_i v_x,i)` после единого
центра и bulk-velocity frame, `jz=Jz/M`; ось z не поворачивается под каждый
снапшот. Развести общий `Jz`, удельный `jz` и массу апертуры. Если масса не
подтверждается через `Masses`/ненулевой `MassTable`, физические метрики не
подменять единичными массами.

### S05 — Критерии и временные окна

- `claim_id: M7-C05`
- `thesis: Кандидат на устойчивую структуру требует одновременного выполнения заранее объявленных эвристик на достаточном late-time покрытии.`
- `evidence_locator: [placeholder: CONFERENCE_TWO_WEEK_PLAN.md §4A; M4 late_time_summary output]`
- `status: supported`
- `visual_intent: timeline T=2/T=5 и checklist критериев; числа пометить `method`, не `result``
- `time_estimate_min: 1.2`

Методические окна: T=2 — `[1,2]`, T=5 — `[2.5,5]` в code time; общее окно
сравнения — `[1,2]`. Для late-time вывода нужно не менее трёх конечных значений,
а для частичной серии — пересечение с реально доступным интервалом. Первичный
screening использует `c/a<0.45`, `z_rms/R_rms<0.35`, `|Vrot|/sigma>0.6`;
это эвристика, а не универсальное определение диска. Все пороги на слайде
пометить как **method** и не выдавать за наблюдаемый результат.

### S06 — Controls и provenance до интерпретации

- `claim_id: M7-C06`
- `thesis: Сравнение допустимо только при явном различении серий, фактически применённых параметров и независимых статусов данных.`
- `evidence_locator: [placeholder: M1 run_manifest.csv; M4 campaign table; M5 approval record if any]`
- `status: provisional`
- `visual_intent: компактная матрица groups × controls и provenance-полоска; no result colors`
- `time_estimate_min: 1.0`

Предусмотрены шесть существующих k08 T=2 запусков и пять прежних k05 T=5 запусков;
это разные контексты, а не взаимозаменяемые matched controls. Новый matched T=5
k08 блок из четырёх запусков относится к M5 и пока отсутствует/не одобрен.
В финальном manifest `status`, `health` и `metrics_status` независимы: incomplete,
pathological, missing и conflict нельзя сворачивать в один `failed` или в нули.
Старый `run_commit` без evidence остаётся `unknown`; ревизия анализа указывается
отдельно.

### S07 — Существующие T=2: место для проверенного результата

- `claim_id: M7-C07`
- `thesis: Итог T=2 должен отвечать на вопрос о форме и вращении в пределах общего окна, но численные значения ещё не заморожены M6.`
- `evidence_locator: [placeholder: M4 campaign_metrics.csv; six k08 T=2 run_ids; M6 claims/figure_manifest]`
- `status: pending`
- `visual_intent: один будущий panel из M6 (shape + rotation + Jz/jz/M); candidate-only, старые PNG не evidence`
- `time_estimate_min: 1.2`

В каркас не вставлять итоговые `c/a`, `z_rms/R_rms`, `|Vrot|/sigma`, `Jz` или
классификации. До M4/M6 показывать только labelled placeholders: `final=—`,
`late_time=—`, `coverage=—`, `verdict_raw=—`. Отдельно сохранить возможность
сообщить `insufficient_coverage`, патологию или неизвестный статус, не называя
это отрицательным физическим результатом.

### S08 — Прежние T=5 и отсутствующий M5

- `claim_id: M7-C08`
- `thesis: T=5 расширяет проверяемое время, но доступность старых k05 данных и отсутствие одобренного matched k08 M5 не дают права объявлять science_complete.`
- `evidence_locator: [placeholder: M1 manifest + M4 coverage for five k05 T=5; M5 approval/queue record; M6 science status]`
- `status: pending`
- `visual_intent: две явно раздельные колонки `legacy k05 T=5` и `matched k08 T=5 M5`; pending/absent badges, без пустых нулей`
- `time_estimate_min: 1.0`

Показывать T=5 только с фактическим `t_reached`, coverage и pathology flags.
Пока matched M5 отсутствует/не одобрен, подпись пакета — `science_partial`, а
не `science_complete`. Не переносить вывод прежней k05 серии на high-spin k08.

### S09 — Численные патологии и границы интерпретации

- `claim_id: M7-C09`
- `thesis: Патология численного решения, перенос массы через апертуру и непроверенная сходимость ограничивают физическую интерпретацию даже завершённого run.`
- `evidence_locator: [placeholder: M1 health/provenance flags; M4 pathology flags; M2 frame metadata; M3 validation README]`
- `status: provisional`
- `visual_intent: разделённая панель «lifecycle / health / metrics» и схема aperture transfer; candidate-only old pathology PNG, not evidence`
- `time_estimate_min: 1.2`

`Systemstep<1e-6` — диагностический флаг, не автоматическое доказательство
физического коллапса. `Jz` внутри `r<5` может измениться из-за входа/выхода
массы; глобальное сохранение требует отдельного контроля. Отсутствие seed/resolution
проверок не позволяет заявлять статистическую значимость или сходимость. Python
reference/source audit диссипации не равен валидации выполняемого GIZMO; уровень
solver experiment пока `not_validated_in_solver`.

### S10 — Узкий вывод в исследованной области

- `claim_id: M7-C10`
- `thesis: До завершения M4/M6 честный вывод ограничен описанием проверенной области и её покрытия, а не универсальным утверждением «dSIDM не образует диск».`
- `evidence_locator: [placeholder: M6 claims.csv + campaign_metrics.csv + manifest revision; final wording after evidence freeze]`
- `status: pending`
- `visual_intent: один блок `supported / provisional / pending / withdrawn` с областью применимости; без иллюстрации результата до M6`
- `time_estimate_min: 0.8`

Финальная формулировка должна выбрать только то, что поддерживают фактические
окна, controls и coverage. Если candidate withdrawn, исправить этот claim во
всех зависимых материалах; отсутствие M5 не скрывать в сноске.

### S11 — Следующие шаги и готовность к передаче

- `claim_id: M7-C11`
- `thesis: Следующий безопасный шаг — проверить один здоровый real-series pilot, затем обновить все 11 строк, figures и claims одной ревизией анализа.`
- `evidence_locator: [placeholder: RUN_STATE next actions; M4 review/test log; M5 approval decision; M6/M7 freeze checklist]`
- `status: provisional`
- `visual_intent: короткий pipeline M4 → (M5 if approved) → M6 → M7; `rehearsal_pending` badge`
- `time_estimate_min: 0.6`

Не обещать дату и не объявлять репетицию состоявшейся. Экспорт/visual review новых
фигур и слайдов остаются отдельными задачами; подготовленный skeleton не является
`talk_ready`.

## Сокращаемая версия (если регламент меньше 15 минут)

Каждый блок ниже может быть убран без изменения основных claim ID; число минут —
оценка, не измерение репетиции.

### C01 — Сжать S01–S02 в титул + вопрос

- `claim_id: M7-C01C02`
- `thesis: Ограниченный вопрос и область вывода задаются до показа результатов.`
- `evidence_locator: [placeholder: S01/S02 locators]`
- `status: provisional`
- `visual_intent: одна схема вопроса; no data asset`
- `time_estimate_min: 0.4`

### C02 — Сжать S03–S04 в методическую карту

- `claim_id: M7-C03C04`
- `thesis: Параметры IC и frame-aware наблюдаемые величины определены до сравнения.`
- `evidence_locator: [placeholder: S03/S04 locators; M2 metadata]`
- `status: supported`
- `visual_intent: IC → aperture → Jz/jz schematic`
- `time_estimate_min: 0.8`

### C03 — Сжать S05–S06 в критерии и controls

- `claim_id: M7-C05C06`
- `thesis: Окна, эвристики и provenance делают сравнение проверяемым, но не создают result автоматически.`
- `evidence_locator: [placeholder: S05/S06 locators; M4/M6 final table]`
- `status: supported`
- `visual_intent: timeline + group matrix`
- `time_estimate_min: 0.8`

### C04 — Объединить S07–S10 в «evidence / limits / narrow conclusion»

- `claim_id: M7-C07C10`
- `thesis: Результат будет узким и условным до появления M4/M6 coverage и pathology-aware claims.`
- `evidence_locator: [placeholder: S07–S10 locators]`
- `status: pending`
- `visual_intent: evidence ledger with pending badges; no old image reuse`
- `time_estimate_min: 2.0`

## Backup (не считать основными слайдами)

### B01 — Словарь параметров

- `claim_id: M7-B01`
- `thesis: `spin_k`, `kick_velocity`, `D`, `Jz` и `jz` — разные величины и должны иметь отдельные колонки.`
- `evidence_locator: [placeholder: plan §2; manifest schema; M2 metadata]`
- `status: supported`
- `visual_intent: таблица терминов и единиц; method labels`

### B02 — Формула диссипации и уровень проверки

- `claim_id: M7-B02`
- `thesis: Для `kick_velocity=0` формула `loss_fraction=2D-D^2` относится к относительной энергии в СЦМ и не заменяет solver validation.`
- `evidence_locator: [placeholder: CONFERENCE_TWO_WEEK_PLAN.md §4B; validation/README.md; M3 CSV]`
- `status: supported`
- `visual_intent: формула + ladder analytic/python/source_audit/solver_experiment`

### B03 — Матрица lifecycle × health × metrics

- `claim_id: M7-B03`
- `thesis: `completed`, `incomplete`, `pathological` и `metrics_status` описывают независимые аспекты одного run.`
- `evidence_locator: [placeholder: M1 run_manifest.csv schema and metadata]`
- `status: supported`
- `visual_intent: 3-column status matrix`

### B04 — Что означает `science_partial`

- `claim_id: M7-B04`
- `thesis: Отсутствующий или не одобренный M5 оставляет доклад допустимым только с явно суженным выводом и статусом `science_partial`.`
- `evidence_locator: [placeholder: M5 decision; M6 readiness table]`
- `status: provisional`
- `visual_intent: readiness badge, not a result plot`

### B05 — Provenance и visual review checklist

- `claim_id: M7-B05`
- `thesis: Каждый финальный claim должен быть связан с versioned input, analysis revision, figure locator и отдельной проверкой читаемости.`
- `evidence_locator: [placeholder: M6 figure_manifest/claims/reproduce; M7 visual-review record]`
- `status: provisional`
- `visual_intent: checklist; old PNGs are candidate-only`

## Freeze checklist для будущей версии

1. Заменить каждый `[placeholder: ...]` на конкретный locator, hash/analysis
   revision и фактическое окно; сохранить `pending` там, где M4/M6 ещё не дали
   evidence.
2. Вставить только значения, которые есть в проверенном M4/M6 CSV; не переносить
   числа из `2026-09-10` или из старых отчётов без нового locator.
3. Проверить, что `run_id` и `group` не смешаны, `spin_k` не подменяет `Jz`, а
   `kick_velocity` явно указан.
4. Обновить status `science_partial`/`science_complete`, visual-review и export
   отдельно; `rehearsal_pending` сменить только после фактической репетиции.
