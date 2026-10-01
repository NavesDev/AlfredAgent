from datetime import date
from pathlib import Path

from infra.claude.state import DailyState

TODAY = date(2026, 10, 1)


def test_missing_file_has_no_session(tmp_path: Path) -> None:
    assert DailyState(tmp_path / "s.json").session_for(TODAY) is None


def test_same_day_returns_saved_session(tmp_path: Path) -> None:
    DailyState(tmp_path / "s.json").save("abc", TODAY)

    assert DailyState(tmp_path / "s.json").session_for(TODAY) == "abc"


def test_new_day_drops_old_session(tmp_path: Path) -> None:
    state = DailyState(tmp_path / "s.json")
    state.save("abc", date(2026, 9, 30))

    assert state.session_for(TODAY) is None


def test_save_creates_parent_dirs(tmp_path: Path) -> None:
    DailyState(tmp_path / "data" / "s.json").save("abc", TODAY)

    assert (tmp_path / "data" / "s.json").exists()
