"""Целостность реестра (маркер `math`): validate + покрытие + подсказки."""

import pytest

pytestmark = pytest.mark.math

from analysis import plots as _plots  # noqa: F401 (триггерит @register)
from analysis.registry import (
    BLOCKS,
    by_block,
    describe,
    find,
    registry,
    to_markdown,
    validate_registry,
)


def test_validate_registry_passes():
    validate_registry()


def test_blocks_nonempty_and_match_paths():
    from analysis.paths import BLOCK_NAMES
    assert tuple(BLOCKS) == tuple(BLOCK_NAMES)
    # Этап 2: наполнены core/campaigns; ic/prerun/presentations — этапы 3/5.
    for b in ("core", "campaigns"):
        assert by_block(b), f"блок '{b}' пуст"
    assert len(registry()) >= 21, "реестр потерял перенесённые plot'ы"


def test_names_unique_and_match_cls():
    for name, spec in registry().items():
        assert spec.name == name
        assert getattr(spec.cls, "name", None) == name
        assert spec.summary.strip(), f"{name}: пустой summary"
        assert spec.filename, f"{name}: пустой filename"
        assert spec.inputs, f"{name}: пустые inputs"


def test_describe_and_markdown_cover_all():
    md = to_markdown()
    for name in registry():
        assert name in md, f"{name} нет в REGISTRY.md"
    assert "НЕ РЕДАКТИРОВАТЬ ВРУЧНУЮ" in md


def test_find_typo_suggests():
    with pytest.raises(KeyError, match="density"):
        find("densit")
