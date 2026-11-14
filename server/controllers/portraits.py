"""Session portraits (ADR 0009): a background queue paints one at a time, files live in a folder.

New sessions and, on boot, sessions without a portrait get painted. A failure keeps the
monogram; the next boot or a request tries again. Never blocks creating a session.
"""

import asyncio
import contextlib
import logging
import sqlite3
from collections.abc import Awaitable, Callable
from pathlib import Path
from urllib.parse import quote

from controllers.settings import Settings, SettingsUpdate
from errors import AgentError, SessionNotFound
from events import EventBus
from infra.claude.agents import KINDS
from infra.claude.portrait import Painting, Subject
from models import project
from models import session as records

log = logging.getLogger("alfred.portraits")

# (subject, model, favorite MCP, disabled MCPs, cwd) -> painting
Paint = Callable[[Subject, str, str | None, tuple[str, ...], Path], Awaitable[Painting]]
EXTS = ("png", "jpg", "webp")


class Portraits:
    def __init__(
        self, db: sqlite3.Connection, bus: EventBus, settings: Settings, folder: Path, paint: Paint
    ) -> None:
        self._db, self._bus, self._settings = db, bus, settings
        self._folder, self._paint = folder, paint
        self._queue: asyncio.Queue[str] = asyncio.Queue()
        self._pending: set[str] = set()

    def file(self, name: str) -> Path | None:
        record = records.get_session(self._db, name)
        return self._file(record.id) if record else None

    def url(self, session_id: int, name: str) -> str | None:
        """Panel URL, versioned by the file's mtime so a new portrait skips the browser cache."""
        path = self._file(session_id)
        if path is None:
            return None
        return f"/api/sessions/{quote(name)}/portrait?v={int(path.stat().st_mtime)}"

    def request(self, name: str) -> None:
        """Paints (again) in the background."""
        record = records.get_session(self._db, name)
        if record is None:
            raise SessionNotFound(f"Não existe sessão chamada {name}.")
        self._enqueue(record.name)

    async def run(self) -> None:
        events = self._bus.subscribe()
        worker = asyncio.create_task(self._work())
        try:
            for record in records.list_sessions(self._db):
                if self._file(record.id) is None:
                    self._enqueue(record.name)
            while True:
                event = await events.get()
                if event["type"] == "session_created":
                    name = str(event["session"]["name"])
                    if self.file(name) is None:
                        self._enqueue(name)
                elif event["type"] == "session_deleted":
                    ids = {str(r.id) for r in records.list_sessions(self._db)}
                    await asyncio.to_thread(self._prune, ids)
        finally:
            self._bus.unsubscribe(events)
            worker.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await worker

    # --- internals ---------------------------------------------------------------------------

    def _enqueue(self, name: str) -> None:
        if name.lower() not in self._pending:
            self._pending.add(name.lower())
            self._queue.put_nowait(name)

    async def _work(self) -> None:
        while True:
            name = await self._queue.get()
            self._pending.discard(name.lower())
            try:
                await self._paint_one(name)
            except AgentError as e:
                log.warning("portrait of %s failed: %s", name, e)

    async def _paint_one(self, name: str) -> None:
        record = records.get_session(self._db, name)
        if record is None:
            return  # deleted while waiting
        app = self._settings.app()
        model, _ = self._settings.resolve("alfred", None, None)
        self._folder.mkdir(parents=True, exist_ok=True)
        painting = await self._paint(
            self._subject(record), model, app.image_mcp, tuple(app.mcp_disabled), self._folder
        )
        if records.get_session(self._db, name) is None:
            return
        await asyncio.to_thread(self._save, record.id, painting)
        if app.image_mcp is None and painting.server and self._settings.app().image_mcp is None:
            self._settings.update(SettingsUpdate(image_mcp=painting.server))
        self._bus.publish("portrait_updated", session=record.name)

    def _subject(self, record: records.SessionRecord) -> Subject:
        ws = project.get_workspace(self._db, record.workspace_id) if record.workspace_id else None
        proj = project.get_project(self._db, ws.project_id) if ws else None
        return Subject(
            name=record.name,
            kind=KINDS[record.kind].label,
            project=proj.name if proj else None,
            project_description=proj.description if proj else "",
            workspace=ws.name if ws else None,
            workspace_description=ws.description if ws else "",
        )

    def _file(self, session_id: int) -> Path | None:
        return next(
            (p for ext in EXTS if (p := self._folder / f"{session_id}.{ext}").is_file()), None
        )

    def _save(self, session_id: int, painting: Painting) -> None:
        for ext in EXTS:
            (self._folder / f"{session_id}.{ext}").unlink(missing_ok=True)
        (self._folder / f"{session_id}.{painting.ext}").write_bytes(painting.data)

    def _prune(self, ids: set[str]) -> None:
        """Drops portraits of sessions that no longer exist."""
        for path in self._folder.glob("*.*"):
            if path.suffix[1:] in EXTS and path.stem not in ids:
                path.unlink(missing_ok=True)
