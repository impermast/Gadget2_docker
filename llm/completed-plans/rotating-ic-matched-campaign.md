# Completed plan — matched dSIDM dark-disk study

Status: historical plan; launch/inventory/literature steps below were completed 2026-10-13. It is not a current TODO or authorization. Four uncertain legacy cases were intentionally preserved, not resolved; current follow-up belongs to `llm/PLAN.md` P-004. Do not repeat runs, archival, deletion or Telegram actions from this document without fresh scope/approval. Outputs remain evidence; see linked reports under `llm/records/` and canonical `/nbody/` paths.

## Зафиксированные параметры и ограничения

- Текущая IC для новой matched-серии:
  `/nbody/ics/dwarf_rot_N1e6_lambda0035/dwarf_rot_N1e6_lambda0035.hdf5`.
- Входной физический параметр задаётся в литературной convention:
  `f_diss = 0.5`. Legacy GIZMO-код не менять. Для его текущего runtime
  параметра использовать преобразование
  `D_code = 1 - sqrt(1 - f_diss) = 0.2928932188`.
- `sigma/m = 0` — CDM-контроль, диссипация для него не действует;
  `sigma/m = 1` и `2 cm^2/g` — SIDM/dSIDM с тем же литературным `f_diss`.
- Для короткой начальной matched-серии приняты параметры предыдущей серии:
  `TimeMax=1`, `TimeBetSnapshot=0.01`, `MaxSizeTimestep=0.005`, 10 MPI;
  запуски последовательные, Telegram progress каждые 30 минут. Новые каталоги
  обязаны быть уникальными. Если позже меняется горизонт T, это отдельная
  версия серии, не resume поверх этих результатов.
- Никаких изменений `/opt`, удаления IC или перезаписи старых результатов.

## Шаг 0 — сначала запустить расчёты параллельно остальной работе

- [x] Preflight 2026-10-13: целевая IC существует; GIZMO/MPI-процессов нет;
  16 CPU, около 11 GiB доступной RAM и 48 GiB свободного места; три целевых
  каталога свободны.
- [x] Запуски выполнены последовательно через `/nbody/scripts/run_sim.sh`:
  исходный batch PID `21630`, исправленная попытка sigma=1 PID `31424`, после
  неё отдельно запущен sigma=2 (wrapper PID `39073`).
  - `20261013_cdm_rotN1e6_fdiss0p5_sigma0_T1_mpi10`
    — CDM, `sigma/m=0`;
  - `20261013_sidm_s1_fdiss0p5_rotN1e6_T1_mpi10`
    — `sigma/m=1`, `f_diss=0.5`, `D_code=0.2928932188`;
  - `20261013_sidm_s2_fdiss0p5_rotN1e6_T1_mpi10`
    — `sigma/m=2`, `f_diss=0.5`, `D_code=0.2928932188`.
- [x] Batch logs:
  `/nbody/runs/20261013_rotN1e6_fdiss0p5_sigma_scan_batch.log` (CDM + failed
  wrong-path attempts),
  `/nbody/runs/20261013_rotN1e6_fdiss0p5_sigma1_2_retry_batch.log` (SIDM-1),
  `/nbody/runs/20261013_rotN1e6_fdiss0p5_sigma2_retry.log` (SIDM-2).
  CDM: completed/ok, T=1, 101/101. SIDM-1: completed/ok, T=1, 101/101,
  no flags, `NInteractions=135610`, 7.22% particles interacted. The retry
  batch's physical gate falsely rejected SIDM-1 because `used-values` rounds
  D to 0.292893 while the gate demanded absolute tolerance 1e-8. Canonical JSON
  confirmed runtime D=0.2928932188 and all expected values; manual gate passed
  with tolerance 1e-6. SIDM-2 launched at 13:06 UTC then terminated at t=0.5659/1,
  57/101 snapshots. GIZMO ended with `No domain decomposition that stays within
  memory bounds is possible.` Wrapper rc=0/run.state COMPLETED do not mean it
  reached TimeMax; classify it as terminally incomplete numerical failure.
  Earlier health checks flagged `low-dt-timebins`/`timestep-collapse` with
  minimum Systemstep ~1.19e-7. Final NInteractions=2,147,508 (7.97%); no live
  process. Final checker health=ok is misleading, as it only sees final tail/state.
- [x] CDM и SIDM-1 завершились без pathology, несмотря на startup warning
  `MaxMemSize` (SIDM-1 safe-memory estimate `-313.289 MB`). SIDM-2 запущен
  только после завершения SIDM-1 и успешной проверки canonical gate. У SIGMA-2
  проверить terminal log; параллельные дополнительные задачи не запускать.
- [x] Для CDM и SIDM-1 проверены used-values и фактическая IC. SIDM-2
  preflight/runtime params подтверждают `sigma=2`, `D_code=0.2928932188`, kick=0,
  правильную IC, `T=1`, cadence=0.01 и max-step=0.005.
