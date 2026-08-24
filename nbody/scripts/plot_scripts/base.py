#nbody/scripts/plot_scripts/base.py
"""
base.py — data contract (runtime validation) и абстрактный BasePlot.

Data contract — компактный декларативный протокол:

    data_contract = {
        "r":   FieldSpec(("R",)),            # required numeric, shape (R,)
        "pos": FieldSpec(("N", 3)),
        "times": FieldSpec(("T",), required=False),
    }

Символьные имена размерностей ("R", "T", "N") должны совпадать между полями;
целые числа в shape проверяются буквально. validate_data() собирает ВСЕ
проблемы и выдаёт одну понятную ошибку вида:

    DensityPlot: field 'r' expected shape ('R',), received (100, 2)
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Dict, Mapping, Tuple, Union

import numpy as np


class PlotValidationError(ValueError):
    """Данные не соответствуют data_contract конкретного plot."""


# ──────────────────────────── Спецификация поля ─────────────────────────────

Dim = Union[str, int]


@dataclass(frozen=True)
class FieldSpec:
    """
    shape : tuple символьных имён ("R", "T", "N") или фиксированных int.
    dtype : "numeric" | "integer" | "str" | "any"
    required : отсутствующий required-ключ — ошибка; optional можно не передавать.
    """

    shape: Tuple[Dim, ...]
    dtype: str = "numeric"
    required: bool = True

    @property
    def shape_str(self) -> str:
        return "(" + ", ".join(str(d) for d in self.shape) + ")"


def F(shape, dtype: str = "numeric", required: bool = True) -> FieldSpec:
    """Короткий алиас для объявления контрактов."""
    return FieldSpec(shape=tuple(shape), dtype=dtype, required=required)


Contract = Dict[str, FieldSpec]


def validate_fields(plot_name: str, fields: Mapping[str, Any],
                    contract: Contract) -> None:
    """
    Проверить dict полей по контракту. Бросает PlotValidationError со
    списком всех проблем сразу. Используется BasePlot.validate_data для
    верхнеуровневых данных и compare-plots для валидации каждого элемента
    серии (переиспользуется, а не копируется).
    """
    problems = []
    dims: Dict[str, int] = {}
    for field_name, spec in contract.items():
        value = fields.get(field_name, None)
        if value is None:
            if spec.required:
                problems.append(
                    f"missing required field '{field_name}' "
                    f"(expected {spec.shape_str}, {spec.dtype})")
            continue

        arr = np.asarray(value)

        if spec.dtype == "numeric" and not np.issubdtype(arr.dtype, np.number):
            problems.append(
                f"field '{field_name}' expected numeric dtype, got {arr.dtype}")
            continue
        if spec.dtype == "integer" and not np.issubdtype(arr.dtype, np.integer):
            problems.append(
                f"field '{field_name}' expected integer dtype, got {arr.dtype}")
            continue
        if spec.dtype == "str" and arr.dtype.kind not in ("U", "S", "O"):
            problems.append(
                f"field '{field_name}' expected string, got dtype {arr.dtype}")
            continue

        if len(spec.shape) != arr.ndim:
            problems.append(
                f"field '{field_name}' expected shape {spec.shape_str}, "
                f"received {arr.shape} (ndim {arr.ndim} != {len(spec.shape)})")
            continue

        for axis, (dim, size) in enumerate(zip(spec.shape, arr.shape)):
            if isinstance(dim, int):
                if size != dim:
                    problems.append(
                        f"field '{field_name}' expected size {dim} along axis "
                        f"{axis} (shape {spec.shape_str}), received {size}")
            elif isinstance(dim, str):
                if dim in dims and dims[dim] != size:
                    problems.append(
                        f"field '{field_name}' inconsistent size of dimension "
                        f"'{dim}' on axis {axis}: got {size}, earlier fields "
                        f"use {dims[dim]}")
                else:
                    dims[dim] = size

    if problems:
        details = "\n  - ".join(problems)
        raise PlotValidationError(
            f"{plot_name}: data validation failed:\n  - {details}")


def format_contract(contract: Contract) -> str:
    """Человекочитаемая таблица контракта (для describe())."""
    lines = []
    for fname, spec in contract.items():
        req = "required" if spec.required else "optional"
        lines.append(f"  {fname:<14} {spec.shape_str:<16} {spec.dtype:<9} {req}")
    return "\n".join(lines)



# ──────────────────────────────── BasePlot ──────────────────────────────────

class BasePlot(ABC):
    """
    Единственный уровень наследования: BasePlot -> ConcretePlot.

    Каждый concrete plot обязан определить:
        name           — короткое имя в registry ("density", ...);
        description    — документация происхождения данных (для человека и AI);
        data_contract  — ожидаемая структура данных (runtime validation);
        default_config — стандартные настройки самого графика;
        render()       — отрисовка + сохранение, возвращает путь/пути файлов.

    render() получает УЖЕ подготовленные plot-ready данные. Никакой загрузки
    HDF5 и физики внутри plot'ов — этим занимаются loaders/analysis-код.
    """

    name: str = ""
    description: str = ""
    data_contract: Contract = {}
    default_config: Dict[str, Any] = {}

    def __init__(self, settings=None):
        # settings — PlotSettings; импорт здесь, чтобы избежать цикла модулей.
        if settings is None:
            from settings import PlotSettings
            settings = PlotSettings()
        self.settings = settings

    @abstractmethod
    def render(self, data: Mapping[str, Any], config: Dict[str, Any]):
        """Отрисовать график по resolved config и сохранить файл(ы).
        Возвращает путь (или список путей) созданных файлов."""

    # ─────────────────────────── validation ────────────────────────────────

    def validate_data(self, data: Mapping[str, Any]) -> None:
        """
        Проверить данные по data_contract. Базовой реализации достаточно для
        большинства plots; concrete plot может расширить/переопределить её.
        """
        validate_fields(self.name, data, self.data_contract)

