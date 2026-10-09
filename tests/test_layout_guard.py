"""Guard-раскладка анализа (маркер `guard`): запрет ad-hoc графиков.

Инварианты (нарушение = красный тест, красный pre-commit, красный CI):

1. `matplotlib` / `PIL` импортируется ТОЛЬКО в `nbody/scripts/analysis/`
   (whitelist ниже — явные незавершённые миграции).
2. `.savefig(` вызывается ТОЛЬКО в узких горловинах `analysis/plotter.py`
   и `analysis/style.py`;
   сборка GIF через PIL — только в `analysis/plots/animations.py`.
3. В `nbody/scripts/analysis/runners/*.py` запрещены CLI-флаги
   `--outdir/--output/--output-dir/-o`: выход вычисляется из AnalysisPaths.
4. Каждый класс-наследник `*Plot` в `analysis/plots/*.py` (кроме `_`-хелперов)
   обязан иметь декоратор `@register`.
5. Whitelist обязан быть точным: запись на несуществующий файл = fail
   (список не может копиться — только убывать).

Whitelist-легенда: удалять запись только после фактической миграции/удаления
рисующего кода и проверки потребителей.
  check_ic_cusp.py, early_cdm_gate.py — метрики в loaders; legacy CLI вызывает
                                        registry-based plotter, но не рисует напрямую.
  analyze_series.py, compare_shape_series.py — совместимые CLI-прокси; rendering
                                               передан make_prerun_plots.py.
"""

from __future__ import annotations

import ast
import builtins
import importlib.util
from pathlib import Path
import sys

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = REPO_ROOT / "nbody" / "scripts"
ANALYSIS = SCRIPTS / "analysis"

# Относительные пути от корня репо (файлы) или каталоги целиком. В whitelist
# остаются только два legacy gate CLI; они пока импортируют plotting layer.
LEGACY_PLOT_WHITELIST = {
    "nbody/scripts/check_simulations/check_ic_cusp.py",            # transitional CLI
    "nbody/scripts/check_simulations/early_cdm_gate.py",           # transitional CLI
}

SAVEFIG_CHOKE_POINTS = {ANALYSIS / "plotter.py", ANALYSIS / "style.py"}
# Узкие горловины сохранения: plotter.py (PNG через plotter) и style.py
# (save_figure/save — обёртка, в которую переедет settings.save_figure).
# Именно сюда на этапе 2 переезжает единственный вызов fig.savefig.
PIL_SAVE_MODULES = {ANALYSIS / "plots" / "animations.py"}  # сборка GIF из кадров
FAIL_MSG = ("Рисование только через nbody/scripts/analysis/ "
            "(реестр + runners + AnalysisPaths). См. implementation_plan.md §[Skills].")

FORBIDDEN_OUTDIR_FLAGS = {"--outdir", "--output", "--output-dir", "-o"}


@pytest.mark.guard
def test_legacy_series_clis_forward_compatible_options(monkeypatch):
    """Legacy CLI names keep their documented arguments and dispatch canonically."""
    check_scripts = SCRIPTS / "check_simulations"
    for filename, argv, expected in (
        ("analyze_series.py",
         ["analyze_series.py", "--run-root", "/runs/one", "--ptype", "3",
          "--max-frames", "10"],
         ["--run-root", "/runs/one", "--ptype", "3", "--max-frames", "10"]),
        ("compare_shape_series.py",
         ["compare_shape_series.py", "--group-root", "/runs/group", "--runs",
          "one", "two", "--metrics-rel", "partial_analysis/metrics_series.csv", "--tg"],
         ["--group-root", "/runs/group", "--campaign", "group", "--member",
          "shape_compare", "--metrics-rel", "partial_analysis/metrics_series.csv",
          "--runs", "one", "two", "--tg"]),
    ):
        captured = {}

        def dispatch(filename=filename, captured=captured):
            captured["argv"] = sys.argv[1:]
            return 0

        runner_path = SCRIPTS / "analysis" / "runners" / "make_prerun_plots.py"
        runner_spec = importlib.util.spec_from_file_location(
            "test_make_prerun_runner", runner_path)
        assert runner_spec.loader is not None
        runner = importlib.util.module_from_spec(runner_spec)
        runner_spec.loader.exec_module(runner)
        monkeypatch.setattr(runner, "main", dispatch)
        monkeypatch.setitem(sys.modules,
                            "analysis.runners.make_prerun_plots", runner)
        monkeypatch.setattr(sys, "argv", argv)
        spec = importlib.util.spec_from_file_location(
            f"legacy_{filename[:-3]}", check_scripts / filename)
        module = importlib.util.module_from_spec(spec)
        assert spec.loader is not None
        spec.loader.exec_module(module)
        assert module.main() == 0
        assert captured["argv"] == expected