- [x] CDM и SIDM-1 физически завершены (T=1, 101/101, health=ok). SIDM-2
  физически не завершён: t=0.5659, 57/101; GIZMO сообщил о невозможности
  выполнить domain decomposition в пределах памяти. Не включать его как T=1
  результат, несмотря на wrapper rc=0/run.state COMPLETED.
- [x] Для SIDM-2 построены canonical series metrics и final-snapshot plots:
  `nbody/analysis/prerun/20261013_sidm_s2_fdiss0p5_rotN1e6_T1_mpi10/` и
  `nbody/analysis/core/20261013_sidm_s2_fdiss0p5_rotN1e6_T1_mpi10/`. Для matched
  интерпретации также построены series metrics SIDM-1.
- [x] Причина: при t=0.55→0.56 `NInteractions` вырос 213,730→2,147,508,
  max collisions per particle 35→2,472, а min systemstep упал
  `1.53e-5→2.38e-7` (в log встречались ~`4e-16`). В r<1 kpc плотность выросла
  примерно на 56%, тогда как r<5 — лишь на 3%; форма осталась сферичной
  (`c/a~0.998`, `z/R~0.707`, `|vrot|/sigma~0.339`). Локализованный центральный
  runaway с tiny timesteps привёл к невозможной memory-bounded domain
  decomposition. Это consistent with dissipation-driven central contraction,
  но core-resolution limit не позволяет утверждать, что runaway физический.

## Шаг 1 — архивировать патологические прогоны и освободить место

- [x] Пока очередь шага 0 считается, выполнен canonical read-only inventory
  46 run-каталогов с runtime params/logs, включая проверку статусов, health,
  фактического времени и снимков. Кроме активного нового CDM найдены: 1 старый
  остановленный CDM без pathology и 3 incomplete/unknown; все четыре результата
  сохранены для ручной проверки. Отдельно найден stale `RUNNING` state без
  процесса у старого SIDM, фактически дошедшего до T=5; каталог не менялся.
  Активная очередь, здоровые runs, IC и shared assets исключены из удаления.
- [x] Шесть старых терминальных патологических/сломанных прогонов сохранены в
  `/nbody/runs/pathological/<original-relative-path>/`; у каждого есть
  `run_summary.md` и `archive_manifest.json` с параметрами, IC, временем,
  coverage, health/причиной и размерами.
- [x] Сохранены runtime params/used-values, state, короткий log tail,
  существующие текстовые series summaries, последний snapshot и его SHA-256;
  restart-наборы и промежуточные snapshots не копировались.
- [x] Все шесть snapshots прошли checksum-сверку и `check_snapshot.py`; после
  этого удалены только соответствующие исходные run-каталоги. Сохранены
  manifests, snapshot checks и `nbody/runs/pathological/README.md`.
- [x] В inventory-README перечислены архивированные runs и объёмы. Исходные
  деревья: 8,795,032,448 bytes; snapshots в архиве: 108,059,376 bytes; net
  оценка освобождения: 8,686,973,072 bytes (~8.09 GiB). `df` после очистки:
  54 GiB доступны. Четыре неясных/неполных legacy случая оставлены.

## Шаг 2 — literature review допустимых параметров dark-disk formation

- [x] Поиск выполнен только по `arXiv.org` и рецензируемым журнальным статьям;
  блоги, форумы, популярные пересказы и документация кода как физические
  источники не использовались.
- [x] В `llm/records/dark-disk-literature-review.md` записаны article/arXiv/DOI
  ссылки и conventions; `f_diss` отделён от `D_code`.
- [x] Сведены FIRE I/II, DDDM, dark-sector cooling и atomic-DM analogues:
  cross-sections/velocity model, halo masses, particle/force resolution where
  reported, cosmological IC/spin limitations, formation epochs, component
  fractions, disk criteria and model limitations.
- [x] Вывод: литература не устанавливает универсальный порог `f_diss<0.5`.
  FIRE I получает rotation/oblate halos at high cross-section, но не thin dark
  disks; DDDM/ADM disks use subcomponents and microphysical cooling, not the
  same all-DM constant-cross-section model. FIRE II flags `f_diss*sigma/m`
  around `<=0.05 cm^2/g` for a specific bright-dwarf observational comparison;
  our sigma=1,2, f=0.5 runs are exploratory, not automatically preferred viable
  dwarf parameters. Full comparison and sources are in the literature report.

## Критерий завершения TODO

- Step 0: три параметрически matched run имеют проверенный физический статус.
- Step 1: confirmed broken runs archived, latest snapshots verified, source
  trees removed and space recovery recorded; four uncertain legacy runs remain
  deliberately preserved for review.
- Step 2: article-by-article review is saved at
  `llm/records/dark-disk-literature-review.md` with conventions and applicability.
