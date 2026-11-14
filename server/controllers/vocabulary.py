"""Keeps the spoken vocabulary (session and project names, with aliases) current.

The listener thread reads `whisper_words` while the loop may replace it; swapping a str is
atomic, so it needs no lock.
"""

import sqlite3

from events import EventBus
from models import project, session
from models import vocabulary as words
from models.vocabulary import Term

CHANGES = {
    "session_created",
    "session_deleted",
    "session_status",
    "project_created",
    "project_updated",
    "project_deleted",
}


class Vocabulary:
    def __init__(self, db: sqlite3.Connection, bus: EventBus) -> None:
        self._db, self._bus = db, bus
        self._terms: list[Term] = []
        self.whisper_words = ""
        self.refresh()

    def refresh(self) -> None:
        sessions = [Term(s.name, tuple(s.aliases)) for s in session.list_sessions(self._db)]
        projects = [Term(p.name, tuple(p.aliases)) for p in project.list_projects(self._db)]
        self._terms = sessions + projects
        self.whisper_words = words.whisper_words(self._terms)

    def canonicalize(self, text: str) -> str:
        return words.canonicalize(text, self._terms)

    def hint(self) -> str:
        return words.hint(self._terms)

    async def run(self) -> None:
        queue = self._bus.subscribe()
        try:
            while True:
                if (await queue.get())["type"] in CHANGES:
                    self.refresh()
        finally:
            self._bus.unsubscribe(queue)
