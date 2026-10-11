# Технический план конференционной кампании

> Редакция 2026-10-10. Выполняется только после отдельного старта кампании.
> Этот файл находится в `llm/`; корневой `implementation_plan.md` относится
> к другому проекту унификации анализа и не должен перезаписываться.
> Цель и научная приёмка: `llm/CONFERENCE_TWO_WEEK_PLAN.md`.
> Автономия, разрешения и восстановление: `llm/CODEX_AUTONOMOUS_PROMPT.md`.

## 1. Цель и границы

Сделать минимальные изменения, необходимые для прослеживаемого анализа dSIDM:
manifest прогонов, корректный Jz/jz, проверка диссипации, согласованные временные
сводки и фигуры; затем собрать презентацию и материалы выступления.
Существующие loaders, AnalysisPaths и registry остаются основной архитектурой.
Новых пакетов по умолчанию нет. Никакие перечисленные ниже файлы, результаты
или этапы не считаются уже созданными/выполненными.

Допустимы небольшие изменения предлагаемой декомпозиции после чтения актуального
кода. Контракты данных и критерии приёмки сохраняются; существенные изменения
метода фиксируются с причиной и повторной проверкой затронутых результатов.

## 2. Факты и обязательные уточнения

Ревизия аудита инфраструктуры — `0c4b607`. Изменчивые факты перепроверять при
старте. Прежние списки «F1…F16» не использовать как безусловную истину.

| Наблюдение | Следствие для реализации |
|---|---|
| Старые T=5 используют IC k05, а `_k0` в run ID обозначает kick=0 | отдельные поля spin_k и kick_velocity; параметры не восстанавливать только по имени |
| `add_halo_rotation.py` содержит расчёт азимутального потока | документировать фактический код/знак/единицы и измеренные IC-метрики; не обещать равновесие |
| `SeriesMetric` пока не содержит Jz; при отсутствии Masses reader использует единицы | для физического Jz/M нужна корректная загрузка массы, включая Header/MassTable |
| `make_prerun_plots.py` пишет `analysis/prerun/<run.name>/` | проверить коллизии basename; manifest всегда использует group/run |
| `resolve_metrics_path()` предпочитает существующий legacy CSV | после регенерации явно выбирать новый CSV и проверять его schema/provenance |
| `classify_series` сравнивает extrema по времени | хранить сырой verdict отдельно от проверки одновременных/устойчивых критериев |
| CDM/SIDM templates различаются MaxSizeTimestep | четыре новых T=5 имеют явный 0.005; разницу старых controls не скрывать |
| Частицы SIDM — PartType3 | проверять применяемые mass/softening и compile flags, а не только SofteningHalo |
| Wrapper проверяет наличие restart.0 перед resume | не считать resume гарантированным; отсутствие TimeBetRestartFile не доказывает невозможность restart |
| `nbody/runs/**` и многие экспорты ignored | executable очередь хранить в scripts; исходники пакета и generated exports учитывать раздельно |

## 3. Контракты данных

### Manifest

Модуль `nbody/scripts/conference/manifest.py`: `ManifestRow`,
`read_run_manifest_row()`, `scan_runs()`, `write_manifest_csv()`.
Переиспользовать парсеры `check_simulations` вместо второй несовместимой
интерпретации логов. Записывать строки детерминированно по полному run_id.

| Поля | Смысл/источник |
|---|---|
| run_id, group, run_path | путь относительно `nbody/runs/`, уникальность group/run |
| ic_path, ic_sha256, spin_k, spin_k_source | сохранённый InitCondFile и подтверждённое происхождение IC; nominal spin, не измеренный момент |
| n_particles, ptype, sigma_over_m, dissipation_d, kick_velocity, velocity_scale | параметры/данные; единицы в metadata |
| softening_value, softening_parameter, max_size_timestep | эффективные настройки нужного ptype; остальные force/time tolerances в сохранённом наборе параметров |
| time_max, time_bet_snapshot, first_snapshot, time_limit_cpu, mpi_procs | фактически применённые параметры, не нынешние defaults |
| run_commit, analysis_commit, analysis_dirty, analysis_patch_sha256 | ревизия запуска из его provenance; отдельно ревизия анализа и fingerprint незакоммиченного кода |
| params_sha256, solver_source_sha256, solver_binary_sha256 | fingerprints и источник подтверждения связи исходников/бинарника |
| snapshots, t_reached, min_systemstep, ninteractions_final | реальные файлы/лог/явно выбранный CSV |
| status, health, metrics_status, verdict_raw | независимые состояния жизненного цикла, качества и анализа |
| metrics_csv, analysis_schema_version, checked_at_utc | locator, версия метода/схемы, время проверки |
| started_at_utc, ended_at_utc, wall_minutes, timing_source | наблюдённое время; оценка из mtime только с пометкой estimated |
| provenance_status, notes | missing/conflict/unknown и причины |

