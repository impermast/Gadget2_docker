# PLAN — текущие обязательства

Checkpoint ID: `s2p5-pair-20261020`

Последняя сверка источников: 2026-10-20 (live launch preflight). Ревизия: `s2p5-pair-20261020`. Единственный список открытых задач. `done` — только с evidence; `superseded` требует причины. Старые permissions не переносятся.

## P-001 — Мигрировать систему памяти агента

Status: done. Evidence: root `AGENTS.md`, four canonical memory files, important-only records gate, updated adapters/skills/session setting and removal of obsolete duplicated rules/state. Origin: явный запрос пользователя. Approval: миграция llm/ и ссылок согласована; симуляции, commits/push и unrelated cleanup не входят.

Acceptance: AGENTS + PROJECT/PLAN/ACTIVE/MEMORY — единственные рабочие правила/state; boot без рекурсивного чтения; records gate встроен; skill refs/session settings/gitignore обновлены; старые конкурирующие rules/state/prompts удалены после извлечения; важные reports/manifests сохранены; concrete project-path refs, JSON settings, shell syntax, and `git diff --check` verified.

## P-002 — Конференционный пакет: довести до проверяемого handoff

Status: active for ICPPA conference preparation by user request m01909. Official ICPPA 2026 schedule found at `https://indico.particle.mephi.ru/event/626/page/112-conference-venue`: 27–30 Oct 2026, Moscow; user’s actual session, slot, duration and desired output still need confirmation. User phrase “в виде просперити” is ambiguous; provisionally interpret as presentation material.

Acceptance: reconcile claims with primary manifests/metrics; distinguish execution-complete k08 T=5 rows, D0.50 retry2, failed retry1/timestep-control, and legacy deferred rows. The k05/k08 ICs are marked `invalidated_by_IC_rotation` in `llm/records/ic-rotation-run-inventory.csv`, and their generator has a verified v_phi sign mismatch; do not present their completed runs as equilibrium-IC dark-disk evidence. Preserve them as legacy diagnostics. Retry2 primary evidence now confirms terminal `Final time=5 reached` and 52 snapshots, but `run.state` is stale at t=4.990/50, `experiment.md` has wrong IC/parameter/runtime details, and no HDF5/log hashes are recorded; keep its conclusion provisional until provenance and package ledgers are corrected. Reconcile `series_index.csv` classifier statuses with completed metrics; update manifest/metrics/claims/reproduce/summary and only regenerate registered package figures after inspecting collisions. Resolve contradictory visual-review badges. Existing deck is 11 slides + 5 backup, exported to 16-page PDF/PPTX; `science_partial`, rehearsal pending. Do not present C1’s 9-M4 scope as a universal or M5-inclusive result; do not treat deferred as negative evidence.

Next: user m02393 approved launching the proposed pair if disk space is ample. Preflight passed: 48.62 GiB free, typical pair ~9.91 GiB, conservative allocation 16 GiB with 12 GiB reserve; no existing MPI/solver, ~8 GiB available RAM, container quota 10 CPU. IC hash/config match, binary/dependencies present and no rebuild needed; central-resolution limitation retained. Queue started at 14:18 UTC / 17:18 MSK, 2026-10-20: `20261020_sidm_s2p5_rotN1e6_T3_mpi10` (sigma=2.5,D=0) is running; `20261020_dsidm_s2p5_f0p1_rotN1e6_T3_mpi10` (sigma=2.5,D=.05131670194948623,f=.1) is queued next, N=1e6 lambda-prime=.035, T=3, cadence=.05, max-step=.005, MPI10, kick=0. Exact commands and provenance: `nbody/runs/.queues/20261020_s2p5_rotN1e6_T3/launch.json` and `queue.sh`. Sequential queue must pass time/log/snapshot and numerical-health gates before the second run; no third run, cleanup, rebuild or Git action approved. Afterwards analyze the matched series and continue P-002 package reconciliation; do not revive invalid k08 ICs or mix rotation definitions.

## P-003 — IC rotation / weak-dissipation исследования

Status: scoped T=3 triplet завершён 2026-10-15; dark-disk signature не обнаружен. Полный кинетический аудит 2026-10-16: в dSIDM global K выросла на 0.482% raw и на 1.24% относительно нормированного среднего CDM/SIDM контроля; excess растёт ≈0.449 процентного пункта/code-time (61 unique times, R²=.989). Ранее оценённые ~23T относятся только к полной механической |E|, не к падению K. T=1 cleanup завершён по m01872; исходные HDF5 временные ряды разрежены, сохраняются только выбранные точки. Остальные линии остаются deferred. Origin: свежие `activeContext.md`/`progress.md` от 2026-10-14 плюс явное одобрение m00427/m00528.

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

## Текущий scoped action

