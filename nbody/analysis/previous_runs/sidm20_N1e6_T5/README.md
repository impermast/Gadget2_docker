# SIDM sigma=20 dwarf N=1e6 T=5 — полный анализ

- Прогон: `nbody/runs/sidm20_dwarf_N1e6_T5/` (GIZMO, DM_SIDM=8, sigma=20, TimeMax=5, 52 снапшота)
- Дата завершения: 2026-08-24

## Результаты

| Метрика | Значение |
|---|---|
| Core density (r<2 kpc) | 2.65e-3 |
| Inner log-slope | -0.14 (почти изотермическое ядро) |
| NInteractions total | 8 147 390 |
| Частиц с рассеяниями | 513991/1e6 (51.4%), mean=15.9, max=94 |
| NI в ядре (r<1.3 kpc) | 100% частиц, mean~29 |

Вывод: SIDM-модуль работает корректно; при sigma=20 за 5 Gyr формируется
выраженное ядро (slope ~0 против -1.39 у CDM).

## Содержимое

- `analysis/` — профили плотности/slope/sigma_v + радиальный профиль NInteractions + summary_analysis.txt
- `animation/evolution.gif` — эволюция проекции плотности x-y, 52 кадра (t=0..5)
- `snapshot_check.txt` — проверка финального снапшота
- `gizmo_run.param` — копия параметров прогона
