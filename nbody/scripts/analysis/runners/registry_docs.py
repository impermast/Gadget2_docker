#!/usr/bin/env python3
"""registry_docs.py — генератор nbody/analysis/REGISTRY.md из реестра графиков.

REGISTRY.md — машинно-читаемый каталог графиков, который читает ИИ-агент:
что показывает plot, какие данные ждёт, какой runner его строит, config keys.
Ручная правка файла запрещена (в шапке стоит предупреждение).

Режимы:
  (без флагов)  перегенерировать REGISTRY.md (по умолчанию);
  --check       не писать, только проверить, что файл совпадает с реестром
                (для CI/pre-commit: exit code 1 при расхождении);
  --print       напечатать markdown в stdout, ничего не менять;
  --describe    напечатать текстовое описание реестра (человекочитаемо).

Выход — ВСЕГДА <analysis-root>/REGISTRY.md (AnalysisPaths, NBODY_ANALYSIS_ROOT).

Пример:
    docker exec gadget-gizmo python3 /nbody/scripts/analysis/runners/registry_docs.py --check
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

_HERE = Path(__file__).resolve().parent
for _p in (_HERE.parent.parent, _HERE.parent):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

from analysis import plots as _plots  # noqa: E402,F401 (триггерит @register)
from analysis.paths import AnalysisPaths  # noqa: E402
from analysis.registry import describe, to_markdown, validate_registry  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--check", action="store_true",
                    help="проверить актуальность REGISTRY.md, не записывая файл")
    ap.add_argument("--print", dest="print_only", action="store_true",
                    help="напечатать markdown в stdout")
    ap.add_argument("--describe", action="store_true",
                    help="напечатать текстовое описание реестра")
    args = ap.parse_args()

    validate_registry()  # целостность: дубликаты, пустые поля, файлы runner'ов
    markdown = to_markdown()

    if args.print_only:
        print(markdown)
        return 0

    path = AnalysisPaths().registry_md()
    if args.check:
        if not path.exists():
            print(f"[FAIL] {path} отсутствует — запустите registry_docs.py")
            return 1
        current = path.read_text()
        if current != markdown:
            print(f"[FAIL] {path} устарел — перегенерируйте registry_docs.py")
            return 1
        print(f"[OK] {path} соответствует реестру")
        return 0

    path.write_text(markdown)
    print(f"[OK] REGISTRY.md записан: {path} ({len(markdown):,} байт)")
    print(describe())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
