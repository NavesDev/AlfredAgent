"""Results a session or Alfred hands over to be seen: files and/or a change report (ADR 0014).

The stored record keeps absolute paths; what the panel sees (controllers/results.py) never does.
"""

import json
import sqlite3
from datetime import UTC, datetime
from pathlib import PurePath
from typing import Literal

from pydantic import BaseModel

Source = Literal["session", "alfred"]
PresentMode = Literal["card", "ampliado"]
Kind = Literal["image", "video", "pdf", "markdown", "text", "html", "other"]

MAX_PER_SESSION = 30

_KINDS: dict[str, Kind] = {
    **dict.fromkeys(("png", "jpg", "jpeg", "webp", "gif", "svg"), "image"),
    **dict.fromkeys(("mp4", "webm", "mov"), "video"),
    "pdf": "pdf",
    "md": "markdown",
    **dict.fromkeys(("html", "htm"), "html"),
    **dict.fromkeys(
        (
            "txt", "log", "json", "yaml", "yml", "toml", "csv", "py", "ts", "tsx", "js", "jsx",
            "rs", "go", "java", "kt", "c", "h", "cpp", "sh", "sql", "css", "xml",
        ),
        "text",
    ),
}  # fmt: skip


class FileChange(BaseModel):
    path: str
    added: int
    removed: int


class ResultRecord(BaseModel):
    id: int
    session_id: int | None  # None: Alfred's own
    source: Source
    title: str
    summary: str | None = None
    report: str | None = None
    changes: list[FileChange] = []
    files: list[str] = []  # absolute paths
    created_at: float


def kind_of(name: str) -> Kind:
    return _KINDS.get(PurePath(name).suffix.lower().lstrip("."), "other")


def _record(row: sqlite3.Row) -> ResultRecord:
    created = datetime.strptime(row["created_at"], "%Y-%m-%d %H:%M:%S").replace(tzinfo=UTC)
    return ResultRecord(
        id=row["id"],
        session_id=row["session_id"],
        source=row["source"],
        title=row["title"],
        summary=row["summary"],
        report=row["report"],
        changes=[FileChange(**c) for c in json.loads(row["changes"])],
        files=json.loads(row["files"]),
        created_at=created.timestamp(),
    )


def insert_result(
    db: sqlite3.Connection,
    session_id: int | None,
    source: Source,
    title: str,
    summary: str | None = None,
    report: str | None = None,
    changes: list[FileChange] | None = None,
    files: list[str] | None = None,
) -> ResultRecord:
    cursor = db.execute(
        "INSERT INTO result (session_id, source, title, summary, report, changes, files)"
        " VALUES (?, ?, ?, ?, ?, ?, ?)",
        (
            session_id,
            source,
            title,
            summary,
            report,
            json.dumps([c.model_dump() for c in changes or []]),
            json.dumps(files or []),
        ),
    )
    record = get_result(db, cursor.lastrowid or 0)
    assert record is not None
    return record


def get_result(db: sqlite3.Connection, result_id: int) -> ResultRecord | None:
    row = db.execute("SELECT * FROM result WHERE id = ?", (result_id,)).fetchone()
    return _record(row) if row else None


def list_results(
    db: sqlite3.Connection, session_id: int | None, limit: int = MAX_PER_SESSION
) -> list[ResultRecord]:
    """Newest first; session_id None lists Alfred's own."""
    rows = db.execute(
        "SELECT * FROM result WHERE session_id IS ? ORDER BY id DESC LIMIT ?", (session_id, limit)
    )
    return [_record(row) for row in rows]


def prune(db: sqlite3.Connection, session_id: int | None, keep: int = MAX_PER_SESSION) -> None:
    """Deletes all but the newest `keep` rows of a session (files stay on disk)."""
    db.execute(
        "DELETE FROM result WHERE session_id IS ? AND id NOT IN"
        " (SELECT id FROM result WHERE session_id IS ? ORDER BY id DESC LIMIT ?)",
        (session_id, session_id, keep),
    )


class ResultFile(BaseModel):
    name: str
    kind: Kind
    size: int
    exists: bool


class ResultView(BaseModel):
    id: int
    session: str  # "alfred" for Alfred's own
    source: Source
    title: str
    summary: str | None
    report: str | None
    changes: list[FileChange]
    files: list[ResultFile]  # never the path
    created_at: float