Отсутствующие числа — nan/пустое поле по документированной схеме, строки —
unknown; не подставлять 0 для неизвестного D/σ/момента. Ноль для CDM допустим
по подтверждённому режиму, а не отсутствию параметра. Старый run_commit без
доказательств — unknown, никогда не текущий HEAD. Хеш существующей IC описывает
её текущую версию; без сохранённого старого хеша не утверждать, что файл никогда
не менялся. Хешировать большие файлы однократно/по необходимости, не в polling.

Состояния:

- status: planned / running / completed / incomplete / failed / unknown;
- health: ok / degraded / pathological / unknown;
- metrics_status: missing / partial / complete / invalid.

completed требует подтверждения TimeMax и завершения, running — живого процесса
или надёжного job status. Нет лога — unknown с причиной, не автоматически failed.
Патология может сочетаться с completed; отсутствие CSV не меняет жизненный статус.
Health=ok означает отсутствие выявленных флагов по доступным проверкам, не доказанную
сходимость. Конфликты `.gizmo_run.param`, usedvalues и логов показывать, не замалчивать.

### Сырые момент и масса

Расширить `nbody/scripts/analysis/loaders/prerun.py::SeriesMetric` тремя полями
в конце, с nan-default для совместимости старых конструкторов/CSV:

| Поле | Определение |
|---|---|
| jz_total_r5 | Σ m_i (x_i v_yi − y_i v_xi), общий Jz в r<5 |
| jz_mass_r5 | Σ m_i в той же апертуре |
| jz_per_mass_r5 | jz_total_r5 / jz_mass_r5, удельный jz |

`angular_momentum_stats(pos_centered, vel_centered, mass, radius)` возвращает
три значения. Центр — тот же weighted_center/shrink_center, что для формы;
скорости отсчитываются от массово-взвешенной bulk velocity выбранного PartType3
по всему снапшоту. Для вращения используй ту же систему отсчёта. Ось z фиксирована
осью исходной IC, не поворачивается под каждый снапшот ради улучшения результата.
Масса берётся из Masses или ненулевого MassTable[ptype]; если её установить
нельзя, абсолютные физические метрики invalid, а не «частицы по единице массы».

В metadata фиксировать ptype, единицы, центр/velocity frame, апертуру, ось и
analysis_schema_version. Изменение mass/velocity frame может корректировать старые
колонки: разрешено только с объяснением, аналитическим тестом и versioned diff,
а не безусловным требованием «изменились лишь новые колонки».

Нормировки вычисляются в слое серии/сводки, не в reader одного снапшота:

- `jz_total_ratio_r5 = Jz(t)/Jz(t0)`;
- `jz_specific_ratio_r5 = jz(t)/jz(t0)`.

Не обозначать удельную нормировку как Jz/Jz0. База — подтверждённый начальный
снапшот данного run или его доказанная IC, с base_time/base_source. Если t0
отсутствует, не называть первый поздний снапшот t=0. При нулевой/численно малой
базе писать nan и normalization_undefined; допуск обосновать масштабом задачи.
Сохранить знак Jz. При пустой апертуре масса 0, удельный момент nan.
Глобальный момент нужен дополнительно, если делается вывод о глобальном сохранении.

### Валидация диссипации

`conference/dissipation_check.py`: независимая reference pairwise-проверка.
Результат содержит case_id, D, kick_velocity, seed, n_trials, loss_fraction_measured,
loss_fraction_theory, momentum_residual, angular_momentum_change, tolerances,
source_hash, validation_level и verdict. Явно определить положительную потерю
энергии в системе центра масс, не использовать неоднозначное ΔE/E.

Уровни: analytic / python_reference / source_audit / solver_experiment.
Один уровень не автоматически доказывает другой. Для kick=0 проверить 2D−D²,
равные/неравные массы и краевые D=0,1; ненулевой kick проверять по полной формуле.
Угловой момент исследовать по геометрии и случайным направлениям; не делать
assert residual!=0 для каждого случая. Гравитационную/полную энергию гало не
сверять напрямую с долей потерь энергии одного столкновения.
Реальный GIZMO-тест проектируется отдельно по научному плану, не встроен в pytest.

### Сводки, фигуры и claims

`conference/summarize_campaign.py`: `late_time_summary()`,
`build_campaign_table()`; вход — manifest и явные CSV, не неявный glob
с выбором первого подходящего файла. Окна и критерии — в научном плане.
Выход содержит final, median, actual_t_start/end, count/coverage по метрике,
базу нормировки, pathology flags, verdict_raw и interpretation.
Не интерполировать отсутствующий late-time участок и не трактовать nan как 0.
Не выкидывать всю строку формы из-за отсутствующего timestep: coverage по колонкам.

