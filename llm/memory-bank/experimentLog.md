### 2026-09-11 spin-k08 sigma2p5 dissipation scan completed

Goal:

- Проверить, остались ли dSIDM кандидаты из очереди `/nbody/runs/dsidm_spin_k08_transition/` (запущена 2026-09-04, всё досчиталось за ~1h45m).

Type:

- Completed-run verification + partial-series diagnostics; no new simulations launched.

Queue (последовательная, sigma=2.5, k=0.8, T=2, 21/21 snapshots каждый):

- `cdm_N1e5_T2`: NI=0 (control, completed/ok).
- `sidm_s2p5_N1e5_T2`: NI=1910 (1.76%) (elastic control, completed/ok).
- `dsidm_s2p5_D0p10_N1e5_T2`: NI=2018, min c/a(r<5)=0.816, max |vrot|/sig=0.404 (изначальный spin, далее ~0.1), stable (1042 sync).
- `dsidm_s2p5_D0p25_N1e5_T2`: NI=2164, min c/a=0.816, stable (1042 sync).
- `dsidm_s2p5_D0p50_N1e5_T2`: NI=2672, min c/a=0.814, min Systemstep=0.000977, stable (1262 sync).
- `dsidm_s2p5_D0p75_N1e5_T2`: **pathological**: 553,610 sync-points, run.log=890MB, min Systemstep=4.77e-07, dNI=12,517,756 (взрыв при t=1.8-2.0), c/a min=0.814. Verdict: `no-disk-before-pathology`.

Result:

- При k=0.8 и sigma=2.5 диссипация до D=0.50 стабильна, но не даёт диска: c/a не ниже ~0.81, вращательная поддержка не растёт. D=0.75 даёт runaway до дискообразования — паттерн повторяет прежние dissipation-сканы (стабильно-толсто/сфероидально vs патология при сильной диссипации).

Status:

- completed-verification; next scientific step (needs approval): sigma scan around 2.5 or higher-k IC check before reruns.

### 2026-09-04 dsidm spin-k08 queued sigma2p5 dissipation scan

Goal:

- Пока пользователь отошёл на 4–5 часов, запустить последовательную очередь dSIDM кандидатов в campaign `/nbody/runs/dsidm_spin_k08_transition/` после успешных CDM/SIDM controls.

Type:

- Sequential simulation queue launched; not parallel, to avoid oversubscribing CPU/MPI.

Queue:

- `dsidm_s2p5_D0p10_N1e5_T2`: `sigma=2.5`, `D=0.10`, `kick=0`, `T=2`.
- `dsidm_s2p5_D0p25_N1e5_T2`: `sigma=2.5`, `D=0.25`, `kick=0`, `T=2`.
- `dsidm_s2p5_D0p50_N1e5_T2`: `sigma=2.5`, `D=0.50`, `kick=0`, `T=2`.
- `dsidm_s2p5_D0p75_N1e5_T2`: `sigma=2.5`, `D=0.75`, `kick=0`, `T=2`.

IC:

- `/nbody/ics/dwarf_rot_N1e5/dwarf_rot_N1e5_k08.hdf5`.

Logs:

- `/nbody/runs/dsidm_spin_k08_transition/queue_dsidm_s2p5_20260904.log`.
- `/nbody/runs/dsidm_spin_k08_transition/queue_dsidm_s2p5_20260904.nohup.log`.

Status:

- launched; queue stops on first failed run due to `set -euo pipefail`.

### 2026-09-04 dsidm spin-k08 campaign setup

Goal:

- Зафиксировать naming/grouping convention для новых research campaigns и подготовить `k=0.8` IC для spin-assisted dSIDM transition study.

Type:

- Campaign setup + derived IC generation; simulations were not launched.

What was done:

- Created `/nbody/runs/dsidm_spin_k08_transition/README.md` with scientific question, naming convention, control reuse policy, initial run sequence, candidate criteria, and classification labels.
- Generated derived IC `/nbody/ics/dwarf_rot_N1e5/dwarf_rot_N1e5_k08.hdf5` from `/nbody/ics/dwarf_rot_N1e5/dwarf_rot_N1e5.hdf5` using `add_halo_rotation.py --k 0.8 --ptype 3`.
- Checked that no existing run references `dwarf_rot_N1e5_k08`, so `CDM_k08` control is not yet available for reuse.

Result:

- Campaign setup complete; next step is to present the first control run plan `dsidm_spin_k08_transition/cdm_N1e5_T2` and wait for user approval before launching.

Status:

