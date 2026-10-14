# MEMORY — проверенные знания и указатели

Краткий индекс долговременных знаний. Подробное evidence находится по ссылкам; статус/scope перечитывать перед применением.

- **GIZMO/GalIC outcomes не взаимозаменяемы; baseline/prerun/full-run различать.** Analysis source of truth: `nbody/scripts/analysis/`, registry `nbody/analysis/REGISTRY.md`.
- **Анализ текущей rotating N=1e6 campaign (2026-10-14):** семь T=1 runs не показывают disk signature (c/a 0.994–0.997, z/R 0.704–0.705, vrot/σ 0.311–0.324); это только эта IC/model/time scope. Campaign evidence: `nbody/analysis/campaigns/rotN1e6_campaign_review_20261014/`; source summary in `llm/records/rotating-n1e6-campaign.md`.
- **Не принимать run.state/rc=0 за физическое завершение.** Проверять actual time, snapshot coverage и terminal log. Пример sigma=2 на rotating N=1e6 остановился на t=0.5659/1, 57/101 с `No domain decomposition that stays within memory bounds is possible.`; provisional pathology при недостаточной central-resolution gate. Подробности: `llm/records/rotating-n1e6-campaign.md`.
- **Dissipation convention и applicability:** `llm/records/dissipation-parameter-audit.md`; статус аудированного solver/ограничения применять только в указанной там области.
- **Dark disk literature crosswalk:** `llm/records/dark-disk-literature-review.md`; atomic dark matter нельзя напрямую приравнивать к phenomenological constant `f_diss`.
- **Rotation IC provenance and gate:** `llm/records/ic-rotation-recommendation.md` + `ic-rotation-baseline-gate.md`; raw lineage/inventory at `ic-rotation-manifest.csv` and `ic-rotation-run-inventory.csv`. Nominal spin/rotation не гарантируют равновесие или образование диска.
- **Conference handoff:** `nbody/analysis/presentations/conference_2026/`; текущий пакет `science_partial`, не считать claims замороженными без сверки manifests/validation.

Новые пункты добавлять только если устойчивы, доказуемы и полезны в будущем; см. records gate в `llm/PROJECT.md`. Обновлять ссылку/существующую запись, не дублировать.