`figure_manifest.csv`: figure_id, path, input CSV/hash, run IDs, plot ID,
command, analysis version. `claims.csv`: claim_id, text, run_ids, locator,
columns/time_window, method_version, limitation, status (supported/provisional/withdrawn).
Слайды ссылаются на claim IDs; ошибочный claim отзывается и исправляется
во всех зависимых материалах.

## 4. Файлы и интеграция

| Путь | Работа |
|---|---|
| `nbody/scripts/conference/__init__.py` | пакет вспомогательных текстовых tools, без собственного рисования |
| `nbody/scripts/conference/manifest.py` | инвентаризация и provenance |
| `nbody/scripts/conference/dissipation_check.py` | reference validation |
| `nbody/scripts/conference/summarize_campaign.py` | согласованная сводка по manifest |
| `nbody/scripts/conference/queue_T5.sh` | только при одобренном T=5: последовательная очередь, preflight, бюджет, abort без перезаписи |
| `analysis/loaders/prerun.py`, при необходимости `loaders/snapshots.py` | Jz, единицы/mass/frame и минимальная совместимая миграция reader'ов |
| `analysis/loaders/__init__.py` | экспорт helper, если соответствует API пакета |
| `analysis/runners/make_prerun_plots.py` | version/provenance серии; защита от коллизий, если реально требуется |
| `analysis/runners/make_campaign_diag_plots.py`, `analysis/plots/campaigns.py` | панель Jz/jz/M через существующий registry-контракт |
| `analysis/runners/make_campaign_morphology_plots.py` | точные подписи σ/D/spin/kick, если используются в докладе |
| `tests/test_conference_tools.py`, `tests/test_loaders_math.py` | значимые тесты новых контрактов |
| `tests/test_render_smoke.py`, golden fixtures | только необходимые дополнения при изменении plot/math |
| `nbody/analysis/REGISTRY.md` | регенерация, только если меняется реестр |
| `nbody/analysis/presentations/conference_2026/` | пакет из научного плана; существующие версии сохранять |
| `llm/RUN_STATE.md`, `llm/CODEX_BACKLOG.md`, memory-bank | создавать/обновлять только после старта работ |

Пути `analysis/...` в таблице относительны к `nbody/scripts/`.
Не менять BasePlot/registry ради единичной фигуры. Без ad-hoc matplotlib/PIL
в conference tools; графика только через имеющиеся слои. Чистые CSV-tools могут
иметь собственный `--out`; canonical plot runners не получают `--outdir`.

До регенерации сохранить прежние производные CSV и их fingerprints в versioned
подкаталог пакета. Старые `runs/**/partial_analysis` не менять. Проверять, что
downstream использует именно обновлённые CSV. При конфликте одинаковых basename
не писать в чужой canonical output: минимально расширить безопасную идентификацию
артефакта через AnalysisPaths и тест, либо явно отметить блокер. Нельзя обходить
контракт путей произвольной записью в run-каталог.

## 5. Этапы и проверки (M0…M8)

| Этап | Зависимости | Результат и условие перехода |
|---|---|---|
| M0 — preflight | явный старт | возможности/разрешения/срок, исходный dirty-state, baseline и начальный RUN_STATE; отсутствующие возможности блокируют только зависимые ветки |
| M1 — manifest | M0 | схема + parser-тесты; 11 старых run ID проверены, missing/conflict показаны; новые runs добавляются как planned |
| M2 — Jz и frame | M0 | helper/readers/schema, аналитические тесты, совместимость и документированный diff метода |
| M3 — диссипация | M0 | reference-тесты и source audit; недоступный исходник/solver явно непроверен, не имитируется |
| M4 — существующие серии | M1, M2 | шесть k08 T=2 + пять k05 T=5 по доступным данным, явный выбор CSV, late-time сводки; нет тихого legacy fallback |
| M5 — T=5 | M1–M4, одобрение и ресурсы | четыре matched run последовательно, контроль состояния/лимитов; во время активного run только lifecycle/resource checks, canonical post-run анализ после terminal; данные и незавершённые состояния видимы |
| M6 — evidence и фигуры | M3, M4; M5 по доступности | claims, campaign_metrics, 3–4 фигуры, reproducibility; с неполным M5 — science_partial |
| M7 — слайды и речь | структура с M0, цифры из M6 | deck/source/export, notes, Q&A; отдельная отметка visual review |
| M8 — передача/репетиция | M6, M7 | проверенный пакет, актуальный RUN_STATE, фактический feedback пользователя или rehearsal_pending |