- completed setup; no science run launched

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

### 2026-08-28 dissipation matrix test (Phase 0-1, IN PROGRESS)

Goal:

- Тестовое показательное исследование: качественная и количественная разница CDM / SIDM / dSIDM (диссипативный SIDM) с вращающимся гало — проверка формирования тёмного диска.
- Группировка runs в подпапках: `runs/<set>/<run>` (конвенция зафиксирована).

Type:

- Test production matrix (N=1e5, T=2 Gyr) + plotting pipeline extension

Status:

- IN PROGRESS (запущена 2026-08-28 08:45, оркестратор `nbody/scripts/run_matrix_dissipation.sh`)

Physics:

- GIZMO нативный `DM_DissipationFactor` (патч DM_DissipationFactor в .param, в работает: f=1 → sticky DM, 0.5·dV kick). `GRAIN_COLLISIONS` НЕ определён — активен `sidm_core.c`, не grain.
- Вращение: GalIC `TypeOfHaloVelocityStructure=2` с `HaloStreamingVelocityParameter=0.5` НЕ сработал (чистое гало без диска не вращается). Вместо этого — новый `add_halo_rotation.py`: накладывает k·v_circ(r) из rotcurve.txt (⟨v_φ⟩ = −17…−21 км/с, J_z = ровно 0.5 круговой поддержки). IC: `dwarf_rot_N1e5/dwarf_rot_N1e5_k05.hdf5`.

Matrix (12 runs, N=1e5, T=2, TimeBet=0.1, 10 procs, в `runs/test_dissipation/`):

| Run | σ | f | |
|---|---|---|---|
| dsidm10_f1 (тестовый, первым) | 10 | 1.0 | физ-проверка до серии |
| cdm_N1e5_T2 | 0 | — | базовый |
| sidm{0.1,1,5,10}_N1e5_T2 | 0.1/1/5/10 | 0 | упругая ветка |
| dsidm{1,5,10}_f1 + _f05 | 1/5/10 | 1.0 / 0.5 | диссипативная сетка |
| dsidm0.1_f001 | 0.1 | 0.01 | валидция: CDM ≈ SIDM ≈ dSIDM при почти неизменной физике |

Pipeline updates:

- `generate_ics.sh`: +`galic_extra` (JSON → sed в param).
- `run_sim.sh`: +`--dissipation <f>`, вложенные --name (`set/run`).
- plot_scripts: +`disk_edgeon` plot (x-z карта плотности), `prepare_particle_snapshot()`, registry = 13 plots.
- Новые скрипты: `add_halo_rotation.py`, `run_matrix_dissipation.sh`.
- Физ-чек тестового прогона: 21 снапшот, NI>0, J_z дрейф <2%, edge-on сплюснутость.

Status:

- протестирована инфраструктура (Phase 0 complete), матрица запущена



Update 2026-08-28 (partial-series diagnostic):

- `dsidm10_f05_k15_N1e5_T2` stopped manually at pathological state, without deleting outputs: Time≈0.941/2, 10 snapshots, Sync-Point≈1.38M, Systemstep≈5.96e-08..1.19e-07.
- Added reusable checker `/nbody/scripts/check_simulations/analyze_series.py`; output for this run: `/nbody/runs/test_dissipation/dsidm10_f05_k15_N1e5_T2/partial_analysis/`.
- Quantitative verdict from `summary_partial_series.txt`: `no-disk-before-pathology` over snapshots 0..9 (t=0..0.9); min c/a(r<5)=0.831, rho_core(r<2) growth=0.459, ΔNI=59,449,572, max |vrot|/sigma(r<5)=0.257, min positive Systemstep=1.19e-07.
- Interpretation: σ=10, f=0.5, kick=15 produces enormous interaction growth and timestep pathology before clear disk-like flattening; not a stable dark-disk parameter point.

Update 2026-08-28 (soft dSIDM rerun launched):

