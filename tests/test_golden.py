"""Level 2: answer testing against tests/golden/values.json.

Golden values are computed from the SAME deterministic synthetic fixture
(see make_golden.py), so this is fast and needs no real simulation data.
If a test fails here after an intentional loaders.py change, regenerate the
golden file with `python tests/make_golden.py` and document why in
tests/golden/README.md (yt-style answer-version discipline).

Group marker: 'golden' (run alone via `pytest tests/ -m golden`).
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

import make_golden

pytestmark = pytest.mark.golden

GOLDEN_PATH = Path(__file__).resolve().parent / "golden" / "values.json"


@pytest.fixture(scope="module")
def golden():
    assert GOLDEN_PATH.exists(), (
        f"{GOLDEN_PATH} missing — run `python tests/make_golden.py` first")
    return json.loads(GOLDEN_PATH.read_text())


def test_golden_reproduced(snap_full, loaders_mod, golden):
    metrics = make_golden.compute_metrics(snap_full)

    mismatches = []
    for key, expected in golden.items():
        if key.startswith("_"):
            continue
        actual = metrics[key]
        if isinstance(expected, list):
            for i, (e, a) in enumerate(zip(expected, actual)):
                if e != pytest.approx(a, rel=1e-9):
                    mismatches.append(f"{key}[{i}]: {e!r} != {a!r}")
        elif isinstance(expected, int) and not isinstance(expected, bool):
            if expected != int(actual):
                mismatches.append(f"{key}: {expected} != {actual}")
        elif expected != pytest.approx(actual, rel=1e-9):
            mismatches.append(f"{key}: {expected!r} != {actual!r}")

    assert not mismatches, (
        "golden values diverged (loaders math changed?):\n  " +
        "\n  ".join(mismatches))


def test_golden_provenance_present(golden):
    prov = golden.get("_provenance", {})
    assert prov.get("seed") == 42
    assert "git_commit_at_generation" in prov