def _rel(p: Path) -> str:
    return str(p.relative_to(REPO_ROOT))


def _is_whitelisted(path: Path) -> bool:
    rel = _rel(path)
    return any(rel == w or rel.startswith(w + "/") for w in LEGACY_PLOT_WHITELIST)


def _py_files() -> list[Path]:
    return sorted((REPO_ROOT / "nbody").rglob("*.py"))


def _parse(path: Path) -> ast.Module:
    try:
        return ast.parse(path.read_text(encoding="utf-8", errors="replace"),
                         filename=str(path))
    except SyntaxError as e:  # битый файл чиним, а не молча пропускаем
        pytest.fail(f"{_rel(path)}: SyntaxError при AST-скане: {e}")
        raise AssertionError


def _iter_import_roots(tree: ast.Module) -> list[str]:
    roots: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            roots.extend(a.name.split(".")[0] for a in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            roots.append(node.module.split(".")[0])
    return roots


@pytest.mark.guard
def test_whitelist_is_exact():
    """Whitelist точный: ни битых путей, ни накопленного легаси."""
    for w in sorted(LEGACY_PLOT_WHITELIST):
        target = REPO_ROOT / w
        assert target.exists(), (
            f"whitelist-запись '{w}' указывает в никуда — "
            f"файл уже мигрирован? Удали строку из LEGACY_PLOT_WHITELIST.")


@pytest.mark.guard
def test_no_matplotlib_outside_analysis():
    """matplotlib/PIL — только в analysis/ (+ точный whitelist)."""
    bad: list[str] = []
    for path in _py_files():
        rel = _rel(path)
        if rel.startswith("nbody/scripts/analysis/") or rel.startswith(
                "nbody/analysis/presentations/"):
            continue
        if _is_whitelisted(path):
            continue
        roots = _iter_import_roots(_parse(path))
        hits = sorted({r for r in roots if r in ("matplotlib", "PIL", "pillow")})
        if hits:
            bad.append(f"{_rel(path)}: импорт {hits}")
    assert not bad, FAIL_MSG + "\n" + "\n".join(bad)


@pytest.mark.guard
def test_savefig_only_in_plotter():
    """savefig — только узкие горловины (plotter.py, style.py)."""
    bad: list[str] = []
    for path in _py_files():
        rel = _rel(path)
        if rel.startswith("nbody/analysis/presentations/"):
            continue  # Curated slide-building source, not an analysis plot class.
        if path in SAVEFIG_CHOKE_POINTS:
            continue
        if _is_whitelisted(path):
            continue
        tree = _parse(path)
        for node in ast.walk(tree):
            if (isinstance(node, ast.Call)
                    and isinstance(node.func, ast.Attribute)
                    and node.func.attr == "savefig"):
                bad.append(f"{_rel(path)}:{node.lineno}: .savefig()")
                break
    assert not bad, FAIL_MSG + "\n" + "\n".join(bad)


@pytest.mark.guard
def test_pil_save_only_in_animations():
    """Сборка GIF (PIL .save) — только analysis/plots/animations.py."""
    bad: list[str] = []
    for path in _py_files():
        if path in PIL_SAVE_MODULES:
            continue
        if _is_whitelisted(path):
            continue
        tree = _parse(path)
        for node in ast.walk(tree):
            if (isinstance(node, ast.Call)
                    and isinstance(node.func, ast.Attribute)
                    and node.func.attr == "save"
                    and not isinstance(node.func.value, ast.Name)):
                continue  # prs.save/pptx и т.п. не трогаем (не фигуры)
            if (isinstance(node, ast.Call)
                    and isinstance(node.func, ast.Attribute)
                    and node.func.attr == "save"
                    and any(kw.arg == "save_all"
                            for kw in node.keywords)):
                bad.append(f"{_rel(path)}:{node.lineno}: PIL GIF-сборка")
                break
    assert not bad, FAIL_MSG + "\n" + "\n".join(bad)


@pytest.mark.guard
def test_runners_have_no_outdir_flags():
    """Раннеры не принимают свободный путь вывода (только AnalysisPaths)."""
    runners = ANALYSIS / "runners"
    assert runners.is_dir(), "нет каталога analysis/runners/ (этап 2 не выполнен?)"
    bad: list[str] = []
    for path in sorted(runners.glob("*.py")):
        tree = _parse(path)
        for node in ast.walk(tree):
            if (isinstance(node, ast.Call)
                    and isinstance(node.func, ast.Attribute)
                    and node.func.attr == "add_argument"):
                flags = [a.value for a in node.args
                         if isinstance(a, ast.Constant) and isinstance(a.value, str)]
                clash = sorted(set(flags) & FORBIDDEN_OUTDIR_FLAGS)
                if clash:
                    bad.append(f"{_rel(path)}:{node.lineno}: запрещённые флаги {clash}")
    assert not bad, ("Выход runner'а вычисляется из spec.block через AnalysisPaths, "
                     "свободный --outdir запрещён.\n" + "\n".join(bad))


@pytest.mark.guard
def test_all_plot_classes_registered():
    """Каждый plot-класс в analysis/plots — только через @register."""
    plots_dir = ANALYSIS / "plots"
    assert plots_dir.is_dir(), "нет каталога analysis/plots/ (этап 2 не выполнен?)"
    bad: list[str] = []
    for path in sorted(plots_dir.glob("*.py")):
        tree = _parse(path)
        for node in tree.body:
            if not isinstance(node, ast.ClassDef):
                continue
            if node.name.startswith("_"):
                continue
            base_names = []
            for b in node.bases:
                if isinstance(b, ast.Name):
                    base_names.append(b.id)
                elif isinstance(b, ast.Attribute):
                    base_names.append(b.attr)
            if not any(b == "BasePlot" or b.endswith("Plot") for b in base_names):
                continue
            has_register = any(
                (isinstance(d, ast.Name) and d.id == "register")
                or (isinstance(d, ast.Attribute) and d.attr == "register")
                or (isinstance(d, ast.Call)
                    and isinstance(d.func, ast.Attribute)
                    and d.func.attr == "register")
                for d in node.decorator_list)
            if not has_register:
                bad.append(f"{_rel(path)}:{node.lineno}: класс {node.name} без @register")
    assert not bad, ("Новые графики — только через реестр (@register + REGISTRY.md). "
                     "Процедура: implementation_plan.md §8.2.\n" + "\n".join(bad))


_SAFE_MODULE_GLOBALS = {"__file__", "__name__", "__doc__", "__package__",
                        "__spec__", "__loader__", "__builtins__"}


def _defined_names(tree: ast.Module) -> set:
    """Приближение области видимости модуля (импорты, def/class, присваивания)."""
    names = set(dir(builtins))
    for node in ast.walk(tree):
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            for a in node.names:
                names.add((a.asname or a.name).split(".")[0])
        elif isinstance(node, ast.alias):
            names.add((node.asname or node.name).split(".")[0])
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef,
                               ast.ClassDef)):
            names.add(node.name)
        elif isinstance(node, ast.Name) and isinstance(node.ctx, (ast.Store,
                                                                  ast.Del)):
            names.add(node.id)
        elif isinstance(node, ast.arg):
            names.add(node.arg)
        elif isinstance(node, ast.ExceptHandler) and node.name:
            names.add(node.name)
    return names | _SAFE_MODULE_GLOBALS


@pytest.mark.guard
def test_no_undefined_names_in_analysis():
    """Переносы/разбиения модулей не должны терять импорты и хелперы.

    Регрессия этапов 1-2: при разрезании loaders.py и analysis_plots.py на
    модули терялись `Mapping`/`Optional`/`validate_fields`/`LogNorm`/
    `_snapshot_number` — такие NameError вылезают только в runtime.
    """
    bad: dict = {}
    for path in sorted(ANALYSIS.rglob("*.py")):
        tree = _parse(path)
        used = {n.id for n in ast.walk(tree)
                if isinstance(n, ast.Name) and isinstance(n.ctx, ast.Load)}
        missing = sorted(used - _defined_names(tree))
        if missing:
            bad[_rel(path)] = missing
    assert not bad, ("Неопределённые имена (потерянные импорты/хелперы) — "
                     "импортируйте из analysis.* или восстановите функцию:\n"
                     + "\n".join(f"  {k}: {v}" for k, v in bad.items()))