- User requested a softer follow-up with analysis and Telegram notification on completion.
- Intended run `test_dissipation/dsidm5_f005_k0_N1e5_T2` with 10 MPI processes failed before simulation start because OpenMPI reported insufficient slots; this folder is a failed launch artifact, not a physics result.
- Working run launched instead as `/nbody/runs/test_dissipation/dsidm5_f005_k0_N1e5_T2_np4/` with `--mpi-procs 4`, IC `/nbody/ics/dwarf_rot_N1e5/dwarf_rot_N1e5_k05`, `sigma=5`, `DM_DissipationFactor=0.05`, `DM_KickPerCollision=0`, `TimeMax=2`, `TimeBetSnapshot=0.1`.
- Telegram is enabled by `run_sim.sh` because `/nbody/tg/telegram.conf` exists, but the first START send returned `TG: ошибка отправки START`; final TG reporting is also scheduled through `check_run.py --format tg` and may depend on the same TG configuration/network.
- Post-run monitor installed from host (`/tmp/monitor_dsidm5_f005_k0_np4.sh`, PID recorded by process table) to wait for the run to end, then write `check_after_finish.txt/json`; if completed+ok, run `/nbody/scripts/plot_scripts/run_full_test.py`; otherwise run `/nbody/scripts/check_simulations/analyze_series.py`; finally write `check_after_finish_tg.txt` via `--format tg`.
- Initial `check-run`: running/ok, by t≈0.336/2 (16.8%), 4/21 snapshots, latest `snapshot_003.hdf5`, `Systemstep=0.00195312`, `NInteractions=2402` affecting 2.26% particles, no pathology flags.

Update 2026-08-28 (soft dSIDM completed + final analysis):

- `/nbody/runs/test_dissipation/dsidm5_f005_k0_N1e5_T2_np4/` completed normally: `Time=2/2`, 21/21 snapshots, latest `snapshot_020.hdf5`, `Sync-Point=1048`, `Systemstep=0.00195312`, no pathology flags.
- Final SIDM counters: `NInteractions=5194`, interacted particles `4208/100000` (4.21%), per-interacted mean=1.23, median=1, p90=2, max=6.
- Final single-run analysis succeeded via `plot_scripts/run_full_test.py` (`ALL CHECKS PASSED in 13.9s`), outputs in `/nbody/runs/test_dissipation/dsidm5_f005_k0_N1e5_T2_np4/plots/`: density, log_slope, sigma_v, interactions_radial, disk_edgeon, 2D/3D GIFs, `summary_analysis.txt`.
- Summary metrics: core density r<2 = `6.5441e-04`, inner log-slope median first bins = `-0.614`, COM=(-4.302,-3.158,-0.965), shrink-center=(-7.630,-2.621,-0.268).
- TG-format completion report regenerated after stopping stale monitor: `check_after_finish_tg.txt` says completed/ok; command exit code 0.

Update 2026-08-28 (initial dissipation grid revised after smoke tests):

- Updated `/nbody/scripts/run_matrix_dissipation.sh` from the old 3-run mini-block (`CDM`, `SIDM σ=10`, pathological `dSIDM σ=10,f=0.5,kick=15`) to a 7-run smoke-calibrated initial grid.
- New grid: `cdm_N1e5_T2`, `sidm5_N1e5_T2`, `sidm10_N1e5_T2`, `dsidm5_f005_k0_N1e5_T2`, `dsidm10_f005_k0_N1e5_T2`, `dsidm10_f01_k0_N1e5_T2`, `dsidm10_f02_k0_N1e5_T2`.
- Rationale: smoke `dsidm5_f005_k0_N1e5_T2_np4` is stable but too weak to form a clear disk; old `dsidm10_f05_k15_N1e5_T2` is pathological. The revised grid removes `kick=15`, keeps `kick=0`, and scans moderate dissipation around σ=10.
- Safety fix: removed automatic `rm -rf` cleanup from the matrix script; it now aborts if a target run directory already exists. Manual cleanup candidates are listed separately and require explicit approval before deletion.

Update 2026-08-28 (sigma=1 grid extension + cleanup):

- Extended `/nbody/scripts/run_matrix_dissipation.sh` with σ=1 points: `sidm1_N1e5_T2`, `dsidm1_f005_k0_N1e5_T2`, `dsidm1_f01_k0_N1e5_T2`, `dsidm1_f02_k0_N1e5_T2`.
- Current grid now has 11 runs: CDM; elastic SIDM σ=1/5/10; dSIDM σ=1 with f=0.05/0.1/0.2; dSIDM σ=5,f=0.05; dSIDM σ=10 with f=0.05/0.1/0.2; all dSIDM use `kick=0`.
- User-approved cleanup policy for `/nbody/runs/test_dissipation/`: keep successful smoke `dsidm5_f005_k0_N1e5_T2_np4`, pathological reference `dsidm10_f05_k15_N1e5_T2`, and SIDM baseline `sidm10_N1e5_T2`; remove failed launch/log leftovers.

Update 2026-08-28 (launch revised grid with PROCS=8):

