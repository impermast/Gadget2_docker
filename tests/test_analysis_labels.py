from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = REPO_ROOT / "nbody" / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from analysis.labels import compact_run_label  # noqa: E402


def test_compact_run_labels_keep_model_and_parameters():
    assert compact_run_label("20261012_cdm_rotN1e6_T1") == "CDM (12 Oct)"
    assert compact_run_label("20261012_sidm_s2p5_rotN1e6_T1") == "SIDM σ=2.5 (elastic)"
    assert compact_run_label("20261014_dsidm_s0p5_fdiss0p1_rotN1e6_T1") == "dSIDM σ=0.5, f=0.1"
    assert compact_run_label("20261015_dsidm_s0p5_f0p1_rotN1e6_T3_mpi10") == "dSIDM σ=0.5, f=0.1"
    assert compact_run_label("20261013_sidm_s1_fdiss0p5_rotN1e6_T1") == "SIDM σ=1, diss=0.5"


def test_compact_run_label_preserves_unknown_name():
    assert compact_run_label("custom_control_run") == "custom_control_run"
