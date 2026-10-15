# REGISTRY — каталог графиков (СГЕНЕРИРОВАНО, НЕ РЕДАКТИРОВАТЬ ВРУЧНУЮ)

Источник: `nbody/scripts/analysis/registry.py` + `plots/*.py`.
Перегенерировать: `python3 /nbody/scripts/analysis/runners/registry_docs.py`.

Как пользоваться (для ИИ-агента):

1. Найди график по блоку/смыслу в таблицах ниже — код читать не нужно.
2. Возьми `runner` и `inputs`: это готовый CLI.
3. Доступные настройки графика — в колонке `config keys`.
4. Внутри блока runner может отличаться (см. `runner` у plot'а); любой runner принимает `--plots a,b,c` для подмножества.

Всего графиков: **26**; блоки: `ic` (1), `prerun` (4), `core` (7), `campaigns` (14), `presentations` (0)

## Блок `ic`

IC — начальные условия (GalIC): target-профиль, гейт разрешения каспа

| plot | что показывает | данные | вход | выходной файл |
|---|---|---|---|---|
| `ic_gate_profile` | IC-gate: измеренный профиль vs NFW-target + наклон + разрешение | prepare_ic_figure_data | ic | `ic_gate_profile.png` |

### `ic_gate_profile`

- **runner:** `runners/make_ic_plots.py`
- **inputs:** ic
- **config keys:** dpi, figsize, gate_range, nmin, title


## Блок `prerun`

PRERUN — ранние снапшоты: гейт первых шагов, диагностика серии

| plot | что показывает | данные | вход | выходной файл |
|---|---|---|---|---|
| `contact_sheet` | Contact-sheet серии: face-on/edge-on кадры по снапшотам | prepare_series_frames | run | `contact_{plane}.png` |
| `early_cusp_compare` | Ранний гейт: IC vs snapshot vs target + сохранение каспа | prepare_early_figure_data | run | `early_cusp_compare.png` |
| `series_evolution` | Эволюция серии: плотность ядра, форма, NI по времени | metrics_series.csv | run | `series_evolution.png` |
| `shape_panel` | Сравнение shape-серий группы: 5 панелей по времени | metrics_series.csv (группа) | runs | `shape_panel_{key}.png` |

### `contact_sheet`

- **runner:** `runners/make_prerun_plots.py`
- **inputs:** run
- **config keys:** bins, cmap, dpi, min_lim, percentile, plane, title

### `early_cusp_compare`

- **runner:** `runners/make_prerun_plots.py`
- **inputs:** run
- **config keys:** dpi, figsize, gate_range, title

### `series_evolution`

- **runner:** `runners/make_prerun_plots.py`
- **inputs:** run
- **config keys:** dpi, figsize, title

### `shape_panel`

- **runner:** `runners/make_prerun_plots.py`
- **inputs:** runs
- **config keys:** dpi, figsize, title


## Блок `core`

CORE — один production-прогон: профили, карты, анимации

| plot | что показывает | данные | вход | выходной файл |
|---|---|---|---|---|
| `density` | Профиль плотности rho(r) одного прогона (unresolved-зона заштрихована) | prepare_profile_data | run | `01_density_profile.png` |
| `disk_edgeon` | Проекция плотности edge-on одного прогона | prepare_particle_snapshot | run | `disk_edgeon.png` |
| `interactions_radial` | Радиальный профиль NInteractions (только SIDM; у CDM пусто) | prepare_profile_data | run | `04_ninteractions_radial.png` |
| `log_slope` | Локальный наклон dlnrho/dlnr одного прогона, опора NFW -1 | prepare_profile_data | run | `02_log_slope.png` |
| `particles_2d` | Анимация проекции плотности xy по серии снапшотов (GIF) | prepare_series | run | `evolution_2d.gif` |
| `particles_3d` | Анимация 3D-разлёта частиц по серии снапшотов (GIF) | prepare_series | run | `evolution_3d.gif` |
| `sigma_v` | Профиль дисперсии скоростей sigma_v(r) одного прогона | prepare_profile_data | run | `03_sigma_v.png` |

### `density`

- **runner:** `runners/make_run_plots.py`
- **inputs:** run
- **config keys:** color_index, dpi, figsize_key, line_width, title, unresolved_label, unresolved_r_max, xlabel, xlim, xscale, ylabel, ylim, yscale

### `disk_edgeon`

- **runner:** `runners/make_run_plots.py`
- **inputs:** run
- **config keys:** bins, cmap, dpi, figsize_key, lim, min_lim, percentile, title, xlabel, ylabel

### `interactions_radial`

- **runner:** `runners/make_run_plots.py`
- **inputs:** run
- **config keys:** dpi, figsize, frac_ylabel, frac_ylim, frac_yscale, mean_ylabel, mean_ylim, mean_yscale, unresolved_label, unresolved_r_max, xlabel, xlim, xscale

### `log_slope`

- **runner:** `runners/make_run_plots.py`
- **inputs:** run
- **config keys:** color_index, dpi, figsize_key, line_width, reference_line, title, unresolved_label, unresolved_r_max, xlabel, xlim, xscale, ylabel, ylim, yscale

### `particles_2d`

- **runner:** `runners/make_run_plots.py`
- **inputs:** run
- **config keys:** bins, cmap, colorbar_label, dpi, fps, gyr_per_code, lim, min_lim, sigma_label

### `particles_3d`

- **runner:** `runners/make_run_plots.py`
- **inputs:** run
- **config keys:** alpha, cmap, duration_ms, gif_palette_colors, label, max_points, point_size, scale_bar, seed, wireframe

### `sigma_v`

- **runner:** `runners/make_run_plots.py`
- **inputs:** run
- **config keys:** color_index, dpi, figsize_key, line_width, title, unresolved_label, unresolved_r_max, xlabel, xlim, xscale, ylabel, ylim, yscale


## Блок `campaigns`

CAMPAIGNS — сравнение группы прогонов и диагностика кампаний

| plot | что показывает | данные | вход | выходной файл |
|---|---|---|---|---|
| `core_density_vs_sigma` | Относительное изменение rho_core к CDM при изменении sigma/m | series | runs | `core_density_vs_sigma.png` |
| `criteria_time_panel` | Панель временных критериев disk-transition (dSIDM-серия) | load_metrics_series | runs | `diag_criteria_time_panel.png` |
| `density_compare` | Сравнение rho(r) группы прогонов на одних осях | series | runs | `density_compare.png` |
| `diag_eloss_vs_f` | Потери энергии vs фактор диссипации (dSIDM-серия) | load_metrics_series | runs | `diag_eloss_vs_f.png` |
| `disk_dashboard` | Дашборд дисковых диагностик группы прогонов | series | runs | `05_disk_dashboard.png` |
| `log_rho_compare` | Верх: rho(r); низ: Delta log rho vs CDM-референс | series | runs | `log_rho_compare.png` |
| `log_slope_compare` | Сравнение наклона dlnrho/dlnr группы прогонов | series | runs | `log_slope_compare.png` |
| `morphology_profiles_compare` | Радиальные морфологические профили группы (c/a, вращение) | series | runs | `03_shape_radial_profiles_final.png` |
| `phase_space_compare` | Фазовое пространство R-vphi группы прогонов | phase_space_histogram | runs | `04_phase_space_R_vphi_final.png` |
| `rot_curve_compare` | Верх: v_circ(r); низ: Delta v vs CDM-референс | series | runs | `rot_curve_compare.png` |
| `runaway_timestep_panel` | Панель dt-runaway диагностики серии прогонов | load_metrics_series | runs | `diag_runaway_timestep_panel.png` |
| `sigma_v_compare` | Сравнение sigma_v(r) группы прогонов | series | runs | `sigma_v_compare.png` |
| `surface_density_residuals` | Остатки поверхностной плотности vs CDM-база | prepare_visual_snapshot | runs | `02_surface_density_residual_vs_cdm_final.png` |
| `visual_morphology_montage` | Монтаж карт поверхностной плотности группы прогонов | prepare_visual_snapshot | runs | `01_surface_density_montage_final.png` |

### `core_density_vs_sigma`

- **runner:** `runners/make_campaign_plots.py`
- **inputs:** runs
- **config keys:** baseline_label, dpi, figsize_key, fractional_title, fractional_ylabel, marker, title, xlabel, xlim, xscale, ylabel, ylim, yscale

### `criteria_time_panel`

- **runner:** `runners/make_campaign_diag_plots.py`
- **inputs:** runs
- **config keys:** criteria_labels, dpi, figsize, legend_font_size, threshold_ca, threshold_thickness, threshold_vrot, title, xlabel, xlim, ylim_ca, ylim_thickness, ylim_vrot

### `density_compare`

- **runner:** `runners/make_campaign_plots.py`
- **inputs:** runs
- **config keys:** dpi, figsize_key, title, xlabel, xlim, xscale, ylabel, ylim, yscale

### `diag_eloss_vs_f`

- **runner:** `runners/make_campaign_diag_plots.py`
- **inputs:** runs
- **config keys:** color_index, dpi, figsize_key, legend_loc, marker, show_theory_curve, show_yx_line, title, xlabel, xlim, ylabel, ylim

### `disk_dashboard`

- **runner:** `runners/make_campaign_morphology_plots.py`
- **inputs:** runs
- **config keys:** dpi, title

### `log_rho_compare`

- **runner:** `runners/make_campaign_plots.py`
- **inputs:** runs
- **config keys:** baseline_label, diff_ylabel, dpi, figsize_key, legend, title, top_ylabel, top_yscale, xlabel, xscale

### `log_slope_compare`

- **runner:** `runners/make_campaign_plots.py`
- **inputs:** runs
- **config keys:** dpi, figsize_key, title, xlabel, xlim, xscale, ylabel, ylim, yscale

### `morphology_profiles_compare`

- **runner:** `runners/make_campaign_morphology_plots.py`
- **inputs:** runs
- **config keys:** dpi, title

### `phase_space_compare`

- **runner:** `runners/make_campaign_morphology_plots.py`
- **inputs:** runs
- **config keys:** cmap, dpi, floor, title

### `rot_curve_compare`

- **runner:** `runners/make_campaign_plots.py`
- **inputs:** runs
- **config keys:** baseline_label, diff_ylabel, dpi, figsize_key, legend, title, top_ylabel, top_yscale, xlabel, xscale

### `runaway_timestep_panel`

- **runner:** `runners/make_campaign_diag_plots.py`
- **inputs:** runs
- **config keys:** dpi, dt_ylabel, dt_yscale, figsize, ni_ylabel, ni_yscale, title, xlabel, xlim

### `sigma_v_compare`

- **runner:** `runners/make_campaign_plots.py`
- **inputs:** runs
- **config keys:** dpi, figsize_key, title, xlabel, xlim, xscale, ylabel, ylim, yscale

### `surface_density_residuals`

- **runner:** `runners/make_campaign_morphology_plots.py`
- **inputs:** runs
- **config keys:** baseline_index, cmap, color_quantile, dpi, eps, lim, smooth_radius, title, vmax, vmax_cap, vmax_floor

### `visual_morphology_montage`

- **runner:** `runners/make_campaign_morphology_plots.py`
- **inputs:** runs
- **config keys:** cmap, dpi, floor, lim, title


## Блок `presentations`

PRESENTATIONS — фигуры под слайды

_пока пусто_

## Примеры запуска

```bash
# один production-прогон (блок core):
docker exec gadget-gizmo python3 /nbody/scripts/analysis/runners/make_run_plots.py \
    --run-root /nbody/runs/<run>

# IC-гейт (блок ic):
docker exec gadget-gizmo python3 /nbody/scripts/analysis/runners/make_ic_plots.py \
    --ic /nbody/ics/<name>

# ранние снапшоты + гейт (блок prerun):
docker exec gadget-gizmo python3 /nbody/scripts/analysis/runners/make_prerun_plots.py \
    --run /nbody/runs/<run> --ref /nbody/runs/<cdm-run>

# сравнение профилей группы (блок campaigns, profile-compare):
docker exec gadget-gizmo python3 /nbody/scripts/analysis/runners/make_campaign_plots.py \
    /nbody/runs/<run-a> /nbody/runs/<run-b> --campaign <campaign>

# морфология группы (блок campaigns: montage/phase-space/dashboard):
docker exec gadget-gizmo python3 \\
    /nbody/scripts/analysis/runners/make_campaign_morphology_plots.py \\
    --group-root /nbody/runs/<campaign> --campaign <campaign>

# DIAG-панели группы (блок campaigns):
docker exec gadget-gizmo python3 \\
    /nbody/scripts/analysis/runners/make_campaign_diag_plots.py \\
    --group-root /nbody/runs/<campaign> --campaign <campaign> \\
    --criteria-runs <run-a> <run-b>
```