- Updated `/nbody/scripts/run_matrix_dissipation.sh`: default `PROCS=${PROCS:-8}` and `GROUP=${GROUP:-test_dissipation}` so matrix runs can be launched in a fresh group without touching preserved reference runs.
- Launched group: `/nbody/runs/test_dissipation_grid_sigma1/`, command `GROUP=test_dissipation_grid_sigma1 PROCS=8 bash /nbody/scripts/run_matrix_dissipation.sh`, background launcher log `/nbody/runs/test_dissipation_grid_sigma1.launcher.log`.
- Initial check: first run `cdm_N1e5_T2` is running/ok on 8 MPI processes; block compare is not ready until all 11 runs complete and pass health checks.

Update 2026-08-28 (old run cleanup/grouping):

- Created grouped production series directory `/nbody/runs/sidm_dwarf_N1e6_T5/` and moved into it: `cdm_dwarf_N1e6_T5`, `sidm0.1_dwarf_N1e6_T5`, `sidm1_dwarf_N1e6_T5`, `sidm5_dwarf_N1e6_T5`, `sidm20_dwarf_N1e6_T5`.
- Deleted user-approved oversized legacy run `/nbody/runs/cdm_N1e6/` (~31G, old IC/cadence with 502 snapshots).
- Current grouped production series size: ~22G. Active dissipation matrix `/nbody/runs/test_dissipation_grid_sigma1/` was left running.

Update 2026-08-28 (archive grouping, no deletion):

- Moved legacy SIDM comparison runs into `/nbody/runs/archive/legacy_cdm_sidm_N1e6/`: `sidm_sigma0.1_N1e6`, `sidm_sigma1_N1e6`, `sidm_sigma2_N1e6`, `sidm_sigma5_N1e6`.
- Moved old small tests into `/nbody/runs/archive/test_sidm/`: `test_sidm_auto`, `test_sidm_auto2`, `cdm_dwarf_N100k`, `sidm20_dwarf_N100k`.
- Moved old top-level logs into `/nbody/runs/archive/logs/`: `batch.log`, `series_dwarf.log`.
- Top-level `nbody/runs/` now contains only `archive/`, `sidm_dwarf_N1e6_T5/`, `test_dissipation/`, active `test_dissipation_grid_sigma1/`, and its launcher log.

### 2026-08-26 add log_rho_compare + rot_curve_compare (delta subplot)

Goal:

- Новые коллективные compare-графики CDM vs SIDM с нижним сабплотом разностей относительно CDM.

Type:

- Plotting pipeline extension (registry)

What was done:

- loaders.prepare_profile_data: +v_circ (rot curve) = sqrt(G_code·M(<r)/r), G_code=43009.17 (ед. GIZMO: кпк, 1e10 Msun, км/с).
- analysis_plots.py: +_DeltaComparePlot (shared helper: 2 сабплота sharex, верх — значения по σ, низ — Δ от базовой серии; интерполяция на общую сетку в log10 r; baseline = первая серия или config['baseline_label']).
- +LogRhoComparePlot (log_rho_compare: верх log ρ(r), низ Δlog10ρ vs CDM), +RotCurveComparePlot (rot_curve_compare: верх v_circ, низ Δv vs CDM). Зарегистрированы в COMPARE_PLOT_CLASSES; COMPARE_PLOTS += 2 (registry = 12 plots).
- compare_runs.py: все profile-plot'ы кроме core_density_vs_sigma строятся из одних series (лог ρ и rot curve включены автоматически).
- Обновлены: skills/make-plots/SKILL.md (+переустановка), memory-bank/techContext.md.

Test:

- compare_runs на 5 сериях dwarf (CDM/0.1/1/5/20): + log_rho_compare.png (216k), rot_curve_compare.png (253k) в nbody/analyse/dwarf_series/; структура подтверждена программно (2 оси, 5 серий верх, Δ+нулевая линия внизу).
- negative: серия без rho/v_circ → "log_rho_compare.series[0]: missing required field ...".
- run_full_test на sidm5_dwarf_N1e6_T5: ALL CHECKS PASSED (однопрогоночный pipeline цел).
- v_circ (пример r=0.37 kpc): CDM 22.9 km/s, SIDM20 20.2 km/s — физически согласовано.

Status:

- completed

### 2026-08-24 dwarf_N1e6 series CDM/SIDM0.1/1/5 (completed)

Goal:

- Серия 4 прогонов на IC dwarf_N1e6 (V200=30, cc=15, N=1e6): CDM, SIDM σ=0.1, 1, 5; TimeMax=5, TimeBet=0.1, 10 MPI-процессов (hwthreads).

