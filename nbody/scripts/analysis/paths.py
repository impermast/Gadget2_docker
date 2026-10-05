#!/usr/bin/env python3
"""paths.py — правила размещения артефактов анализа по блокам.

Единая точка правды о том, «куда кладём результаты»:

    nbody/analysis/
      REGISTRY.md         — сгенерированный каталог графиков
      README.md           — карта блоков
      ic/<ic_name>/       — гейт и target-профили начальных условий
      prerun/<run_name>/  — ранние снапшоты: гейт первых шагов, серия
      core/<run_name>/    — один production-прогон
      campaigns/<campaign>[/<run>]/  — сравнение группы прогонов
      presentations/<YYYY-MM-DD[-name]>/
      previous_runs/      — артефакты прежних прогонов + таблица переходов
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass, field
from pathlib import Path

# Порядок и состав блоков (должен совпадать с registry.BLOCKS).
BLOCK_NAMES = ("ic", "prerun", "core", "campaigns", "presentations")

DEFAULT_ROOT = Path("/nbody/analysis")
ROOT_ENV_VAR = "NBODY_ANALYSIS_ROOT"

# Имя/группа артефакта — ровно один сегмент пути: без `/`, `..`, пустых строк.
# Жёсткая часть группировки: никакой вызов не может «увести» каталог наружу
# (в runs/, /tmp, …) — см. artifact_dir().
_SEGMENT_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")


def default_analysis_root() -> Path:
    """Корень артефактов анализа (переопределяется через NBODY_ANALYSIS_ROOT)."""
    env = os.environ.get(ROOT_ENV_VAR)
    return Path(env) if env else DEFAULT_ROOT


@dataclass
class AnalysisPaths:
    """Помощник путей: block() -> каталог блока, artifact_dir() -> подкаталог."""

    root: Path = field(default_factory=default_analysis_root)

    def __post_init__(self) -> None:
        self.root = Path(self.root)

    def _check(self, block: str) -> str:
        if block not in BLOCK_NAMES:
            raise KeyError(
                f"Unknown analysis block '{block}'. "
                f"Допустимые: {list(BLOCK_NAMES)}")
        return block

    @staticmethod
    def _check_segment(value: str, what: str) -> str:
        """Имя артефакта — ровно один сегмент пути (защита от `..` и `/`)."""
        if not _SEGMENT_RE.match(value or ""):
            raise ValueError(
                f"Недопустимое {what} '{value}': разрешены только "
                f"латиница/цифры/._- без слэшей (один сегмент пути)")
        return value

    def _contained(self, p: Path) -> Path:
        """Каталог обязан лежать внутри root (containment-guard)."""
        root = self.root.resolve()
        try:
            p.resolve().relative_to(root)
        except ValueError:
            raise ValueError(
                f"Каталог '{p}' выходит за корень анализа '{root}' — запрещено")
        return p

    def block(self, block: str) -> Path:
        """Каталог блока (создаётся при необходимости)."""
        self._check(block)
        p = self.root / block
        p.mkdir(parents=True, exist_ok=True)
        return self._contained(p)

    def artifact_dir(self, block: str, name: str,
                     group: str | None = None) -> Path:
        """Каталог артефактов: <root>/<block>[/<group>]/<name>."""
        self._check(block)
        self._check_segment(name, "имя артефакта")
        base = self.root / block
        if group is not None:
            self._check_segment(group, "имя группы/кампании")
            base = base / group
        p = base / name
        p.mkdir(parents=True, exist_ok=True)
        return self._contained(p)

    def run_dir(self, run_name: str) -> Path:
        """Каталог production-прогона (блок core)."""
        return self.artifact_dir("core", run_name)

    def ic_dir(self, ic_name: str) -> Path:
        """Каталог артефактов начальных условий."""
        return self.artifact_dir("ic", ic_name)

    def prerun_dir(self, run_name: str) -> Path:
        """Каталог ранних снапшотов прогона."""
        return self.artifact_dir("prerun", run_name)

    def campaign_dir(self, campaign: str, member: str | None = None) -> Path:
        """Каталог кампании (или каталог участника внутри кампании)."""
        if member:
            return self.artifact_dir("campaigns", member, group=campaign)
        return self.artifact_dir("campaigns", campaign)

    def presentation_dir(self, label: str) -> Path:
        """Каталог презентации/слайдов."""
        return self.artifact_dir("presentations", label)

    def previous_runs_dir(self) -> Path:
        """Артефакты прежних прогонов (не перезаписываем — только чтение)."""
        p = self.root / "previous_runs"
        p.mkdir(parents=True, exist_ok=True)
        return p

    def registry_md(self) -> Path:
        """Путь к сгенерированному REGISTRY.md."""
        self.root.mkdir(parents=True, exist_ok=True)
        return self.root / "REGISTRY.md"