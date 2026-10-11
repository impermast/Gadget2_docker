#!/usr/bin/env python3
"""Inventory simulation runs and write a deterministic provenance manifest.

This module is intentionally conservative.  A manifest is evidence about what
is present on disk, not a second simulation-status implementation.  Parameter
and log parsing is delegated to :mod:`check_simulations` where possible.  In
particular, this tool never opens an HDF5 dataset; snapshot information is
limited to filenames and text/CSV diagnostics.

Typical host invocation::

    python -m nbody.scripts.conference.manifest \
        --roots nbody/runs/dsidm_spin_k08_transition \
                nbody/runs/dissipation/test_dissipation_focused_T5 \
        --out nbody/analysis/presentations/conference_2026/run_manifest.csv

``/nbody`` paths emitted by GIZMO parameter files are understood when the
corresponding host path is available below the repository's ``nbody`` folder.
Large IC hashes are opt-in (``--hash-ics``) and cached once per source path.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import os
import re
import subprocess
import sys
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Iterator, Mapping, MutableMapping, Optional, Sequence


# ``manifest.py`` is also usable as a file (not just ``python -m``), matching
# the existing check_simulations CLIs.
SCRIPT_DIR = Path(__file__).resolve().parents[1]
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from check_simulations.gizmo_log import parse_log, parse_sync_points  # noqa: E402
from check_simulations.params import parse_param_file  # noqa: E402
from check_simulations.processes import find_processes  # noqa: E402
from check_simulations.verdict import classify  # noqa: E402


SCHEMA_VERSION = "conference-manifest-v1"
METRICS_SCHEMA_VERSION = "conference-metrics-v1"
UNKNOWN = "unknown"

# Keep this order stable.  It is the public CSV contract and also makes diffs
# useful when the manifest is regenerated.
MANIFEST_COLUMNS = [
    "run_id",
    "group",
    "run_path",
    "ic_path",
    "ic_sha256",
    "spin_k",
    "spin_k_source",
    "n_particles",
    "ptype",
    "sigma_over_m",
    "dissipation_d",
    "kick_velocity",
    "velocity_scale",
    "softening_value",
    "softening_parameter",
    "max_size_timestep",
    "time_max",
    "time_bet_snapshot",
    "first_snapshot",
    "time_limit_cpu",
    "mpi_procs",
    "run_commit",
    "analysis_commit",
    "analysis_dirty",
    "analysis_patch_sha256",
    "params_sha256",
    "solver_source_sha256",
    "solver_binary_sha256",
    "snapshots",
    "t_reached",
    "min_systemstep",
    "ninteractions_final",
    "status",
    "health",
    "metrics_status",
    "verdict_raw",
    "metrics_csv",
    "analysis_schema_version",
    "checked_at_utc",
    "started_at_utc",
    "ended_at_utc",
    "wall_minutes",
    "timing_source",
    "provenance_status",
    "notes",
]


@dataclass
class ManifestRow:
    """One row of the conference run manifest.

    ``None`` means that the value was not evidenced.  It is serialized as an
    empty CSV field; this is deliberately different from a confirmed numeric
    zero (for example CDM's cross section).
    """

    run_id: str
    group: str
    run_path: str
    ic_path: Optional[str] = None
    ic_sha256: Optional[str] = None
    spin_k: Optional[float] = None
    spin_k_source: Optional[str] = None
    n_particles: Optional[int] = None
    ptype: Optional[int] = None
    sigma_over_m: Optional[float] = None
    dissipation_d: Optional[float] = None
    kick_velocity: Optional[float] = None
    velocity_scale: Optional[float] = None
    softening_value: Optional[float] = None
    softening_parameter: Optional[str] = None
    max_size_timestep: Optional[float] = None
    time_max: Optional[float] = None
    time_bet_snapshot: Optional[float] = None
    first_snapshot: Optional[float] = None
    time_limit_cpu: Optional[float] = None
    mpi_procs: Optional[int] = None
    run_commit: Optional[str] = None
    analysis_commit: Optional[str] = None
    analysis_dirty: Optional[bool] = None
    analysis_patch_sha256: Optional[str] = None
    params_sha256: Optional[str] = None
    solver_source_sha256: Optional[str] = None
    solver_binary_sha256: Optional[str] = None
    snapshots: int = 0
    t_reached: Optional[float] = None
    min_systemstep: Optional[float] = None
    ninteractions_final: Optional[float] = None
    status: str = UNKNOWN
    health: str = UNKNOWN
    metrics_status: str = "missing"
    verdict_raw: str = ""
    metrics_csv: Optional[str] = None
    analysis_schema_version: Optional[str] = None
    checked_at_utc: Optional[str] = None
    started_at_utc: Optional[str] = None
    ended_at_utc: Optional[str] = None
    wall_minutes: Optional[float] = None
    timing_source: Optional[str] = None
    provenance_status: str = UNKNOWN
    notes: str = ""

    def as_dict(self) -> dict[str, Any]:
        """Return the stable public mapping used by CSV and JSON writers."""

        values = asdict(self)
        return {key: values.get(key) for key in MANIFEST_COLUMNS}

    def __getitem__(self, key: str) -> Any:
        """Permit small callers/tests to use ``row["status"]`` as well."""

        if key not in MANIFEST_COLUMNS:
            raise KeyError(key)
        return getattr(self, key)


def _coerce_number(value: Any) -> Any:
    """Parse GIZMO scalar text without turning unknown values into zero."""

    if value is None or isinstance(value, (int, float)):
        return value
    text = str(value).strip()
    if not text or text.lower() in {"n/a", "na", "none", "unknown", "nan"}:
        return None
    try:
        number = float(text)
    except (TypeError, ValueError):
        return text
    if number.is_integer() and abs(number) < 2**53:
        return int(number)
    return number


def _finite_number(value: Any) -> Optional[float]:
    value = _coerce_number(value)
    if isinstance(value, (int, float)):
        try:
            result = float(value)
            if result == result and abs(result) != float("inf"):
                return result
        except (TypeError, ValueError):
            pass
    return None


def _number_or_none(value: Any) -> Any:
    """Return an int for integral values, otherwise a finite float/None."""

    number = _finite_number(value)
    if number is None:
        return None
    return int(number) if number.is_integer() and abs(number) < 2**53 else number


def _sha256_file(path: Path, chunk_size: int = 1024 * 1024) -> Optional[str]:
    if not path.is_file():
        return None
    digest = hashlib.sha256()
    try:
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(chunk_size), b""):
                digest.update(chunk)
    except OSError:
        return None
    return digest.hexdigest()


def _sha256_bytes(parts: Iterable[bytes]) -> str:
    digest = hashlib.sha256()
    for part in parts:
        digest.update(part)
    return digest.hexdigest()


def _canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _utc_from_mtime(path: Path) -> Optional[str]:
    try:
        stamp = path.stat().st_mtime
    except OSError:
        return None
    return datetime.fromtimestamp(stamp, tz=timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _read_state(path: Path) -> dict[str, str]:
    result: dict[str, str] = {}
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return result
    for line in text.splitlines():
        if "=" in line:
            key, value = line.split("=", 1)
            result[key.strip()] = value.strip()
    return result


def _read_head(path: Path, max_bytes: int = 256_000) -> str:
    """Read only a bounded log prefix for cheap provenance fields."""

    if not path.is_file():
        return ""
    try:
        with path.open("rb") as handle:
            return handle.read(max_bytes).decode("utf-8", errors="replace")
    except OSError:
        return ""


def _normalise_path_text(value: Any) -> Optional[str]:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _repo_root() -> Path:
    # .../nbody/scripts/conference/manifest.py -> repository root
    return Path(__file__).resolve().parents[3]


def _map_container_path(path_text: str, repo_root: Path) -> Path:
    """Resolve host/container paths without changing the stored parameter."""

    raw = Path(path_text).expanduser()
    if raw.exists():
        return raw

    # The canonical container mount is /nbody.  Prefer a real host checkout
    # when invoked on the host; inside the container this branch is normally
    # unnecessary because /nbody already exists.
    if raw.is_absolute() and (str(raw) == "/nbody" or str(raw).startswith("/nbody/")):
        mapped = repo_root / "nbody" / raw.relative_to("/nbody")
        if mapped.exists() or mapped.with_name(mapped.name + ".hdf5").exists():
            return mapped
    if not raw.is_absolute():
        candidate = repo_root / raw
        if candidate.exists():
            return candidate
    return raw


def _ic_source_path(ic_value: Optional[str], run_root: Path, repo_root: Path) -> Optional[Path]:
    if not ic_value:
        return None
    candidates: list[Path] = []
    raw = Path(ic_value).expanduser()
    candidates.append(raw)
    candidates.append(_map_container_path(ic_value, repo_root))
    if not raw.is_absolute():
        candidates.append(run_root / raw)
    # GIZMO commonly stores InitCondFile without the .hdf5 suffix.
    expanded: list[Path] = []
    for candidate in candidates:
        expanded.append(candidate)
        if candidate.suffix.lower() != ".hdf5":
            expanded.append(candidate.with_name(candidate.name + ".hdf5"))
    for candidate in expanded:
        if candidate.is_file():
            return candidate
    return None


def _parse_param(path: Path) -> dict[str, str]:
    # The shared parser strips comments and handles the parameter syntax used
    # by run_sim.sh.  Keep an empty mapping for missing files.
    try:
        return parse_param_file(path)
    except (OSError, ValueError):
        return {}


def _param_sources(run_root: Path) -> list[tuple[str, Path, dict[str, str]]]:
    paths = [
        ("runtime", run_root / ".gizmo_run.param"),
        ("usedvalues", run_root / "output" / "parameters-usedvalues"),
        ("usedvalues_legacy", run_root / ".gizmo_run.param-usedvalues"),
    ]
    return [(name, path, _parse_param(path)) for name, path in paths if path.is_file()]


def _param_values(sources: Sequence[tuple[str, Path, Mapping[str, Any]]]) -> tuple[dict[str, Any], list[str]]:
    """Choose applied values and report disagreements between source files."""

    # GIZMO's parameters-usedvalues is the strongest evidence of what the
    # solver accepted.  The legacy sidecar is equivalent, then runtime input.
    priority = {"usedvalues": 0, "usedvalues_legacy": 1, "runtime": 2}
    keys = sorted({key for _name, _path, values in sources for key in values})
    selected: dict[str, Any] = {}
    conflicts: list[str] = []
    for key in keys:
        entries: list[tuple[str, Any]] = []
        for name, _path, values in sources:
            if key in values:
                entries.append((name, _coerce_number(values[key])))
        if not entries:
            continue
        selected[key] = sorted(entries, key=lambda item: priority.get(item[0], 99))[0][1]
        comparable_values = [value for _name, value in entries]
        comparable = True
        first = comparable_values[0]
        for other in comparable_values[1:]:
            if isinstance(first, (int, float)) and isinstance(other, (int, float)):
                # parameters-usedvalues are printed with slightly different
                # precision from the input file for a few unit constants.  Do
                # not call that formatting drift a physics conflict; ordinary
                # disagreements such as TimeMax 2 vs 3 remain conflicts.
                if not math.isclose(float(first), float(other), rel_tol=1e-5, abs_tol=1e-12):
                    comparable = False
                    break
            elif first != other:
                comparable = False
                break
        if not comparable:
            conflicts.append(key)
    return selected, conflicts


def _hash_params(sources: Sequence[tuple[str, Path, Mapping[str, Any]]]) -> Optional[str]:
    if not sources:
        return None
    chunks: list[bytes] = []
    for name, path, _values in sorted(sources, key=lambda item: item[0]):
        try:
            data = path.read_bytes()
        except OSError:
            continue
        chunks.extend((name.encode("utf-8"), b"\0", data, b"\0"))
    return _sha256_bytes(chunks) if chunks else None


def _spin_from_ic(ic_path: Optional[str]) -> tuple[Optional[float], Optional[str]]:
    if not ic_path:
        return None, None
    match = re.search(r"(?:^|[_-])k(?P<digits>\d{1,3})(?:[_\-.]|$)", Path(ic_path).name, re.IGNORECASE)
    if not match:
        return None, None
    digits = match.group("digits")
    try:
        if len(digits) == 2 and digits.startswith("0"):
            value = float(f"0.{digits[1:]}")
        elif len(digits) == 2:
            value = float(digits) / 10.0
        else:
            value = float(digits)
    except ValueError:
        return None, None
    return value, "ic_path_basename_nominal"


def _metrics_candidates(run_root: Path) -> list[Path]:
    # Keep a documented priority, while exposing differing candidates as a
    # provenance conflict instead of silently taking whichever glob wins.
    candidates = [
        run_root / "partial_analysis" / "metrics_series.csv",
        run_root / "analysis" / "metrics_series.csv",
        run_root / "metrics_series.csv",
        run_root / "output" / "metrics_series.csv",
    ]
    return [path for path in candidates if path.is_file()]


def _read_metrics(path: Path, time_max: Optional[float], expected_snapshots: Optional[int]) -> dict[str, Any]:
    """Read a metrics CSV without materialising it into the manifest."""

    result: dict[str, Any] = {
        "valid": False,
        "rows": 0,
        "latest_time": None,
        "latest": {},
        "min_systemstep": None,
        "ninteractions_final": None,
        "schema_version": METRICS_SCHEMA_VERSION,
        "error": None,
    }
    try:
        with path.open("r", encoding="utf-8", errors="replace", newline="") as handle:
            reader = csv.DictReader(handle)
            if not reader.fieldnames:
                result["error"] = "empty_header"
                return result
            fieldnames = {name.strip() for name in reader.fieldnames if name}
            if "time" not in fieldnames:
                result["error"] = "missing_time_column"
                return result
            for raw_row in reader:
                if not raw_row or not any(value not in (None, "") for value in raw_row.values()):
                    continue
                result["rows"] += 1
                row = {str(key).strip(): value for key, value in raw_row.items() if key}
                result["latest"] = row
                current_time = _finite_number(row.get("time"))
                if current_time is not None:
                    result["latest_time"] = current_time
                step = _finite_number(
                    row.get("nearest_systemstep", row.get("min_systemstep", row.get("systemstep")))
                )
                # Zero/negative values are missing sentinels, not positive
                # Systemsteps.  The contract asks for the minimum positive
                # value.
                if step is not None and step > 0:
                    previous = result.get("min_systemstep")
                    result["min_systemstep"] = step if previous is None else min(previous, step)
                interactions = _number_or_none(
                    row.get("ninteractions_total", row.get("ninteractions", row.get("NInteractions")))
                )
                if interactions is not None:
                    result["ninteractions_final"] = interactions
    except (OSError, csv.Error, UnicodeError) as exc:
        result["error"] = type(exc).__name__
        return result

    if result["rows"] <= 0 or result["latest_time"] is None:
        result["error"] = result["error"] or "no_data_rows"
        return result
    result["valid"] = True
    latest_time = float(result["latest_time"])
    if time_max is not None:
        # Coverage is complete only when the metric itself reaches TimeMax;
        # the check_simulations one-snapshot tolerance is not sufficient for
        # an evidence table.
        result["status"] = "complete" if latest_time >= 0.995 * time_max else "partial"
    elif expected_snapshots and result["rows"] >= expected_snapshots:
        result["status"] = "complete"
    else:
        result["status"] = "partial"
    return result


def _snapshot_numbers(run_root: Path) -> list[int]:
    output = run_root / "output"
    if not output.is_dir():
        return []
    numbers: list[int] = []
    pattern = re.compile(r"^snapshot_?(\d+)\.hdf5$", re.IGNORECASE)
    try:
        entries = list(output.iterdir())
    except OSError:
        return []
    for path in entries:
        match = pattern.match(path.name)
        if match:
            numbers.append(int(match.group(1)))
    return sorted(set(numbers))


def _expected_snapshots(time_max: Optional[float], time_bet: Optional[float]) -> Optional[int]:
    if time_max is None or time_bet in (None, 0):
        return None
    try:
        return int(float(time_max) / float(time_bet) + 1.0000001)
    except (TypeError, ValueError, ZeroDivisionError):
        return None


def _identity(run_root: Path, context_root: Optional[Path] = None) -> tuple[str, str, str]:
    """Return ``(run_id, group, run_path)`` with portable forward slashes."""

    resolved = run_root.resolve()
    # The repository convention is explicit: paths below the nearest ``runs``
    # component are relative to nbody/runs, independent of host/container
    # absolute prefixes.
    run_parts = resolved.parts
    runs_indices = [i for i, part in enumerate(run_parts) if part == "runs"]
    if runs_indices:
        relative = Path(*run_parts[runs_indices[-1] + 1 :])
    else:
        context = context_root.resolve() if context_root is not None else None
        if context is not None:
            try:
                relative = resolved.relative_to(context)
                if len(relative.parts) <= 1:
                    relative = Path(context.name) / relative
            except ValueError:
                relative = Path(resolved.parent.name) / resolved.name
        else:
            relative = Path(resolved.parent.name) / resolved.name
    run_id = relative.name or resolved.name
    group_path = relative.parent
    group = "." if str(group_path) in ("", ".") else group_path.as_posix()
    return run_id, group, relative.as_posix()


def _looks_like_run(path: Path) -> bool:
    if not path.is_dir():
        return False
    names = {".gizmo_run.param", ".gizmo_run.param-usedvalues", "run.log", "run.state"}
    try:
        if any((path / name).is_file() for name in names):
            return True
        output = path / "output"
        return output.is_dir() and any(output.glob("snapshot_*.hdf5"))
    except OSError:
        return False


def _iter_run_dirs(root: Path) -> Iterator[Path]:
    if _looks_like_run(root):
        yield root
        return
    if not root.is_dir():
        return
    # os.walk lets us prune output/plots and does not follow symlinks.  Once a
    # run directory is found, its nested files are never interpreted as runs.
    for current, dirs, _files in os.walk(root, topdown=True, followlinks=False):
        dirs[:] = sorted(d for d in dirs if d not in {"output", "plots", "partial_analysis", "configs", ".git", "__pycache__"})
        current_path = Path(current)
        if current_path != root and _looks_like_run(current_path):
            yield current_path
            dirs[:] = []


def _analysis_info(repo_root: Path) -> dict[str, Any]:
    info: dict[str, Any] = {
        "commit": None,
        "dirty": None,
        "patch_sha256": None,
    }
    try:
        commit = subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=repo_root, capture_output=True, text=True, check=False
        ).stdout.strip()
        info["commit"] = commit or None
        status = subprocess.run(
            ["git", "status", "--porcelain", "--", "nbody/scripts/analysis", "nbody/scripts/conference"],
            cwd=repo_root,
            capture_output=True,
            text=True,
            check=False,
        ).stdout
        info["dirty"] = bool(status.strip())
        if info["dirty"]:
            diff = subprocess.run(
                ["git", "diff", "--binary", "--", "nbody/scripts/analysis", "nbody/scripts/conference"],
                cwd=repo_root,
                capture_output=True,
                check=False,
            ).stdout
            chunks: list[bytes] = [diff]
            # git diff does not include untracked files.  Include their bytes
            # with path labels so the fingerprint remains meaningful while the
            # manifest itself is being developed.
            for prefix in (repo_root / "nbody" / "scripts" / "analysis", repo_root / "nbody" / "scripts" / "conference"):
                if not prefix.exists():
                    continue
                for path in sorted(prefix.rglob("*")):
                    if not path.is_file() or "__pycache__" in path.parts:
                        continue
                    try:
                        relative = path.relative_to(repo_root).as_posix().encode("utf-8")
                        chunks.extend((relative, b"\0", path.read_bytes(), b"\0"))
                    except OSError:
                        continue
            info["patch_sha256"] = _sha256_bytes(chunks)
    except (OSError, subprocess.SubprocessError):
        pass
    return info


def _solver_hashes(
    repo_root: Path,
    solver_source: Optional[str | Path] = None,
    solver_binary: Optional[str | Path] = None,
) -> tuple[Optional[str], Optional[str]]:
    source_candidates: list[Path] = []
    binary_candidates: list[Path] = []
    if solver_source:
        source_candidates.append(Path(solver_source))
    if solver_binary:
        binary_candidates.append(Path(solver_binary))
    env_root = os.environ.get("GIZMO_SOURCE_ROOT")
    if env_root:
        source_candidates.append(Path(env_root) / "sidm" / "sidm_core.c")
        binary_candidates.append(Path(env_root) / "GIZMO")
    source_candidates.extend((Path("/opt/gizmo-public/sidm/sidm_core.c"), repo_root / "gizmo-public" / "sidm" / "sidm_core.c"))
    binary_candidates.extend((Path("/opt/gizmo-public/GIZMO"), repo_root / "gizmo-public" / "GIZMO"))
    source_hash = next((digest for path in source_candidates if (digest := _sha256_file(path))), None)
    binary_hash = next((digest for path in binary_candidates if (digest := _sha256_file(path))), None)
    return source_hash, binary_hash


def _run_commit(run_root: Path, sources: Sequence[tuple[str, Path, Mapping[str, Any]]]) -> Optional[str]:
    patterns = [
        re.compile(r"(?:run[_ -]?commit|git[_ -]?commit|commit(?:[_ -]?sha)?)[^0-9a-f]{0,20}([0-9a-f]{7,40})", re.I),
    ]
    files: list[Path] = [path for _name, path, _values in sources]
    for name in ("experiment.md", "provenance.json", "manifest_metadata.json", "run_metadata.json", "README.md"):
        path = run_root / name
        if path.is_file():
            files.append(path)
    for path in files:
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        for pattern in patterns:
            match = pattern.search(text)
            if match:
                return match.group(1)
    return None


def _log_head_fields(text: str) -> dict[str, Any]:
    result: dict[str, Any] = {}
    ptype_counts: list[tuple[int, int]] = []
    for match in re.finditer(r"^\s*Type\s+(\d+)\s+\([^\n]*?\):\s+(\d+)", text, re.MULTILINE):
        ptype_counts.append((int(match.group(1)), int(match.group(2))))
    if ptype_counts:
        ptype, count = max(ptype_counts, key=lambda item: item[1])
        if count > 0:
            result["ptype"] = ptype
            result["n_particles"] = count
    match = re.search(r"contains\s+(\d+)\s+particles", text, re.I)
    if match and "n_particles" not in result:
        result["n_particles"] = int(match.group(1))
    match = re.search(r"Running on\s+(\d+)\s+MPI tasks", text, re.I)
    if match:
        result["mpi_procs"] = int(match.group(1))
    match = re.search(r"TimeLimitCPU[^\n]*defaulting[^=]*=\s*([0-9.eE+-]+)", text, re.I)
    if match:
        result["time_limit_cpu_default"] = _number_or_none(match.group(1))
    match = re.search(r"TimeOfFirstSnapshot[^\n]*defaulting[^=]*=\s*([0-9.eE+-]+)", text, re.I)
    if match:
        result["first_snapshot_default"] = _number_or_none(match.group(1))
    match = re.search(r"System time:\s*(.+)", text, re.I)
    if match:
        try:
            dt = datetime.strptime(match.group(1).strip(), "%a %b %d %H:%M:%S %Y").replace(tzinfo=timezone.utc)
            result["started_at_utc"] = dt.isoformat().replace("+00:00", "Z")
        except ValueError:
            pass
    return result


def _safe_relative(path: Path, root: Path) -> str:
    try:
        return path.relative_to(root).as_posix()
    except ValueError:
        return path.as_posix()


def read_run_manifest_row(
    run_root: str | Path,
    *,
    context_root: str | Path | None = None,
    hash_ics: bool = False,
    hash_cache: Optional[MutableMapping[str, str]] = None,
    analysis_info: Optional[Mapping[str, Any]] = None,
    repo_root: str | Path | None = None,
    solver_source: str | Path | None = None,
    solver_binary: str | Path | None = None,
    precomputed_solver_hashes: tuple[Optional[str], Optional[str]] | None = None,
) -> ManifestRow:
    """Read one run without mutating it or opening HDF5 datasets."""

    root = Path(run_root).expanduser().resolve()
    repository = Path(repo_root).expanduser().resolve() if repo_root else _repo_root()
    run_id, group, run_path = _identity(root, Path(context_root) if context_root else None)
    sources = _param_sources(root)
    selected, conflicts = _param_values(sources)

    log_path = root / "run.log"
    log = parse_log(log_path) if log_path.is_file() else {
        "exists": False,
        "latest": None,
        "previous_window": None,
        "small_dt_bins": [],
    }
    log_head = _log_head_fields(_read_head(log_path))
    state = _read_state(root / "run.state")
    numbers = _snapshot_numbers(root)
    snapshots_count = len(numbers)

    time_max = _number_or_none(selected.get("TimeMax"))
    time_bet = _number_or_none(selected.get("TimeBetSnapshot"))
    expected = _expected_snapshots(_finite_number(time_max), _finite_number(time_bet))
    # The existing verdict classifier is reused, but fed only text/filename
    # evidence.  It does not need snapshot metadata for its flags.
    report_snapshots = {
        "count": snapshots_count,
        "expected": expected,
        "latest_metadata": {},
    }
    report = {
        "state": state,
        "processes": find_processes(root),
        "params": {"selected": selected},
        "log": log,
        "snapshots": report_snapshots,
    }
    verdict = classify(report)
    flags = list(verdict.get("flags") or [])

    metrics_paths = _metrics_candidates(root)
    metrics_path = metrics_paths[0] if metrics_paths else None
    metric_info = _read_metrics(metrics_path, _finite_number(time_max), expected) if metrics_path else {
        "valid": False,
        "rows": 0,
        "latest_time": None,
        "latest": {},
        "min_systemstep": None,
        "ninteractions_final": None,
        "schema_version": None,
        "error": None,
    }
    if metric_info.get("min_systemstep") is not None and metric_info["min_systemstep"] < 1e-6:
        flags.append("timestep-collapse")
    flags = sorted(set(flags))

    # Missing run.log is intentionally unknown, even if snapshots happened to
    # be copied into the directory.  This avoids the old "missing => failed"
    # inference and keeps lifecycle status independent from metrics quality.
    if not log_path.is_file():
        status = UNKNOWN
        health = UNKNOWN
    else:
        status = str(verdict.get("status") or UNKNOWN)
        health = "pathological" if any(
            flag in {"timestep-collapse", "syncpoint-runaway", "stalled-time-progress"} for flag in flags
        ) else str(verdict.get("health") or UNKNOWN)
        # ``check_simulations`` tolerates one absent snapshot when deciding
        # that a run may be complete.  A provenance manifest must be stricter:
        # without an explicit completed state, a log that has not reached
        # TimeMax remains incomplete even if the snapshot count is close.
        latest_time = _finite_number((log.get("latest") or {}).get("time"))
        if (
            status == "completed"
            and _finite_number(time_max) is not None
            and (latest_time is None or latest_time < 0.995 * float(time_max))
        ):
            status = "incomplete"
    raw_verdict = {
        "status": status,
        "health": health,
        "flags": flags,
        "classifier_status": verdict.get("status"),
        "classifier_health": verdict.get("health"),
    }

    latest_log = log.get("latest") or {}
    reached_candidates = [
        value for value in (
            _finite_number(latest_log.get("time")),
            _finite_number(metric_info.get("latest_time")),
        ) if value is not None
    ]
    t_reached = reached_candidates[0] if reached_candidates else None
    if latest_log.get("time") is None and metric_info.get("latest_time") is not None:
        t_reached = metric_info["latest_time"]

    log_steps: list[float] = []
    if log_path.is_file():
        try:
            log_steps = [point.systemstep for point in parse_sync_points(log_path)]
        except (OSError, UnicodeError, ValueError):
            log_steps = []
    min_steps = [step for step in log_steps if step > 0 and step == step and abs(step) != float("inf")]
    if metric_info.get("min_systemstep") is not None:
        min_steps.append(float(metric_info["min_systemstep"]))
    min_systemstep = min(min_steps) if min_steps else None

    latest_metrics = metric_info.get("latest") or {}
    ninteractions_final = metric_info.get("ninteractions_final")
    if ninteractions_final is None:
        ninteractions_final = _number_or_none(
            latest_metrics.get("ninteractions_total", latest_metrics.get("ninteractions"))
        )

    ic_path = _normalise_path_text(selected.get("InitCondFile"))
    spin_k, spin_source = _spin_from_ic(ic_path)
    ic_sha256 = None
    ic_source = _ic_source_path(ic_path, root, repository)
    if hash_ics and ic_source is not None:
        cache_key = str(ic_source.resolve())
        if hash_cache is not None and cache_key in hash_cache:
            ic_sha256 = hash_cache[cache_key]
        else:
            ic_sha256 = _sha256_file(ic_source)
            if ic_sha256 and hash_cache is not None:
                hash_cache[cache_key] = ic_sha256

    sigma = _number_or_none(selected.get("DM_InteractionCrossSection"))
    dissipation = _number_or_none(selected.get("DM_DissipationFactor"))
    kick = _number_or_none(selected.get("DM_KickPerCollision"))
    velocity_scale = _number_or_none(selected.get("DM_InteractionVelocityScale"))
    # Confirmed CDM mode permits a meaningful zero for omitted SIDM-only
    # controls; never apply this rule when sigma itself is unknown.
    if _finite_number(sigma) == 0:
        if dissipation is None:
            dissipation = 0
        if kick is None:
            kick = 0
        if velocity_scale is None:
            velocity_scale = 0

    ptype = log_head.get("ptype")
    n_particles = log_head.get("n_particles")
    metric_particles = _number_or_none(latest_metrics.get("particles"))
    if metric_particles is not None:
        n_particles = metric_particles

    if ptype is not None:
        softening_map = {0: "SofteningGas", 1: "SofteningHalo", 2: "SofteningDisk", 3: "SofteningBulge", 4: "SofteningStars", 5: "SofteningBndry"}
        softening_parameter = softening_map.get(int(ptype))
    else:
        softening_parameter = None
    softening = _number_or_none(selected.get(softening_parameter)) if softening_parameter else None

    mpi_procs = _number_or_none(log_head.get("mpi_procs"))
    if mpi_procs is None:
        for path in (root / "experiment.md", root / "README.md"):
            try:
                text = path.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue
            match = re.search(r"MPI\s+procs\s*:\s*(\d+)", text, re.I)
            if match:
                mpi_procs = int(match.group(1))
                break

    time_limit = _number_or_none(selected.get("TimeLimitCPU"))
    if time_limit is None:
        time_limit = _number_or_none(log_head.get("time_limit_cpu_default"))
    first_snapshot = _number_or_none(selected.get("TimeOfFirstSnapshot"))
    if first_snapshot is None:
        first_snapshot = _number_or_none(log_head.get("first_snapshot_default"))

    timing_source = None
    wall_minutes = _number_or_none(state.get("ELAPSED_MIN"))
    if wall_minutes is not None:
        timing_source = "run.state"
    started_at = log_head.get("started_at_utc")
    ended_at = None
    if state.get("TIMESTAMP"):
        try:
            dt = datetime.strptime(state["TIMESTAMP"], "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc)
            ended_at = dt.isoformat().replace("+00:00", "Z")
            if started_at is None:
                started_at = ended_at
        except ValueError:
            pass
    if timing_source is None and (started_at or ended_at):
        timing_source = "log_header_estimated"

    analysis = dict(analysis_info or _analysis_info(repository))
    if precomputed_solver_hashes is None:
        solver_source_hash, solver_binary_hash = _solver_hashes(repository, solver_source, solver_binary)
    else:
        solver_source_hash, solver_binary_hash = precomputed_solver_hashes

    notes: list[str] = []
    if not log_path.is_file():
        notes.append("log=missing;status=unknown")
    if not sources:
        notes.append("parameters=missing")
    if conflicts:
        notes.append("parameter_conflict=" + ",".join(sorted(conflicts)))
    if not metrics_paths:
        notes.append("metrics=missing")
    elif len(metrics_paths) > 1:
        metric_hashes = {_sha256_file(path) for path in metrics_paths}
        if len(metric_hashes) > 1:
            notes.append("metrics_source_conflict=" + ",".join(_safe_relative(path, root) for path in metrics_paths))
        else:
            notes.append("metrics_sources_duplicate=" + ",".join(_safe_relative(path, root) for path in metrics_paths))
    if metric_info.get("error"):
        notes.append("metrics=" + str(metric_info["error"]))
    if not ic_sha256:
        notes.append("ic_sha256=not_requested_or_unavailable")
    if ic_source is None and ic_path:
        notes.append("ic_source=unresolved:" + ic_path)
    if not analysis.get("commit"):
        notes.append("analysis_commit=unknown")
    if not solver_source_hash:
        notes.append("solver_source_sha256=unknown")
    if not solver_binary_hash:
        notes.append("solver_binary_sha256=unknown")
    if ptype is None:
        notes.append("ptype=unknown")
    if metric_info.get("min_systemstep") is not None and metric_info["min_systemstep"] < 1e-6:
        notes.append("pathology=timestep_collapse_from_metrics")
    if log_path.is_file() and log.get("sync_points_seen_tail") is not None:
        notes.append("log_parser=bounded_tail")
    notes = sorted(set(notes))

    if conflicts:
        provenance_status = "conflict"
    elif not sources or not log_path.is_file():
        provenance_status = "missing"
    elif not _run_commit(root, sources):
        # The absence of historical run provenance is a distinct unknown, not
        # a claim that the run used the current checkout.
        provenance_status = UNKNOWN
        notes.append("run_commit=unknown:no_evidence")
    elif not ic_sha256 or not solver_source_hash or not solver_binary_hash:
        provenance_status = UNKNOWN
    else:
        provenance_status = "ok"
    notes = sorted(set(notes))

    evidence_paths = [path for _name, path, _values in sources]
    for path in (log_path, root / "run.state", metrics_path):
        if path is not None and path.is_file():
            evidence_paths.append(path)
    checked_at = None
    mtimes: list[float] = []
    for path in evidence_paths:
        try:
            mtimes.append(path.stat().st_mtime)
        except OSError:
            pass
    if mtimes:
        checked_at = datetime.fromtimestamp(max(mtimes), tz=timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")

    metrics_status = "missing"
    if metrics_path is not None:
        metrics_status = "invalid" if not metric_info.get("valid") else str(metric_info.get("status") or "partial")

    return ManifestRow(
        run_id=run_id,
        group=group,
        run_path=run_path,
        ic_path=ic_path,
        ic_sha256=ic_sha256,
        spin_k=spin_k,
        spin_k_source=spin_source,
        n_particles=int(n_particles) if isinstance(n_particles, (int, float)) else None,
        ptype=int(ptype) if isinstance(ptype, (int, float)) else None,
        sigma_over_m=_number_or_none(sigma),
        dissipation_d=_number_or_none(dissipation),
        kick_velocity=_number_or_none(kick),
        velocity_scale=_number_or_none(velocity_scale),
        softening_value=_number_or_none(softening),
        softening_parameter=softening_parameter,
        max_size_timestep=_number_or_none(selected.get("MaxSizeTimestep")),
        time_max=_number_or_none(time_max),
        time_bet_snapshot=_number_or_none(time_bet),
        first_snapshot=first_snapshot,
        time_limit_cpu=time_limit,
        mpi_procs=int(mpi_procs) if isinstance(mpi_procs, (int, float)) else None,
        run_commit=_run_commit(root, sources),
        analysis_commit=analysis.get("commit"),
        analysis_dirty=analysis.get("dirty"),
        analysis_patch_sha256=analysis.get("patch_sha256"),
        params_sha256=_hash_params(sources),
        solver_source_sha256=solver_source_hash,
        solver_binary_sha256=solver_binary_hash,
        snapshots=snapshots_count,
        t_reached=t_reached,
        min_systemstep=min_systemstep,
        ninteractions_final=ninteractions_final,
        status=status,
        health=health,
        metrics_status=metrics_status,
        verdict_raw=_canonical_json(raw_verdict),
        metrics_csv=_safe_relative(metrics_path, root) if metrics_path else None,
        analysis_schema_version=metric_info.get("schema_version") if metric_info.get("valid") else None,
        checked_at_utc=checked_at,
        started_at_utc=started_at,
        ended_at_utc=ended_at,
        wall_minutes=wall_minutes,
        timing_source=timing_source,
        provenance_status=provenance_status,
        notes=";".join(notes),
    )


def scan_runs(
    roots: str | Path | Sequence[str | Path],
    *,
    hash_ics: bool = False,
    repo_root: str | Path | None = None,
    solver_source: str | Path | None = None,
    solver_binary: str | Path | None = None,
) -> list[ManifestRow]:
    """Scan explicit roots recursively and return sorted unique rows."""

    if isinstance(roots, (str, Path)):
        root_values: list[str | Path] = [roots]
    else:
        root_values = list(roots)
    repository = Path(repo_root).expanduser().resolve() if repo_root else _repo_root()
    resolved_roots: list[Path] = []
    for value in root_values:
        raw = Path(value).expanduser()
        mapped = _map_container_path(str(raw), repository) if not raw.exists() else raw
        resolved = mapped.resolve()
        if resolved not in resolved_roots:
            resolved_roots.append(resolved)
    resolved_roots.sort(key=lambda path: path.as_posix())
    analysis = _analysis_info(repository)
    solver_hashes = _solver_hashes(repository, solver_source, solver_binary)
    hash_cache: dict[str, str] = {}
    rows: list[ManifestRow] = []
    seen_dirs: set[Path] = set()
    for root in resolved_roots:
        for run_root in sorted(_iter_run_dirs(root), key=lambda path: path.as_posix()):
            real = run_root.resolve()
            if real in seen_dirs:
                continue
            seen_dirs.add(real)
            row = read_run_manifest_row(
                real,
                context_root=root,
                hash_ics=hash_ics,
                hash_cache=hash_cache,
                analysis_info=analysis,
                repo_root=repository,
                solver_source=solver_source,
                solver_binary=solver_binary,
                precomputed_solver_hashes=solver_hashes,
            )
            rows.append(row)
    rows.sort(key=lambda row: (row.group, row.run_id, row.run_path))
    seen_keys: set[tuple[str, str]] = set()
    duplicates: list[str] = []
    for row in rows:
        key = (row.group, row.run_id)
        if key in seen_keys:
            duplicates.append(f"{row.group}/{row.run_id}")
        seen_keys.add(key)
    if duplicates:
        raise ValueError("duplicate group/run_id: " + ", ".join(sorted(duplicates)))
    return rows


def _csv_value(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, float):
        if value != value or abs(value) == float("inf"):
            return ""
        return repr(value)
    return str(value)


def write_manifest_csv(rows: Iterable[ManifestRow | Mapping[str, Any]], out: str | Path) -> Path:
    """Write stable columns/ordering and reject duplicate group/run keys."""

    normalised: list[ManifestRow | Mapping[str, Any]] = list(rows)
    records: list[dict[str, Any]] = []
    for row in normalised:
        record = row.as_dict() if isinstance(row, ManifestRow) else {key: row.get(key) for key in MANIFEST_COLUMNS}
        records.append(record)
    records.sort(key=lambda record: (str(record.get("group") or ""), str(record.get("run_id") or ""), str(record.get("run_path") or "")))
    seen: set[tuple[str, str]] = set()
    for record in records:
        key = (str(record.get("group") or ""), str(record.get("run_id") or ""))
        if key in seen:
            raise ValueError(f"duplicate group/run_id: {key[0]}/{key[1]}")
        seen.add(key)

    destination = Path(out).expanduser()
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle, lineterminator="\n")
        writer.writerow(MANIFEST_COLUMNS)
        for record in records:
            writer.writerow([_csv_value(record.get(key)) for key in MANIFEST_COLUMNS])
    return destination


def write_manifest_metadata(
    rows: Sequence[ManifestRow],
    out: str | Path,
    *,
    roots: Optional[Sequence[str | Path]] = None,
    hash_ics: bool = False,
) -> Path:
    """Write compact, deterministic provenance next to a CSV package."""

    payload = {
        "schema_version": SCHEMA_VERSION,
        "columns": MANIFEST_COLUMNS,
        "row_count": len(rows),
        "roots": [str(Path(root)) for root in roots] if roots else [],
        "hash_ics": bool(hash_ics),
        "checked_at_semantics": "derived_from_newest_evidence_mtime",
        "analysis_commits": sorted({row.analysis_commit for row in rows if row.analysis_commit}),
        "analysis_dirty": sorted({row.analysis_dirty for row in rows if row.analysis_dirty is not None}),
        "status_counts": {status: sum(row.status == status for row in rows) for status in sorted({row.status for row in rows})},
        "health_counts": {health: sum(row.health == health for row in rows) for health in sorted({row.health for row in rows})},
        "metrics_status_counts": {
            status: sum(row.metrics_status == status for row in rows)
            for status in sorted({row.metrics_status for row in rows})
        },
    }
    destination = Path(out).expanduser()
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return destination


def _build_cli() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--roots", nargs="+", required=True, help="Explicit host/container run or group roots")
    parser.add_argument("--out", required=True, help="CSV destination")
    parser.add_argument("--metadata-out", help="Optional deterministic JSON provenance destination")
    parser.add_argument("--hash-ics", action="store_true", help="Hash each distinct IC once (otherwise record unknown)")
    parser.add_argument("--repo-root", help="Repository root for /nbody mapping and analysis revision")
    parser.add_argument("--solver-source", help="Optional sidm_core.c path")
    parser.add_argument("--solver-binary", help="Optional GIZMO binary path")
    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = _build_cli().parse_args(argv)
    rows = scan_runs(
        args.roots,
        hash_ics=args.hash_ics,
        repo_root=args.repo_root,
        solver_source=args.solver_source,
        solver_binary=args.solver_binary,
    )
    write_manifest_csv(rows, args.out)
    if args.metadata_out:
        write_manifest_metadata(rows, args.metadata_out, roots=args.roots, hash_ics=args.hash_ics)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
