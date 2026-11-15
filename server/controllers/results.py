"""Results sessions and Alfred hand over to be seen (ADR 0014).

A session's final reply records one through APRESENTAR/GUARDAR lines; Alfred shows the last one
or a file it found. Every file passes the read guard when recorded and again when served.
"""

import logging
import os
import sqlite3
from pathlib import Path
from typing import Protocol

from errors import FileGone, GitError, ResultNotFound, ResultNotReadable, SessionNotFound
from events import EventBus
from infra import git as real_git
from infra.claude.permissions import readable
from infra.claude.summary import parse_presentation, parse_resumo, strip_control
from models import result as records
from models import session as sessions
from models.result import FileChange, PresentMode, ResultFile, ResultRecord, ResultView

ALFRED = "alfred"
TITLE_MAX = 80

log = logging.getLogger("alfred.results")


class Git(Protocol):
    async def head(self, path: Path) -> str | None: ...
    async def numstat(self, path: Path, base: str) -> list[FileChange]: ...


class Results:
    def __init__(
        self, db: sqlite3.Connection, bus: EventBus, home: Path, git: Git = real_git
    ) -> None:
        self._db, self._bus, self._home, self._git = db, bus, home, git

    async def head(self, cwd: Path) -> str | None:
        """Where a task starts, for its change report."""
        return await self._git.head(cwd)

    async def record(
        self, session: str, reply: str, cwd: Path | None, head: str | None
    ) -> ResultView | None:
        """Records what the reply asks for; shows it as a card on APRESENTAR."""
        asked = parse_presentation(reply)
        if asked is None:
            return None
        files = [str(p) for raw in asked.files if (p := self._checked(raw, session))]
        if not files and not asked.report:
            return None
        report, changes = None, []
        if asked.report:
            report = strip_control(reply)
            if cwd is not None and head is not None:
                try:
                    changes = await self._git.numstat(cwd, head)
                except GitError as e:
                    log.warning("change report of %s without numstat: %s", session, e)
        summary = parse_resumo(reply) or None
        title = summary or (Path(files[0]).name if files else "Relatório")
        record = records.insert_result(
            self._db,
            self._session_id(session),
            "session",
            title[:TITLE_MAX],
            summary,
            report,
            changes,
            files,
        )
        return self._publish(record, "card" if asked.show else None)

    def present_last(self, session: str, mode: PresentMode) -> ResultView:
        sid = self._session_id(session)
        last = records.list_results(self._db, sid, limit=1)
        if not last:
            raise ResultNotFound(f"A sessão {self._name(sid)} ainda não tem resultado.")
        return self._show(last[0], mode)

    def present_path(self, raw: str, mode: PresentMode) -> ResultView:
        """A file Alfred found becomes a result of its own and is shown."""
        path = Path(os.path.expanduser(raw.strip()))
        if not readable(path, self._home):
            raise ResultNotReadable("Não tenho acesso a esse arquivo.")
        if not path.is_file():
            raise ResultNotReadable("Não achei esse arquivo.")
        record = records.insert_result(self._db, None, "alfred", path.name, files=[str(path)])
        records.prune(self._db, None)
        self._bus.publish("result_created", result=self._view(record).model_dump())
        return self._show(record, mode)

    def present(self, result_id: int, mode: PresentMode) -> ResultView:
        return self._show(self._get(result_id), mode)

    def close(self) -> None:
        self._bus.publish("presentation_closed")

    def get(self, result_id: int) -> ResultView:
        return self._view(self._get(result_id))

    def list(self, session: str, limit: int = records.MAX_PER_SESSION) -> list[ResultView]:
        rows = records.list_results(self._db, self._session_id(session), limit)
        return [self._view(r) for r in rows]

    def file(self, result_id: int, index: int) -> Path:
        record = self._get(result_id)
        if not 0 <= index < len(record.files):
            raise ResultNotFound("Esse resultado não tem esse arquivo.")
        path = Path(record.files[index])
        if not readable(path, self._home):
            raise ResultNotReadable("Não tenho acesso a esse arquivo.")
        if not path.is_file():
            raise FileGone("Arquivo não existe mais.")
        return path

    # --- internals ---------------------------------------------------------------------------

    def _checked(self, raw: str, session: str) -> Path | None:
        path = Path(os.path.expanduser(raw))
        if readable(path, self._home) and path.is_file():
            return path
        log.warning("result of %s: dropped %s (outside the home, secret or missing)", session, raw)
        return None

    def _publish(self, record: ResultRecord, mode: PresentMode | None) -> ResultView:
        records.prune(self._db, record.session_id)
        view = self._view(record)
        self._bus.publish("result_created", result=view.model_dump())
        if mode is not None:
            self._bus.publish("result_presented", result=view.model_dump(), mode=mode)
        return view

    def _show(self, record: ResultRecord, mode: PresentMode) -> ResultView:
        view = self._view(record)
        self._bus.publish("result_presented", result=view.model_dump(), mode=mode)
        return view

    def _get(self, result_id: int) -> ResultRecord:
        record = records.get_result(self._db, result_id)
        if record is None:
            raise ResultNotFound("Esse resultado não existe.")
        return record

    def _session_id(self, spoken: str) -> int | None:
        """None for Alfred; else the session whose name or alias is `spoken`."""
        wanted = spoken.strip().lower()
        if wanted == ALFRED:
            return None
        for record in sessions.list_sessions(self._db):
            if wanted in (n.lower() for n in [record.name, *record.aliases]):
                return record.id
        raise SessionNotFound(f"Não existe sessão chamada {spoken}.")

    def _name(self, session_id: int | None) -> str:
        if session_id is None:
            return ALFRED
        row = self._db.execute("SELECT name FROM session WHERE id = ?", (session_id,)).fetchone()
        return str(row["name"]) if row else "?"

    def _view(self, record: ResultRecord) -> ResultView:
        return ResultView(
            id=record.id,
            session=self._name(record.session_id),
            source=record.source,
            title=record.title,
            summary=record.summary,
            report=record.report,
            changes=record.changes,
            files=[self._file_view(Path(p)) for p in record.files],
            created_at=record.created_at,
        )

    def _file_view(self, path: Path) -> ResultFile:
        exists = readable(path, self._home) and path.is_file()
        return ResultFile(
            name=path.name,
            kind=records.kind_of(path.name),
            size=path.stat().st_size if exists else 0,
            exists=exists,
        )