M1–M3 можно выполнять в удобном порядке при сохранении контрактов. M7 начинать
с каркаса рано; итоговые числа вставлять после проверки. Ожидающий разрешения
M5 не блокирует M6/M7 на существующих данных. Проверка solver и σ/m=5 extension
ведутся как условные подзадачи с отдельными разрешениями; их пропуск не скрывается.
M5=done означает обработанный блок с явными исходами, а не автоматически
science_complete: научная полнота определяется фактическим coverage.

После завершения и независимой проверки каждого M-этапа создаётся отдельный
локальный stage-checkpoint commit до перехода к следующему этапу. Root/оркестратор
перед commit проверяет diff, соответствующие тесты и принадлежность файлов.
В commit попадают только явно относящиеся к этому этапу файлы: незавершённые,
deferred и unrelated dirty paths остаются вне него. Используй понятный префикс,
например `stage(Mn): ...`. После commit сохрани полный SHA. Push не следует из
commit: он разрешён только после явного подтверждения конкретных remote и ref.
В состоянии/handoff фиксируй remote, ref и фактический результат/вывод push;
при отказе или недоступности сохрани локальный commit со статусом `push_pending`.
Запрещены force-push, reset и clean; успешный push нельзя заявлять без
фактического вывода команды.

### Минимальные тесты

- Manifest: run ID с группой, разные источники параметров/конфликт, нет лога,
  нет метрик, incomplete после лимита, completed+pathological, неизвестный
  run_commit, текущий analysis_commit; запусков GIZMO в тестах нет.
- Jz: кольцо известной массы/радиуса; жёсткое вращение с
  Jz=Ω·ΣmR², неравные массы, смена знака, перенос координат/общей скорости
  с корректным центрированием, пустая апертура, MassTable fallback.
- Нормировка: одинаковая база даёт 1 при ненулевом Jz; отсутствие t0 и нулевая
  база не дают ложную единицу; общий/удельный момент различаются при изменении массы.
- CSV: стабильный header, пустая серия не падает на metrics[0], nan и старые
  колонки читаются; свежая серия не затеняется legacy CSV; коллизия run.name
  из разных групп не приводит к перезаписи.
- Dissipation: 2D−D², импульс, крайние D, ненулевой kick, geometry/seed;
  допуски привязаны к масштабу величин, а не только rel при ожидаемом нуле.
- Late-time: границы окна, мало данных, несортированные времена, пропуски
  и раздельный coverage; несинхронные экстремумы не дают устойчивого кандидата.
- Figures: существующие registry/plotter-contract/render tests для изменённых
  панелей; корректные подписи spin_k и kick_velocity.

Команды для будущей реализации, выбирать по изменению:

```bash
.venv/bin/python -m pytest tests/test_loaders_math.py tests/test_conference_tools.py -q
.venv/bin/python -m pytest tests/test_registry.py tests/test_plotter_contract.py tests/test_render_smoke.py -q
.venv/bin/python -m pytest tests/ -q
```

Первую команду выполнять после появления нового тестового файла. Golden values
обновлять только после независимого вывода ожидаемых значений и записи причины.
Полный suite не запускать после каждой Markdown-правки. Не считать pre-existing
падение следствием нового кода; доказать отсутствие регрессии в затронутой области.

### Проверка на реальных данных

После тестов взять один существующий k08 run, сохранить старый CSV, пересчитать
каноническим runner'ом и сравнить старые колонки с учётом объявленной миграции.
Проверить Jz на отдельном расчёте из тех же входных массивов/единиц. Затем
распространить метод на остальные runs. Убедиться, что manifest, сводка, figure
и slide claim указывают на одну версию данных.

Сохранить точные команды, версии и входные файлы в `reproduce.md`. Команда
с многоточием или ещё не реализованным флагом не считается воспроизводимой.
Скрипты должны корректно работать в заявленной среде host/container; не смешивать
`/home/kds/sci/gadget2_docker/nbody` с контейнерным `/nbody`.
При работе на host задать корректный NBODY_ANALYSIS_ROOT через поддержанный контракт.

## 6. Контроль изменения плана

Стабильную спецификацию не превращать в ежедневный лог. Прогресс и следующие
действия хранить в RUN_STATE, устойчивые научные решения — в отчёте/memory-bank.
При изменении контракта обновить связанные разделы всех трёх документов и
отметить, какие артефакты требуют повторного расчёта.

Не объявлять результат готовым по наличию файлов: проверять содержимое,
происхождение, читаемость и соответствие научной приёмке. Завершение очереди,
зелёные тесты и готовность выступления — отдельные проверки.
