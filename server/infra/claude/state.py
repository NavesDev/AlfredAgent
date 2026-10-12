"""Persist the main agent's Claude session id for the current day.

The session is also tied to a version of the agent's setup (prompt and tools): a conversation
started with an older setup is dropped, or the agent keeps using tools as they used to be.
"""

import json
from datetime import date
from pathlib import Path


class DailyState:
    def __init__(self, path: Path) -> None:
        self._path = path

    def session_for(self, day: date, version: str = "") -> str | None:
        if not self._path.exists():
            return None
        data = json.loads(self._path.read_text())
        if data["date"] != day.isoformat() or data.get("version", "") != version:
            return None
        return str(data["claude_session_id"])

    def save(self, session_id: str, day: date, version: str = "") -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._path.write_text(
            json.dumps(
                {"date": day.isoformat(), "version": version, "claude_session_id": session_id}
            )
        )
