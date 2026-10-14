# PLAN — текущие обязательства

Checkpoint ID: `migration-1-commit`

Последняя сверка источников: 2026-10-14 (датировки источников; перед consequential action проверить live state). Ревизия: migration-1-complete. Единственный список открытых задач. `done` — только с evidence; `superseded` требует причины. Старые permissions не переносятся.

## P-001 — Мигрировать систему памяти агента

Status: done. Evidence: root `AGENTS.md`, four canonical memory files, important-only records gate, updated adapters/skills/session setting and removal of obsolete duplicated rules/state. Origin: явный запрос пользователя. Approval: миграция llm/ и ссылок согласована; симуляции, commits/push и unrelated cleanup не входят.

Acceptance: AGENTS + PROJECT/PLAN/ACTIVE/MEMORY — единственные рабочие правила/state; boot без рекурсивного чтения; records gate встроен; skill refs/session settings/gitignore обновлены; старые конкурирующие rules/state/prompts удалены после извлечения; важные reports/manifests сохранены; concrete project-path refs, JSON settings, shell syntax, and `git diff --check` verified.

## P-002 — Конференционный пакет: довести до проверяемого handoff

Status: deferred pending user priority/deadline confirmation. Origin: migrated out of the removed conference planning/prompt documents; current source is the package `nbody/analysis/presentations/conference_2026/`. Дата выступления и текущий live status не подтверждены; сначала установить.

Acceptance: согласовать/freeze claims с первичными manifests/metrics; различать matched k08 T=5 M5 (три принятых ряда), accepted canonical D0.50 retry2 (T=5, 52 points, `no-disk-before-pathology`, ещё не integrated в package ledgers), failed retry1/ timestep-control и два legacy deferred rows. Критерии в актуальном package, не старом plan. PDF/export/figures/notes/Q&A готовы и deck визуально проверен по RUN_STATE; human rehearsal остаётся pending. Package остаётся `science_partial` до integration/freeze claims. Дата выступления в старых assumptions не подтверждена: не утверждать, что deadline ещё впереди/прошёл.

Next: интегрировать accepted retry2 D0.50 в `nbody/analysis/presentations/conference_2026/` и обновить manifest/metrics/claims/reproduce/summary согласно existing lifecycle gates; выяснить ближайший приоритет и deadline у пользователя. Не переписывать failed retry1 как T=5 result. Проверить deferred rows и текущее состояние; старый ресурсный snapshot не актуален. Не запускать новые production runs только ради вида завершённости.

## P-003 — IC rotation / weak-dissipation исследования

Status: deferred pending user priority (научные действия требуют отдельного scoped approval и gates). Origin: свежие `activeContext.md`/`progress.md` от 2026-10-14.

Три текущие линии, не эквивалентные готовности к launch:
1. `corecusp_N1e7`: разобраться в расхождении central velocity dispersion между prereun и GIZMO; проверить центр/потенциал. Не принимать IC gate до подтверждения.
2. Rotation IC: выбранная ветвь `vphi = 0.25 vc`; сравнить prereun/GIZMO и вращательную поддержку. Не смешивать с уже завершённым baseline и не объявлять физически подтверждённый диск.
3. N=10^7, T=5, SIDM 5/10: возможные следующие запуски только после IC/ранней-state quality gate, ресурсов и согласованного сравнения с CDM. Запуски не разрешены этим планом.

Acceptance для каждой линии: сопоставимый критерий и canonical evidence; для launch — текущая проверка ресурсов/процессов/IC и явное одобрение параметров.

## P-004 — Отложенные кампании/дефекты: сохранять, не считать активными подтверждёнными багами

Status: deferred; revalidate before action. Origin: legacy backlog/state.

- 32 k05/k08-dependent runs: сохранить run trees, reports и provenance; никакого автоматического архивирования/удаления. Решение о валидности/инвалидации и cleanup — после сверки актуального evidence/approval.
- Batch-helper `IndexError: list index out of range` (helper did not pass two required CLI args), четыре неопределённых legacy runs, weak-dissipation resource gate и merge decision — исторические leads; проверить релевантность/состояние перед возобновлением. Неархивированные 32-run k05/k08 inventory — `llm/records/ic-rotation-run-inventory.csv`; существующие IC lineage — `llm/records/ic-rotation-manifest.csv`.
- Старый `progress.md` содержал незакрытые GADGET workflow path fixes (`run_gadget.sh`, `Makefile`), GADGET-2 workflow test, mixed CDM+SIDM IC config test и добавление mixed-IC примера в `gizmo-sim`. Это deferred, не текущий приоритет; перед работой проверить код/актуальность.
- Corecusp / GADGET / mixed-IC / solver-validation / analysis defects, не названные в актуальном триплете, остаются deferred; не превращать старый backlog в активный список bugs без воспроизведения.

## Следующий выбор

После migration следующий сессионный шаг — спросить пользователя, что ставить выше: конференционный evidence package (P-002) или одну из трёх научных линий P-003. Сначала уточнить дату/актуальность, не выполнять скрытое продолжение старого roadmap.

## Правила перехода

- Приоритет: текущий пользовательский запрос → PROJECT safety/scope → этот PLAN → ACTIVE checkpoint → MEMORY/evidence. При расхождении сначала reconcile, не выбирать удобную версию.
- Любой новый дорогой эксперимент/проектная цель сначала proposed с критериями и approval; самостоятельно дробить разрешённую задачу можно, расширять scope нельзя.
- P-001 закрыт после проверки миграции. Не удалять этот PLAN и открытые пункты ради упрощения.
