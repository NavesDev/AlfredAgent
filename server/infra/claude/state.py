"""Persist the main agent's Claude session id for the current day."""

import json
from datetime import date
from pathlib import Path


class DailyState:
    def __init__(self, path: Path) -> None:
        self._path = path

    def session_for(self, day: date) -> str | None:
        if not self._path.exists():
            return None
        data = json.loads(self._path.read_text())
        return data["claude_session_id"] if data["date"] == day.isoformat() else None

    def save(self, session_id: str, day: date) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._path.write_text(
            json.dumps({"date": day.isoformat(), "claude_session_id": session_id})
        )
