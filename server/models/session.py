"""Named sessions: the stored record, and what the panel and Alfred see of one."""

import json
import sqlite3
from typing import Any, Literal

from pydantic import BaseModel

Status = Literal["idle", "busy", "error"]


class SessionRecord(BaseModel):
    id: int
    name: str
    aliases: list[str] = []
    kind: str
    workspace_id: int | None = None
    model: str | None = None
    effort: str | None = None
    claude_session_id: str | None = None
    protected: bool = False


Phase = Literal["exploring", "editing", "running"]
SubagentStatus = Literal["running", "completed", "failed", "stopped"]


class SubagentView(BaseModel):
    id: str
    type: str
    description: str
    last_tool: str | None = None
    status: SubagentStatus = "running"


class SessionView(BaseModel):
    name: str
    aliases: list[str]  # spoken alternatives, for names Whisper gets wrong
    kind: str
    label: str
    model: str
    effort: str | None
    cwd: str
    project: str | None
    workspace: str | None
    branch: str | None
    status: Status
    phase: Phase | None
    task: str | None
    activity: str | None
    queue: int
    waiting: bool  # every slot is busy; the next task waits for one
    connected: bool  # a claude process is open
    tasks_done: int
    tokens: int
    context_tokens: int | None  # how full its context window was after the last task
    context_max: int | None  # the model's context window
    last_summary: str | None
    last_error: str | None  # why the last task failed, until the next one starts
    protected: bool
    subagents: list[SubagentView]


def _record(row: sqlite3.Row) -> SessionRecord:
    fields = {k: row[k] for k in SessionRecord.model_fields}
    return SessionRecord(**{**fields, "aliases": json.loads(fields["aliases"])})


def insert_session(
    db: sqlite3.Connection,
    name: str,
    kind: str,
    workspace_id: int | None = None,
    model: str | None = None,
    effort: str | None = None,
    protected: bool = False,
    aliases: list[str] | None = None,
) -> SessionRecord:
    aliases = aliases or []
    cursor = db.execute(
        "INSERT INTO session (name, aliases, kind, workspace_id, model, effort, protected)"
        " VALUES (?, ?, ?, ?, ?, ?, ?)",
        (name, json.dumps(aliases), kind, workspace_id, model, effort, int(protected)),
    )
    return SessionRecord(
        id=cursor.lastrowid or 0,
        name=name,
        aliases=aliases,
        kind=kind,
        workspace_id=workspace_id,
        model=model,
        effort=effort,
        protected=protected,
    )


def list_sessions(db: sqlite3.Connection) -> list[SessionRecord]:
    return [_record(row) for row in db.execute("SELECT * FROM session ORDER BY id")]


def get_session(db: sqlite3.Connection, name: str) -> SessionRecord | None:
    row = db.execute("SELECT * FROM session WHERE name = ?", (name,)).fetchone()
    return _record(row) if row else None


_UPDATABLE = {"model", "effort", "claude_session_id", "aliases"}


def update_session(db: sqlite3.Connection, name: str, **fields: Any) -> None:
    """Only aliases, model, effort and claude_session_id change after creation."""
    assert set(fields) <= _UPDATABLE, set(fields) - _UPDATABLE
    if "aliases" in fields:
        fields["aliases"] = json.dumps(fields["aliases"])
    for key, value in fields.items():
        db.execute(f"UPDATE session SET {key} = ? WHERE name = ?", (value, name))


def delete_session(db: sqlite3.Connection, name: str) -> None:
    db.execute("DELETE FROM session WHERE name = ?", (name,))


def sessions_in_workspace(db: sqlite3.Connection, workspace_id: int) -> list[str]:
    rows = db.execute(
        "SELECT name FROM session WHERE workspace_id = ? ORDER BY id", (workspace_id,)
    )
    return [row["name"] for row in rows]
