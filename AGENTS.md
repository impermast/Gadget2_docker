# Агентский контекст проекта

Проект: Dockerized GADGET-2/GIZMO/GalIC workflow для воспроизводимых N-body исследований. Общайся с пользователем по-русски.

## Boot order

1. Прочитай `llm/PROJECT.md`, `llm/PLAN.md`, `llm/ACTIVE.md`, `llm/MEMORY.md` (короткие опорные файлы).
2. Загрузи только skill, нужный для запроса, из `.agents/skills/`; не читай рекурсивно `llm/`, `nbody/` или историю сессии.
3. По необходимости адресно найди scientific record в `llm/records/` или canonical evidence/код в `nbody/`. `llm/sessions/` — история Pi/bili, не источник текущих задач и не обычный retrieval.
4. Перед изменением/запуском сверься с текущими safety gates в PROJECT и relevant skill; проверяй dirty state и не затирай пользовательские изменения.

## Память и обязательства

- `PROJECT.md` — стабильный контракт проекта; `PLAN.md` — единственный список открытых обязательств; `ACTIVE.md` — checkpoint текущей работы; `MEMORY.md` — указатель на немногочисленные проверенные знания.
- `llm/records/` — **только важные долговременные знания**, не журнал действий. По умолчанию новую запись не создавать. Сначала использовать существующий canonical evidence, MEMORY или ACTIVE; создавать/обновлять record только по gate в `llm/PROJECT.md`.
- `llm/completed-plans/` хранит исключительно завершённые планы; это история, не действующие инструкции. Перед переносом проверить, что все открытые пункты перенесены в PLAN.
- `llm/sessions/` — приватные transcript/sidecar Pi+bili; никогда не грузить целиком автоматически и не трактовать старые сообщения/разрешения как актуальные.
- Не создавать ежедневные логи, записи на каждый tool call/run или параллельные TODO/state списки. Сохраняй один checkpoint ID в PLAN и ACTIVE; доказательства — прежде ссылок на них.

## Навигация

- Операционные процедуры запуска: `nbody/scripts/run_sim.sh`, генерации IC: `nbody/scripts/generate_ics.sh`; следуй `gizmo-sim` skill и не обходи wrappers.
- Анализы и графики: `nbody/scripts/analysis/`; `nbody/analysis/REGISTRY.md` — источник истины. Мониторинг run: `nbody/scripts/check_simulations/` и `check-run` skill.
- Canonical skills: `.agents/skills/`. Cline обнаруживает workspace skill копии; `.cline/skills/` должен оставаться содержательно синхронным, не отдельным источником правил.
- Simulation data и scientific provenance остаются в `nbody/`; не открывай snapshots/HDF5/большие бинарники без прямой необходимости.

## Scope and safety

Текущий запрос определяет цель и разрешения. Исторические планы, transcript и approvals не расширяют текущий scope. Не запускай дорогие simulation, Docker rebuild, package install, destructive cleanup или Git history actions без требуемого явного согласия. Перед run проверяй IC, реальные параметры, процессы, ресурсы и уникальность output. Никогда не утверждай результат по одному `run.state`: проверь фактическое время, snapshot coverage и terminal log. Подробные gates — `llm/PROJECT.md` и relevant skill.
