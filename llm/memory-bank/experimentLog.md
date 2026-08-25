# Experiment Log

Use this file to record completed or attempted simulations.

### 2026-08-25 git policy + fast test suite + CI auto-runs (infrastructure)

Goal:

- Безопасный git-workflow с ИИ-агентом и быстрая валидация кода анализа без запуска симуляций.

Type:

- Infrastructure (git policy, testing, CI) — не симуляция

What was done:

- Ветка `agent/dev` (единственная ветка агента), push agent/* разрешён, master защищён правилами.
- Шаблон коммитов `llm/gitmessage.txt` (RUN/TEST/RESULT), включён через git config.
- `.gitignore`: llm/ трекается в agent/dev; на master снимается при мерже (процедура в 02-workflow.md).
- Тесты: `tests/` по паттерну answer-testing yt — синтетическая HDF5-фикстура (`synth_snap.py`, однородный шар N=2000 seed=42), 22 юнит-теста математики loaders + 1 golden-тест против `tests/golden/values.json` (регенерация через `make_golden.py`).
- Автопрогон: pre-commit hook `githooks/pre-commit` + GitHub Actions `.github/workflows/tests.yml` (checkout@v5 / setup-python@v6, junit → markdown-таблица статистики в Step Summary через `.github/scripts/test_summary.py`).

Test:

- `pytest tests/ -q`: 23 passed (~0.25 s локально); CI runs #1, #2 — success (~15–17 s);
- failure-path проверен: ❌ FAILED + сообщение assertion корректно попадают в таблицу.

Status:

- completed

Notes:

- Полезные находки: `loaders.write_summary()` падает на снапшотах без датасета Masses; `shrink_center` статистически разбрасывает центр на ~1–2.5 kpc при N=2000 (не баг, природа алгоритма).
- PyPI напрямую недоступен с этой машины — ставить пакеты через зеркало tuna.

### 2026-08-24 dwarf_N1e6 series CDM/SIDM0.1/1/5 (IN PROGRESS)

Goal:

- Серия 4 прогонов на IC dwarf_N1e6 (V200=30, cc=15, N=1e6): CDM, SIDM σ=0.1, 1, 5; TimeMax=5, TimeBet=0.1, 10 MPI-процессов (hwthreads).

Type:

- SIDM/CDM production series + автоматический анализ + TG-репорт

Status:

- IN PROGRESS (запущена 2026-08-24 ~20:08 через run_series_dwarf.sh, nohup в контейнере)
- Оркестратор: nbody/scripts/run_series_dwarf.sh (промежуточные TG с ETA после каждого прогона, финальный анализ run_full_test × 4 + compare_runs 5 серий с sidm20 + TG-репорт с графиками)
- Ожидаемое суммарное время: ~20-26 ч
- Инцидент при первом запуске: OpenMPI не дал 10 слотов (8 физ. ядер); исправлено OMPI_MCA_hwloc_base_use_hwthreads_as_cpus=1; упавшие run-каталоги удалены, серия перезапущена. Также исправлен greedy --labels в compare_runs.py (позиционные ДО --labels).

### 2026-08-24 remove legacy analysis scripts, multi-run in registry

Goal:

- Полный вывод старых analysis/plotting скриптов: сводка и multi-run сравнение перенесены в plot_scripts, legacy-файлы удалены.

Type:

- Architecture cleanup (plotting layer)

What was done:

- loaders.py: +write_summary() (текстовая сводка дословно из analyze_final_snapshot.py), +rho_core в prepare_profile_data, +inner_log_slope.
- analysis_plots.py: +compare-plots в registry — density_compare, log_slope_compare, sigma_v_compare (multi-series, валидация каждой серии через base.validate_fields), core_density_vs_sigma. plotter.py: +коллекция COMPARE_PLOTS (registry = 10 plots).
- Новый compare_runs.py — CLI сравнения нескольких прогонов (замена compare_all.py и analyze_halo.py --cdm --sidm).
- run_full_test.py пишет summary_analysis.txt в Phase C.
- УДАЛЕНЫ: analyze_final_snapshot.py, analyze_halo.py, compare_all.py.
- run_sidm_batch.sh: post-processing переключен на compare_runs.py (bash -n OK).
- Не перенесённые niche-графики удалены вместе со скриптами: phase r-vr, surface density compare, projected grid, contour overlay, circularity, core density evolution(t) — добавляются в registry по мере необходимости.
- Обновлены: skills/make-plots/SKILL.md (+переустановка), memory-bank (techContext, activeContext, progress).

Test:

- run_full_test.py на sidm20_dwarf_N1e6_T5: ALL CHECKS PASSED (17.0s), +summary_analysis.txt;
- compare_runs.py на 5 реальных прогонах (cdm_N1e6 + sidm_sigma0.1/1/2/5_N1e6): 4 PNG в nbody/analyse/cdm_sidm_all за 6.2s;
- negative-валидация compare-plot'ов: серия без обязательного поля отклоняется с указанием plot.series[i] и поля.

Status:

- completed

### 2026-08-24 merge plot_config into PlotSettings (settings.py)

Goal:

- Устранение размазанной логики стиля: plot_config.py + PlotSettings -> один модуль.

Type:

- Architecture cleanup (plotting layer)

What was done:

- plot_config.py УДАЛЁН; всё его содержимое (COLORS, SIZES, LINE_STYLES/MARKERS, STYLE, setup/apply/save, rcParams-механика) перенесено в `plot_scripts/settings.py`. PlotSettings — публичный фасад, apply() использует локальный setup().
- Legacy-скрипты переключены на импорт из settings.py: analyze_halo.py, compare_all.py, analyze_final_snapshot.py (+ добавлен import sys где нужен).
- GRAPH3D из plot_config не переносился (был мёртвым после удаления make_3d_animation.py; 3D-defaults живут в PlotSettings.view_3d и default_config частиц).
- Обновлены: plot_scripts/README.md, skills/make-plots/SKILL.md (переустановлен), memory-bank/techContext.md.

Test:

- run_full_test.py: ALL CHECKS PASSED (17.4s);
- analyze_halo.py (single-run): exit 0, 3 PNG;
- analyze_final_snapshot.py: exit 0, 4 PNG + summary txt;
- compare_all.py: import OK.

Status:

- completed

### 2026-08-24 memory-bank + skill adaptation, legacy graphics cleanup

Goal:

- Адаптация memory-bank и skill `make-plots` под новую plotting-инфраструктуру; удаление старых чисто графических скриптов.

Type:

- Documentation + cleanup

What was done:

- `skills/make-plots/SKILL.md` полностью переписан под `plot_scripts/`: таблица registry (6 plots), протокол с introspection-first, one-shot команда run_full_test.py, примеры Python-кода, инструкция добавления нового plot, список legacy/удалённых файлов. Skills переустановлены через `skills/install.sh` в `~/.codex/skills/` и `~/.agents/skills/`.
- Memory-bank адаптирован: techContext (plot_config помечен legacy, раздел Removed), activeContext (пути visualization, убраны битые example_snap issues), progress (TODO обновлены).
- Удалены старые графические скрипты: `nbody/gadget_test/example_snap.py`, `example_snap3D.py` (glio), `ytvis.py`, `field_maker.py` (yt). Научные analysis-скрипты (analyze_halo, compare_all, analyze_final_snapshot, check_snapshot) сохранены.

Status:

- completed

### 2026-08-24 plotting-infrastructure-refactor

Goal:

- Переработка plotting-слоя: единая инфраструктура `nbody/scripts/plot_scripts/` (NbodyPlotter + registry + data contracts) вместо разрозненных скриптов.

Type:

- Architecture refactor + visualization (без изменения физической методологии)

What was done:

- Созданы: settings.py (RunPaths/SimulationInfo/PlotSettings), base.py (BasePlot + data contract validation), plotter.py (registry/describe/make_plot(s)), analysis_plots.py (density, log_slope, sigma_v, interactions_radial), animation_plots.py (particles_2d, particles_3d), loaders.py (математика перенесена дословно из analyze_final_snapshot.py / make_run_evolution.py), run_full_test.py.
- Удалены после успешного теста: `png_to_gif.py` (нерабочий — нет imageio), `make_run_evolution.py`, `make_3d_animation.py` (полностью заменены particles_2d/particles_3d).
- Обновлены: skills/make-plots/SKILL.md, skills/gizmo-sim/SKILL.md, memory-bank.

Test:

- run: `nbody/runs/sidm20_dwarf_N1e6_T5` (52 snapshots, σ=20, N=1e6)
- command: `docker exec gadget-gizmo python3 /nbody/scripts/plot_scripts/run_full_test.py --run-root /nbody/runs/sidm20_dwarf_N1e6_T5`
- результат: ALL CHECKS PASSED (16.3s); 4 PNG + 2 GIF (12 кадров каждый) в `plots/`; negative-validation тесты (4/4) прошли.

Status:

- completed

Notes:

- Расхождение COM vs shrinkage centering СОЗНАТЕЛЬНО не исправлялось (вне скоупа); новый loaders использует shrinkage как в analyze_final_snapshot.py.
- compare_all.py / analyze_halo.py / analyze_final_snapshot.py не тронуты (научный код + legacy entrypoints).

### 2026-08-24 sidm20_dwarf_N1e6_T5 (полный прогон σ=20 N=1e6 T=5 + NInteractions)

Goal:

- Полноценный SIDM-прогон σ=20 на карликовом гало (N=1e6, TimeMax=5) с прямым счётчиком столкновений NInteractions.

Type:

- SIDM production run + automated post-analysis

Input:

- IC: `/nbody/ics/dwarf_N1e6/dwarf_N1e6.hdf5` (1e6 частиц, GalIC cc=15, V200=30)
- Param: `nbody/runs/sidm20_dwarf_N1e6_T5/.gizmo_run.param` (σ=20, TimeMax=5, TimeBet=0.1)
- Config: `Config_cdm_sidm.sh` (DM_SIDM=8) + патч NInteractions (`nbody/patches/`)
- Цепочка: `auto_run_after_ics.sh` → GIZMO → `chain_analysis_after_sim.sh` → `analyze_final_snapshot.py`

Key parameters:

- particle number: 1 000 000
- SIDM cross-section: 20
- runtime: TimeMax=5 (~5 Gyr), 52 снапшота (000–051)
- wall time: ~19 часов (GalIC ~3 ч + GIZMO ~16 ч, 4 ядра)

Outputs:

- run dir: `nbody/runs/sidm20_dwarf_N1e6_T5/`
- snapshots: `output/snapshot_000..051.hdf5` (по 69 MB)
- logs: `run.log` (25 MB), `analysis.log`, `snapshot_check.txt`
- plots: `plots/01_density_profile.png`, `02_log_slope.png`, `03_sigma_v.png`, `04_ninteractions_radial.png`, `summary_analysis.txt`

Status:

- completed (GIZMO exit 0, «Final time=5 reached», анализ exit 0)

Notes:

- **NInteractions работает**: всего 8 147 390 рассеяний; 51.4% частиц взаимодействовали хотя бы раз (mean=15.9, median=13, max=94 на interacted).
- Радиальный профиль NI физически корректен: в ядре (r<1.3 kpc) 100% частиц, mean NI≈28; на r~9 kpc — 52%; за r>370 kpc — ~0.
- Core density (r<2 kpc): 2.65e-3; inner log-slope = **−0.14** (почти изотермическое ядро) — после правок анализа (shrinkage-центрирование, окно slope 0.25 dex, порог ≥3 бина).
- COM offset финального снапшота 1.5 kpc (эскаперы); в анализе используется shrinkage-центр.
- Полный анализ + эволюционная GIF собраны в `nbody/analyse/sidm20_N1e6_T5/` (README.md, analysis/, animation/evolution.gif 52 кадра).
- Новый скрипт `nbody/scripts/make_run_evolution.py` — эволюционные GIF по одному прогону (PIL вместо imageio, его в контейнере нет).


### 2026-08-24 single_run_check (тест навыка make-plots)

Goal:

- Проверить новый агентский навык make-plots на готовом прогоне sidm20_dwarf_N100k (без новой симуляции).

Type:

- Visualization

Input:

- Run dir: `nbody/runs/sidm20_dwarf_N100k/output` (21 снапшот, σ=20, N=100k)
- Script: `nbody/scripts/analyze_halo.py` (single-run mode, `--cdm <dir>`)

Commands:

```bash
docker exec gadget-gizmo bash -c "cd /nbody/scripts && python3 analyze_halo.py \
  --cdm /nbody/runs/sidm20_dwarf_N100k/output \
  --outdir /nbody/runs/sidm20_dwarf_N100k/plots/single_run_check"
```

Outputs:

- plots: `plots/single_run_check/01_surface_density.png`, `02_density_profile.png`, `03_log_slope.png`
- logs: `logs/analyze_single_run_check.log`

Status:

- completed

Notes:

- Навык make-plots прошёл полный цикл: выбор скрипта → инспекция аргументов → изолированная папка вывода (существующие `plots/sidm_*.png` не тронуты) → логирование → отчёт.
- В single-run режиме `summary.txt` не создаётся (он есть только в compare-режиме `--sidm`) — это ожидаемое поведение скрипта.
- Анализ выполнялся внутри контейнера `gadget-gizmo`: каталоги прогонов принадлежат root, хостовый пользователь писать в них не может.


### 2026-08-23 ninteractions_prototype_smoke (smoke-тест блока NInteractions)

Goal:

- Проверить, что добавление вывода NInteractions в снапшоты GIZMO работает (прототип).

Type:

- Smoke-test / prototype (правка ядра GIZMO)

Input:

- IC: `/nbody/ics/dwarf_N100k/dwarf_N100k.hdf5` (100000 частиц)
- Param: `/tmp/smoke.param` (σ=20, TimeMax=0.05/0.2)
- Config: `Config_cdm_sidm.sh` (DM_SIDM=8)

Правка GIZMO (воспроизводимые патчи в `nbody/patches/ninteract_{allvars,io}.patch`):

- В `allvars.h`: новый enum `IO_NINTERACTIONS` рядом с IO_POT.
- В `io.c` 6 мест: запись блока (через `unsigned long long* ip_ull`), размер (8 байт), datatype UINT64 (typekey=2), 1 элемент, все частицы (nall), включение при `#ifdef DM_SIDM`, имя "NInteractions" и label "NIN ".

Key results:

- snapshot_000 (t=0): NInteractions = 0 у всех 100000 частиц (корректно).
- snapshot_001 (t=0.05): сумма 7826, 5575 частиц ≥1 (5.6%), медиана 1, p90=2, макс 10 — реальный рост счётчика со временем.
- Дополние: это доказывает, что SIDM-модуль в предыдущих прогонах реально работал — просто счётчик не выводился.

Notes:

- Первый вариант (запись через `MyIDType`) давал мусор: `MyIDType` = unsigned int (4B) при !LONGIDS, а датасет был UINT64 (8B). Исправлено отдельным `unsigned long long*`.
- Сборка GIZMO успешна (make -j), backup исходников в `/opt/gizmo-public/.backup_ninteract_20260823/`.
- Полный прогон σ=20 N=1e6 T=5 отложен до подтверждения пользователя.

### 2026-08-23 cdm_sidm_all (анализ существующих прогонов, верификация SIDM)

Goal:

- Количественная валидация SIDM-модуля по уже готовым прогонам (без новых симуляций).

Type:

- Аналитический (сравнение CDM vs SIDM)

Input:

- N100k: `runs/cdm_dwarf_N100k` vs `runs/sidm20_dwarf_N100k` (σ=20, оба Time=2.0, 21 снапшот)
- N1e6: `runs/cdm_N1e6` vs `runs/sidm_sigma{0.1,1,2,5}_N1e6` (Time=5.0)
- Скрипт: `nbody/scripts/compare_all.py` (дополнен: чтение σ из заголовка снапшота, fallback на имя папки; rename edges→bins)

Key results:

- N1e6 inner log-slope: CDM −1.392 → σ0.1 −1.218 → σ1 −0.575 → σ2 −0.892 → σ5 −1.038 (тренд «больше σ → мягче ядро», core density ≈ const).
- N100k σ=20: slope −2.73…−2.97 (CDM) vs −2.80…−2.86 (σ20) — смягчение лишь ~0.1; core density r<2 растёт +7% (1.855e-3→1.991e-3); σ_vel почти совпадает.

Notes:

- NInteractions отсутствует во ВСЕХ снапшотах (и N100k, и N1e6) — прямого счётчика столкновений нет, только косвенные признаки.
- В N100k при Time=2.0 эффект SIDM слабый из-за малого времени релаксации (ядро ещё формируется, центр может подрасти до провала). Для полного core formation нужен TimeMax≈10.
- Output: `nbody/analyse/cdm_sidm_all/{N100k,N1e6}/` (01..07 PNG + summary.txt). Воспроизводимость N1e6 совпадает со старым `cdm_sidm_comparison/summary.txt`.

### 2026-07-24 sidm20_dwarf_N100k (верификация 2026-08-21)

Goal:

- Последний тест SIDM (σ=20) на карлике N=100k; проверка завершённости и адекватности модуля SIDM.

Type:

- SIDM

Input:

- IC file: `/nbody/ics/dwarf_N100k/dwarf_N100k.hdf5` (100000 частиц, PartType3, v200=30, c=15)
- parameter file: `nbody/runs/sidm20_dwarf_N100k/.gizmo_run.param` (DM_InteractionCrossSection=20)
- config: `nbody/runs/sidm20_dwarf_N100k/configs/Config.sh` (DM_SIDM=8, OUTPUT_POTENTIAL, EVALPOTENTIAL)
- run: `mpirun --allow-run-as-root -np 4 /opt/gizmo-public/GIZMO .gizmo_run.param`

Key parameters:

- particle number: 100000
- SIDM cross-section: 20 (упругая velocity-independent модель: DM_KickPerCollision=0, DM_DissipationFactor=0, DM_InteractionVelocityScale=0)
- runtime: TimeMax=2 (~2 Gyr), TimeBetSnapshot=0.1
- softening: SofteningHalo=0.05; units: kpc, 1e10 Msun, km/s

Outputs:

- output directory: `nbody/runs/sidm20_dwarf_N100k/output/`
- snapshots: `snapshot_000.hdf5`..`snapshot_020.hdf5` (21 шт), restart.0-3
- logs: `run.log`, `output/cpu.txt`, `snapshot_check.txt`
- plots: `plots/sidm_vs_cdm.png`, `plots/sidm_differences.png`, `plots/sidm_evolution.png`

Status:

- completed (дошёл до конца: `Final time=2 reached. Simulation ends.`)

Notes (верификация 2026-08-21):

- Тест достиг TimeMax=2, записан 21-й снапшот; ошибок/крахов нет.
- SIDM-модуль реален/активен: билд с `DM_SIDM=8`, AGS-цикл исполнялся каждый шаг; в cpu.txt `ags-nongas` = 82% времени (2556 c из 3119 c), `agsdensity` = 70.8%.
- CDM-контроль (cdm_dwarf_N100k) корректен: SIDM-теги игнорируются, AGS отсутствует.
- 6 HDF5-DIAG предупреждений безобидны: в single-precision IC нет атрибута `Flag_DoublePrecision`.
- Замечание: в снапшоты НЕ пишется `NInteractions` — нет прямого счётчика числа столкновений в выводе.
- Замечание: `snapshot_check.txt` даёт r_max=7619 (далёкие эскаблеры), r_med=9.6, v_med=28.3 — структура гало на месте.
- Косвенно модуль даёт ожидаемый физический эффект: для N1e6-прогонов (см. `nbody/analyse/cdm_sidm_comparison/summary.txt`) inner slope ядра смягчается (CDM −1.392 → σ=1: −0.575), при этом core density почти не меняется.
- `run_sidm20.sh` в HEAD настроен на N=1e6 (dwarf_N1e6); фактический прогон был с N=100k (dwarf_N100k).

### 2026-06-16 test_sidm_quick

Goal:

- Quick functional test of GIZMO SIDM workflow in Docker container.

Type:

- SIDM

Input:

- IC file: `/nbody/gizmo_test/halo_10000_sidm_ic` (10000 particles, pre-converted to PartType3)
- parameter file: `nbody/runs/test_sidm_quick/gizmo_sidm.param`
- config file: `nbody/runs/test_sidm_quick/Config_cdm_sidm.sh` (DM_SIDM=8)
- run script: manual `mpirun` via `docker exec`

Key parameters:

- particle number: 10000
- SIDM cross-section: 10 (DM_InteractionCrossSection)
- runtime: TimeMax=0.1
- output cadence: TimeBetSnapshot=0.1
- seed: N/A (default)

Commands:

```bash
cd /nbody/runs/test_sidm_quick
cp Config_cdm_sidm.sh /opt/gizmo-public/Config.sh
cd /opt/gizmo-public
make clean && make -j$(nproc)
cd /nbody/runs/test_sidm_quick
cp gizmo_sidm.param .gizmo_run.param
sed -i 's|^OutputDir.*|OutputDir  /nbody/runs/test_sidm_quick/output_test_sidm/|' .gizmo_run.param
mpirun --allow-run-as-root -np 4 /opt/gizmo-public/GIZMO .gizmo_run.param
```

Outputs:

- output directory: `nbody/runs/test_sidm_quick/output_test_sidm/`
- snapshots: `snapshot_000.hdf5` (initial), `snapshot_001.hdf5` (final, t=0.1)
- logs: inline in terminal (captured to /tmp/cline/large-output-*)
- plots: not yet generated

Status:

- completed

Notes:

- GIZMO built successfully with DM_SIDM=8, EVALPOTENTIAL, OUTPUT_POTENTIAL.
- No hydro or cooling modules enabled, only N-body.
- Many ignored param tags are expected (they belong to disabled modules).
- Run took ~2 minutes wall time.
- Snapshot files are ~635 KB each (HDF5, single precision).
- Work-load balance was good (gravity balance ~1.01–1.03).

## Template

### YYYY-MM-DD run_name

Goal:

- ...

Type:

- CDM / SIDM / GalIC IC generation / visualization / debugging

Input:

- IC file:
- parameter file:
- config file:
- run script:

Key parameters:

- particle number:
- SIDM cross-section:
- runtime:
- output cadence:
- seed:

Commands:

```bash
...
```

Outputs:

- output directory:
- snapshots:
- plots:
- logs:

Status:

- completed / failed / interrupted

Notes:

- ...