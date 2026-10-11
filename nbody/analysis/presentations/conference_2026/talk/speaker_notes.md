# Заметки докладчика M7 — evidence-aware handoff

Статус: `science_partial` · `visual_review_pending` · `rehearsal_pending`; PDF
export verified. Ниже — русская структура примерно на 15 минут; actual user
rehearsal ещё не проведена. Первый CDM k08 T5 run прошёл terminal/post-run gate
и интегрирован; остальные matched k08 M5 runs pending, поэтому claims ещё не
frozen. Deferred runs — missing evidence, не отрицательный результат.

## Сценарий и переходы

| Слайд | Время, мин | Устный акцент и переход |
|---|---:|---|
| S01 | 0:45 | Вопрос: может ли dSIDM дать устойчивую тонкую вращательную структуру в ограниченной серии? Обозначить scope. |
| S02 | 0:50 | Это не общий запрет и не обещание диска: отделяем гипотезу от критерия. |
| S03 | 1:10 | Изолированное NFW-гало, вращающиеся IC, CDM/SIDM/dSIDM. `spin_k` — параметр IC, не измеренный момент; `kick_velocity` — `DM_KickPerCollision`, не spin. |
| S04 | 1:20 | В `r<5 kpc` после единого центра и bulk-frame: `Jz=Σm(x vy-y vx)`, `jz=Jz/M`; ось z фиксирована. Aperture transfer может менять апертурный момент. |
| S05 | 1:10 | Окна и эвристики — method, не observation; отсутствующий late-time участок не интерполируем. |
| S06 | 1:00 | k08 T=2, legacy k05 T=5 и matched k08 T=5 M5 (первый CDM принят, остальные pending) — разные контексты. Lifecycle, health и metrics_status независимы. |
| S07 | 1:20 | Для T=2 показывать только значения, проверенные по `campaign_metrics.csv`/series metadata и связанному `run_id`; до freeze произнести `pending`, не подставлять число и не использовать старый PNG как evidence. |
| S08 | 1:00 | Legacy k05 T=5 не заменяет matched k08 controls. Первый CDM k08 T=5 run принят, остальные M5 runs pending; явно сказать `science_partial` и что claims не frozen. Deferred rows назвать missing evidence. |
| S09 | 1:20 | Патология, aperture transfer и отсутствие convergence/seed ограничивают интерпретацию. `Systemstep<1e-6` — диагностический флаг; reference-check не равен solver validation. |
| S10 | 0:55 | Формулировать только claim, поддержанный coverage и controls из `claims.csv`; не произносить «dSIDM не образует диск» без такой поддержки. |
| S11 | 0:40 | M4 → M5 post-run gate → M6 → M7 → visual review → user rehearsal. Сохранить `rehearsal_pending`; дату не объявлять. |
| Резерв | 2:00 | Backup B01–B05 по вопросам и оставшемуся времени. |

Сумма основных слайдов — около 11,5 минут; оставшееся время — запас на
переходы, вопросы или backup. Это плановая оценка, не результат репетиции.

## Словарь

- `D` — безразмерная доля диссипативного изменения скорости. Формула
  `2D-D^2` при `kick_velocity=0` относится к относительной энергии в СЦМ и не
  является solver validation.
- `spin_k` — номинальный параметр вращающейся IC; из него нельзя заключить
  измеренный `Jz`, spin λ или равновесие.
- `kick_velocity` — velocity kick на столкновение
  (`DM_KickPerCollision`); нулевой kick не означает невращающуюся IC.
- `Jz` — общий z-компонент момента внутри апертуры; `jz=Jz/M` — удельный
  момент. Не подписывать `jz/jz0` как `Jz/Jz0`.
- Aperture transfer — вход/выход частиц через `r<5`, поэтому апертурный `Jz`
  может изменяться без нарушения глобального сохранения.
- Численная патология — диагностический флаг, а не автоматически физический
  коллапс или результат.

## Evidence locators перед устным показом чисел

Перед evidence freeze сверить каждый claim с [claims.csv](../claims.csv),
каждое число — с [campaign_metrics.csv](../campaign_metrics.csv),
`run_id`, metric key, фактическим окном и series metadata. Lifecycle и
deferred/M5 ограничения проверять в [run_manifest.csv](../run_manifest.csv) и
`run_manifest_metadata.json`; figure locator и revision — в
[figure_manifest.csv](../figs/figure_manifest.csv). Метод и воспроизводимость
сверять с [reproduce.md](../reproduce.md) и
[processing_report.md](../m4_series/processing_report.md). Если locator,
coverage или revision отсутствует, устный ответ остаётся `pending`.

## Репетиционный чеклист

- [ ] Фактический темп и переходы проверены пользователем; до этого
  `rehearsal_pending`.
- [ ] Ни один `pending`/`provisional` claim не превращён в result.
- [ ] `science_partial`, deferred/M5 limitation и scope произнесены явно.
- [ ] PDF export verified; полный visual freeze выполнен отдельно, а не по
  одному наличию файла.
- [ ] После freeze визуально проверены слайды и locator footers; это отдельная
  проверка, не часть этого документа.