Type:

- SIDM/CDM production series + автоматический анализ + TG-репорт

Key parameters:

- IC: `/nbody/ics/dwarf_N1e6/dwarf_N1e6` (1e6 частиц, GalIC V200=30, cc=15)
- TimeMax=5, TimeBet=0.1 → 52 снапшота (000–051) на прогон
- 10 MPI-процессов (8 физ. ядер + 2 HT), OMPI_MCA_hwloc_base_use_hwthreads_as_cpus=1
- Оркестратор: `nbody/scripts/run_series_dwarf.sh` (промежуточные TG-уведомления с ETA между прогонами, финальный анализ + TG-репорт с графиками)

Results (финальные снапшоты, t=5):

| Прогон | Wall time | NInteractions total | interacted | ρ_core (r<2 kpc) | inner slope |
|--------|-----------|--------------------:|-----------:|------------------:|------------:|
| cdm_dwarf_N1e6_T5 | 9ч 33м | 0 | 0% | 2.196e-3 | −0.360 |
| sidm0.1_dwarf_N1e6_T5 | 11ч 14м | 39 428 | 3.43% | 2.201e-3 | −0.428 |
| sidm1_dwarf_N1e6_T5 | 11ч 20м | 367 146 | 17.95% | 2.253e-3 | +0.350 |
| sidm5_dwarf_N1e6_T5 | 11ч 19м | 1 785 910 | 36.25% | 2.395e-3 | +0.077 |

Выводы:

- Тренд «больше σ → выше ρ_core и больше рассеяний» подтверждён на dwarf-IC, величины монотонны.
- Для σ=1 slope меняет знак (−→+): формирование ядра уже заметно; σ=5 и выше — выраженное ядро.
- σ=0.1 почти неотличим от CDM (нижний предел сетки), как и ожидалось из оценки.
- Сравнение 5 серий (CDM/0.1/1/5/20, включая готовый sidm20_dwarf_N1e6_T5): `nbody/analyse/dwarf_series/` — density/log_slope/sigma_v_compare + log_rho_compare + rot_curve_compare + core_density_vs_sigma.
- Графики каждого прогона: `nbody/runs/<run>/plots/` (4 PNG + 2 GIF + summary).

Status:

- completed (серия завершена 2026-08-26 ~15:37, SERIES COMPLETE analyze_fail=0)

Notes:

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
### 2026-09-03 dSIDM T=2 grid cleanup + shape/thickness diagnostics

Goal:

- Завершить анализ T=2 dissipation grid и подготовить надёжный критерий выбора следующего focused T=5 эксперимента.

Type:

- Completed-run analysis + analysis tooling

Run/data:

- Group: `nbody/runs/test_dissipation_grid_sigma1/`
- IC: `/nbody/ics/dwarf_rot_N1e5/dwarf_rot_N1e5_k05.hdf5`
- Matrix: CDM; SIDM σ=1/5/10; dSIDM σ=1,f=0.05/0.1/0.2,k=0; dSIDM σ=5,f=0.05,k=0; dSIDM σ=10,f=0.05/0.1/0.2,k=0.

What was done:

- Pathological run `dsidm10_f02_k0_N1e5_T2` was removed after timestep-collapse (`low-dt-timebins`, `timestep-collapse`).
- `run_full_test.py` completed for the remaining 10 runs and produced per-run `plots/summary_analysis.txt` and plots.
- Added reusable group comparison tool `nbody/scripts/check_simulations/compare_shape_series.py` to aggregate `analyze_series.py` CSV outputs without reopening snapshots.
- Hardened `analyze_series.py` log-scale plotting for zero-only series (e.g. CDM NInteractions).
- Tested `analyze_series.py` on 5 key T=2 runs: CDM, SIDM10, dSIDM5 f=0.05, dSIDM10 f=0.05, dSIDM10 f=0.1.
- Generated group shape/thickness comparison in `nbody/runs/test_dissipation_grid_sigma1/shape_compare/`.

Key result:

- No T=2 dark-disk signature in shape/thickness metrics: final `c/a(r<5)≈0.937–0.950`, `z_rms/R_rms(r<5)≈0.668–0.679`, `|vrot|/sigma(r<5)≈0.064–0.072`; all disk scores are 0.
- dSIDM σ=10,f=0.1 has the largest NI among tested stable candidates (`NI=11618`) but no geometric disk signature by T=2.

Status:

- completed; result supports moving to focused longer T=5 runs rather than broadening T=2 parameter sampling.
