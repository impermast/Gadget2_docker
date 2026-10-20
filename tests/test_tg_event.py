from pathlib import Path
import sys


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "nbody" / "tg"))
from tg_event import progress_cooldown_remaining  # noqa: E402


def test_progress_cooldown_is_per_run_and_defaults_to_thirty_minutes(tmp_path):
    state_file = tmp_path / "run.state"
    marker = tmp_path / ".tg_progress_last_sent"
    marker.write_text("1000\n")

    assert progress_cooldown_remaining(str(state_file), now=1000) == 1800
    assert progress_cooldown_remaining(str(state_file), now=2700) == 100
    assert progress_cooldown_remaining(str(state_file), now=2800) == 0


def test_progress_cooldown_allows_first_notification(tmp_path):
    state_file = tmp_path / "run.state"

    assert progress_cooldown_remaining(str(state_file), now=1000) == 0