Approved sigma=2.5 pair (m02393) launched through `nbody/runs/.queues/20261020_s2p5_rotN1e6_T3/queue.sh` at 2026-10-20 14:18 UTC; queue PID=105, first mpirun PID=164 and 10 GIZMO ranks confirmed, actual SIDM usedvalues match approval. First checker says running/health=ok/preliminary; dSIDM remains queued. Inspect `queue.log` and actual per-run evidence before claiming completion; never restart the queue blindly. No third run approved. Both use existing IC SHA-256 `308599c843f887a574b5c0773591d906d6c80c4c15da4bec85fb9489d84b1c0a`; solver SHA-256 `bb3927203b3ea9202de9da7605de292ccfbdf1325ea702d279bb30e0a369e2db`; full source/template identities and limitations are in `launch.json`. Source↔binary linkage and central-resolution convergence are not proven; the old IC's N(<1 kpc)=41929 is below its separate 100000-particle threshold. This is a controlled same-IC finite-resolution extension, not a validation claim.

Baseline scoped T=3 triplet завершён 2026-10-15. Evidence: `/nbody/runs/20261015_cdm_rotN1e6_T3_control_mpi10`, `/nbody/runs/20261015_sidm_s0p5_rotN1e6_T3_mpi10`, `/nbody/runs/20261015_dsidm_s0p5_f0p1_rotN1e6_T3_mpi10` — все `completed`, health=ok, t=3/3, 62/61 snapshots (дублирующий terminal snapshot при t=3), процессов нет, flags none. Анализ: `nbody/analysis/campaigns/rotN1e6_T3_triplet_20261015/` и canonical per-run metrics в `nbody/analysis/prerun/`. Вывод: c/a(r<5)=0.993–0.997 и z/R=0.706–0.707 остаются толстыми; диск не сформирован.

Полный анализ всех snapshots через canonical `read_state`/`bulk_velocity`/`potential_energy_from_block`: в каждом из трёх runs 62 HDF5 files, 61 unique time; дублированные snapshot_060/061 при t=3 усреднены для временного fit. Массово-взвешенная K в COM-frame: CDM −0.832%, SIDM −0.667%, dSIDM +0.482% от собственной K0. Нормируя каждый elastic control на K0, средний контроль к T=3 падает, а dSIDM K выше его на 1.241%; линейный fit relative excess растёт на 0.4493 pp/code-time (R²=.989), интервальные темпы 0.40/0.47/0.37 pp на t=0–1/1–2/2–3. Значит, наблюдаемого времени до заданной потери global K нет: она не падает.

В dSIDM W становится на 0.875% более отрицательной, raw E=K+W теряет 1.270% |E0| (≈1.32% после контроля drift), при этом Jz(all halo) меняется −0.016%; это согласуется с гравитационной конверсией W→K на фоне слабого охлаждения, а не с одноосевым глобальным K-провалом. `NInteractions` endpoint slope=40,151 particle-endpoint counts/code-time (R²=.99996), то есть ≈20,075 pair-event equivalents/code-time если each pair increments both endpoints; interval rates 19,946/20,022/20,269. Latest snapshot count=120,502; mean of duplicate t=3 snapshots=120,474 (~60,237 pair-event equivalents), 8.386% particles touched. Interacted subset carries 9.28% K, so 1/3 of that subset K≈3.09% global K — only a rough one-time scale, not measured loss/event. Cylindrical K_R/K,K_phi/K,K_z/K почти неизменны: (.3332,.3336,.3332)→(.3314,.3358,.3329). `D=.0513167019`, kick=0; source formula `(1-D)^2` implies ~10% relative pair KE/event, но source↔binary identity не доказана. Нельзя превращать это в 1/3 global-halo KE lost/event или экстраполировать ~23T на K: та оценка была для full mechanical |E|, не kinetic energy. Новых запусков/plots не делал.

Storage cleanup (approval m01872): in the 7 complete rotating N=1e6 T=1 runs retained one-based snapshot positions 1,20,40,60,80,101, mapped to `snapshot_000`, `_019`, `_039`, `_059`, `_079`, `_100`; removed the other 95 snapshots/run. Removed 160 restart files from those 7 plus the incomplete T=1 SIDM-2 run; preserved its only two snapshots `_000` and `_056`. Total unlinked 50.933 GiB; host root now has 54 GB free. Docker build cache untouched. Raw T=1 temporal HDF5 series are now sparse; old derived analysis remains separate.

Next: активный приоритет P-002 выбран пользователем m01909. Сначала завершить read-only evidence audit, затем по явному scope обновить существующий conference package; запускать новые production runs только после отдельного согласования точных параметров, IC, ресурсов и команд.

## Правила перехода

- Приоритет: текущий пользовательский запрос → PROJECT safety/scope → этот PLAN → ACTIVE checkpoint → MEMORY/evidence. При расхождении сначала reconcile, не выбирать удобную версию.
- Любой новый дорогой эксперимент/проектная цель сначала proposed с критериями и approval; самостоятельно дробить разрешённую задачу можно, расширять scope нельзя.
- P-001 закрыт после проверки миграции. Не удалять этот PLAN и открытые пункты ради упрощения.
