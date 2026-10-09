#!/usr/bin/env python3
"""registry.py — ЕДИНЫЙ реестр графиков: источник истины для ИИ-агента и людей.

Идея: агент НЕ читает код plot'ов. Он читает сгенерированный
`nbody/analysis/REGISTRY.md` (см. `to_markdown()`), где для каждого графика
указано: что показывает, какие данные ждёт, какой runner его строит, пример
команды, имя выходного файла и доступные config-ключи.

Как это держится в синхроне с кодом:

- каждый concrete plot объявляет атрибуты `name`, `block`, `summary`
  (обязательные) и опционально `data_source`, `inputs`, `runner`, `notes`;
- при импорте модулей блоков классы регистрируются декоратором `@register`;
- `validate_registry()` проверяет целостность (тест + генератор REGISTRY.md);
- `to_markdown()` собирает REGISTRY.md, ручная правка которого запрещена.

Блоки (порядок важен — это порядок в REGISTRY.md):

    ic            — начальные условия (target GalIC, гейт IC)
    prerun        — ранние снапшоты прогона (гейты, диагностика серии)
    core          — один production-прогон (профили, карты, анимации)
    campaigns     — сравнение группы прогонов, диагностика кампаний
    presentations — фигуры под слайды
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Type

# Каталог analysis/ — база для проверки существования runner-файлов.
_HERE = Path(__file__).resolve().parent

BLOCKS: Tuple[str, ...] = ("ic", "prerun", "core", "campaigns", "presentations")

BLOCK_TITLES: Dict[str, str] = {
    "ic": "IC — начальные условия (GalIC): target-профиль, гейт разрешения каспа",
    "prerun": "PRERUN — ранние снапшоты: гейт первых шагов, диагностика серии",
    "core": "CORE — один production-прогон: профили, карты, анимации",
    "campaigns": "CAMPAIGNS — сравнение группы прогонов и диагностика кампаний",
    "presentations": "PRESENTATIONS — фигуры под слайды",
}

# Runner по умолчанию для блока. Конкретный plot может переопределить его
# атрибутом класса `runner` (пример: морфологические plots блока campaigns
# строит make_campaign_morphology_plots.py, DIAG-панели — make_campaign_diag_plots.py).
# validate_registry() проверяет, что файл runner'а существует — реестр не может
# ссылаться на несуществующий CLI. `presentations` пока только asset storage.
BLOCK_RUNNERS: Dict[str, str] = {
    "ic": "runners/make_ic_plots.py",
    "prerun": "runners/make_prerun_plots.py",
    "core": "runners/make_run_plots.py",
    "campaigns": "runners/make_campaign_plots.py",
    "presentations": "",
}

# Какой вход ожидает блок по умолчанию.
BLOCK_INPUTS: Dict[str, Tuple[str, ...]] = {
    "ic": ("ic",),
    "prerun": ("run",),
    "core": ("run",),
    "campaigns": ("runs",),
    "presentations": ("campaign",),
}


class RegistryError(ValueError):
    """Ошибка целостности реестра (дубликат имени, неизвестный блок и т.п.)."""


@dataclass(frozen=True)
class PlotSpec:
    """Описание одного графика. Собирается автоматически из класса plot."""

    name: str
    block: str
    summary: str
    cls: Type[object] = field(repr=False, compare=False, default=None)
    data_source: str = ""
    inputs: Tuple[str, ...] = ()
    runner: str = ""
    filename: str = ""
    config_keys: Tuple[str, ...] = ()
    notes: str = ""

    @property
    def dotted(self) -> str:
        return f"{type(self.cls).__module__}.{self.cls.__name__}" if self.cls else ""


_REGISTRY: Dict[str, PlotSpec] = {}
_LOADED = False


def register(cls):
    """Декоратор: зарегистрировать concrete plot в реестре."""
    name = getattr(cls, "name", "")
    if not name:
        raise RegistryError(f"{cls.__name__}: не задан атрибут name")
    block = getattr(cls, "block", "")
    if block not in BLOCKS:
        raise RegistryError(
            f"{cls.__name__} ('{name}'): block='{block}' неизвестен; "
            f"допустимые блоки: {BLOCKS}")
    if name in _REGISTRY:
        prev = _REGISTRY[name].cls
        raise RegistryError(
            f"дубликат имени plot '{name}': {cls.__name__} и "
            f"{getattr(prev, '__name__', prev)}")

    cfg = dict(getattr(cls, "default_config", {}) or {})
    spec = PlotSpec(
        name=name,
        block=block,
        summary=getattr(cls, "summary", "") or (getattr(cls, "description", "") or "").strip().split("\n")[0],
        cls=cls,
        data_source=getattr(cls, "data_source", "") or "см. description",
        inputs=tuple(getattr(cls, "inputs", ()) or BLOCK_INPUTS[block]),
        runner=getattr(cls, "runner", "") or BLOCK_RUNNERS[block],
        filename=str(cfg.get("filename", "")),
        config_keys=tuple(sorted(k for k in cfg if k != "filename")),
        notes=getattr(cls, "notes", ""),
    )
    _REGISTRY[name] = spec
    return cls


def load_all() -> None:
    """Импортировать модули блоков (триггерит регистрацию). Идемпотентно."""
    global _LOADED
    if _LOADED:
        return
    _LOADED = True
    from . import plots  # noqa: F401  (побочный эффект: @register)


def registry() -> Dict[str, PlotSpec]:
    """Загруженный реестр (после load_all())."""
    load_all()
    return dict(_REGISTRY)


def names() -> List[str]:
    return sorted(registry().keys())


def find(name: str) -> PlotSpec:
    """Найти plot по имени; при промахе — подсказка ближайших вариантов."""
    import difflib

    reg = registry()
    if name in reg:
        return reg[name]
    close = difflib.get_close_matches(name, list(reg), n=3, cutoff=0.4)
    hint = f" Возможно, вы имели в виду: {', '.join(close)}." if close else ""
    raise KeyError(f"Unknown plot '{name}'.{hint} Доступные: {sorted(reg)}")


def by_block(block: str) -> List[PlotSpec]:
    if block not in BLOCKS:
        raise KeyError(f"Unknown block '{block}'. Допустимые: {list(BLOCKS)}")
    reg = registry()
    return [reg[n] for n in sorted(reg) if reg[n].block == block]


def describe(name: Optional[str] = None, block: Optional[str] = None) -> str:
    """Человекочитаемое/машинное описание реестра (для `--describe` и агента)."""
    reg = registry()
    if name is not None:
        spec = find(name)
        keys = ", ".join(spec.config_keys) or "—"
        return (
            f"[{spec.name}]  block={spec.block}  ({spec.dotted})\n"
            f"  summary:     {spec.summary}\n"
            f"  data source: {spec.data_source}\n"
            f"  inputs:      {', '.join(spec.inputs)}\n"
            f"  runner:      {spec.runner}\n"
            f"  filename:    {spec.filename or '—'}\n"
            f"  config keys: {keys}\n"
            f"  notes:       {spec.notes or '—'}"
        )
    blocks = [block] if block else list(BLOCKS)
    out = [f"plot registry: {len(reg)} plots, blocks={list(BLOCKS)}"]
    for b in blocks:
        specs = by_block(b)
        out.append(f"\n## {b}  ({len(specs)})")
        for s in specs:
            out.append(f"  {s.name:<26} {s.summary}")
    return "\n".join(out)


def to_markdown() -> str:
    """Сгенерировать содержимое nbody/analysis/REGISTRY.md."""
    reg = registry()
    lines: List[str] = []
    lines.append("# REGISTRY — каталог графиков (СГЕНЕРИРОВАНО, НЕ РЕДАКТИРОВАТЬ ВРУЧНУЮ)")
    lines.append("")
    lines.append("Источник: `nbody/scripts/analysis/registry.py` + `plots/*.py`.")
    lines.append("Перегенерировать: `python3 /nbody/scripts/analysis/runners/registry_docs.py`.")
    lines.append("")
    lines.append("Как пользоваться (для ИИ-агента):")
    lines.append("")
    lines.append("1. Найди график по блоку/смыслу в таблицах ниже — код читать не нужно.")
    lines.append("2. Возьми `runner` и `inputs`: это готовый CLI.")
    lines.append("3. Доступные настройки графика — в колонке `config keys`.")
    lines.append("4. Внутри блока runner может отличаться (см. `runner` у plot'а); "
                 "любой runner принимает `--plots a,b,c` для подмножества.")
    lines.append("")
    lines.append(f"Всего графиков: **{len(reg)}**; блоки: "
                 + ", ".join(f"`{b}` ({len(by_block(b))})" for b in BLOCKS))
    lines.append("")

    for b in BLOCKS:
        specs = by_block(b)
        lines.append(f"## Блок `{b}`")
        lines.append("")
        lines.append(BLOCK_TITLES[b])
        lines.append("")
        if not specs:
            lines.append("_пока пусто_")
            lines.append("")
            continue
        lines.append("| plot | что показывает | данные | вход | выходной файл |")
        lines.append("|---|---|---|---|---|")
        for s in specs:
            lines.append(
                f"| `{s.name}` | {s.summary} | {s.data_source} | "
                f"{', '.join(s.inputs)} | `{s.filename or '—'}` |")
        lines.append("")
        for s in specs:
            runner = s.runner
            lines.append(f"### `{s.name}`")
            lines.append("")
            lines.append(f"- **runner:** `{runner}`")
            lines.append(f"- **inputs:** {', '.join(s.inputs)}")
            lines.append(f"- **config keys:** {', '.join(s.config_keys) or '—'}")
            if s.notes:
                lines.append(f"- **notes:** {s.notes}")
            lines.append("")
        lines.append("")

    lines.append("## Примеры запуска")
    lines.append("")
    lines.append("```bash")
    lines.append("# один production-прогон (блок core):")
    lines.append("docker exec gadget-gizmo python3 /nbody/scripts/analysis/runners/make_run_plots.py \\")
    lines.append("    --run-root /nbody/runs/<run>")
    lines.append("")
    lines.append("# IC-гейт (блок ic):")
    lines.append("docker exec gadget-gizmo python3 /nbody/scripts/analysis/runners/make_ic_plots.py \\")
    lines.append("    --ic /nbody/ics/<name>")
    lines.append("")
    lines.append("# ранние снапшоты + гейт (блок prerun):")
    lines.append("docker exec gadget-gizmo python3 /nbody/scripts/analysis/runners/make_prerun_plots.py \\")
    lines.append("    --run /nbody/runs/<run> --ref /nbody/runs/<cdm-run>")
    lines.append("")
    lines.append("# сравнение профилей группы (блок campaigns, profile-compare):")
    lines.append("docker exec gadget-gizmo python3 /nbody/scripts/analysis/runners/make_campaign_plots.py \\")
    lines.append("    /nbody/runs/<run-a> /nbody/runs/<run-b> --campaign <campaign>")
    lines.append("")
    lines.append("# морфология группы (блок campaigns: montage/phase-space/dashboard):")
    lines.append("docker exec gadget-gizmo python3 \\\\")
    lines.append("    /nbody/scripts/analysis/runners/make_campaign_morphology_plots.py \\\\")
    lines.append("    --group-root /nbody/runs/<campaign> --campaign <campaign>")
    lines.append("")
    lines.append("# DIAG-панели группы (блок campaigns):")
    lines.append("docker exec gadget-gizmo python3 \\\\")
    lines.append("    /nbody/scripts/analysis/runners/make_campaign_diag_plots.py \\\\")
    lines.append("    --group-root /nbody/runs/<campaign> --campaign <campaign> \\\\")
    lines.append("    --criteria-runs <run-a> <run-b>")
    lines.append("```")
    lines.append("")
    return "\n".join(lines)


def validate_registry() -> None:
    """Проверить целостность реестра (используется тестом и генератором)."""
    reg = registry()
    if not reg:
        raise RegistryError("реестр пуст: модули plots не зарегистрировали ни одного графика")
    empty = [b for b in BLOCKS if not by_block(b)]
    if empty:
        import warnings
        warnings.warn(
            f"блоки реестра пока пусты: {empty} "
            f"(пустые блоки не требуют runner'а; presentations хранит assets)")
    for name, s in reg.items():
        if s.name != name:
            raise RegistryError(f"ключ реестра '{name}' != PlotSpec.name '{s.name}'")
        if getattr(s.cls, "name", None) != name:
            raise RegistryError(f"'{name}': PlotSpec.name != cls.name")
        if not s.summary.strip():
            raise RegistryError(f"'{name}': пустой summary")
        if not s.filename:
            raise RegistryError(f"'{name}': пустой default_config['filename']")
        if not s.inputs:
            raise RegistryError(f"'{name}': пустой inputs")
        if s.block not in BLOCKS:
            raise RegistryError(f"'{name}': неизвестный block '{s.block}'")
        # The presentation block currently stores curated assets; plots in that
        # block will define a concrete runner when such a plot is introduced.
        if not s.runner:
            if s.block == "presentations":
                continue
            raise RegistryError(f"'{name}': пустой runner")
        runner_file = _HERE / s.runner
        if not runner_file.is_file():
            raise RegistryError(
                f"'{name}': runner '{s.runner}' не существует "
                f"(ожидался файл {runner_file})")


def reset_for_tests() -> None:
    """Только для тестов: очистить реестр и флаг загрузки."""
    global _LOADED
    _REGISTRY.clear()
    _LOADED = False