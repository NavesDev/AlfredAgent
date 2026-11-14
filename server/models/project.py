"""Projects group workspaces; a workspace is any folder, or a git worktree made from one."""

import json
import sqlite3
from typing import Literal

from pydantic import BaseModel

WorkspaceKind = Literal["folder", "worktree"]


class Workspace(BaseModel):
    id: int
    project_id: int
    name: str
    path: str
    kind: WorkspaceKind
    parent_id: int | None = None
    branch: str | None = None
    description: str = ""


class Project(BaseModel):
    id: int
    name: str
    aliases: list[str]
    description: str = ""
    workspaces: list[Workspace] = []


def _workspace(row: sqlite3.Row) -> Workspace:
    return Workspace(**{k: row[k] for k in Workspace.model_fields})


def _project(db: sqlite3.Connection, row: sqlite3.Row) -> Project:
    return Project(
        id=row["id"],
        name=row["name"],
        aliases=json.loads(row["aliases"]),
        description=row["description"],
        workspaces=workspaces_of(db, row["id"]),
    )


def insert_project(
    db: sqlite3.Connection, name: str, aliases: list[str], description: str = ""
) -> Project:
    cursor = db.execute(
        "INSERT INTO project (name, aliases, description) VALUES (?, ?, ?)",
        (name, json.dumps(aliases), description),
    )
    return Project(id=cursor.lastrowid or 0, name=name, aliases=aliases, description=description)


def get_project(db: sqlite3.Connection, id: int) -> Project | None:
    row = db.execute("SELECT * FROM project WHERE id = ?", (id,)).fetchone()
    return _project(db, row) if row else None


def list_projects(db: sqlite3.Connection) -> list[Project]:
    return [_project(db, row) for row in db.execute("SELECT * FROM project ORDER BY id")]


def find_project(db: sqlite3.Connection, name: str) -> Project | None:
    """By name or alias, ignoring case."""
    wanted = name.strip().lower()
    for p in list_projects(db):
        if wanted == p.name.lower() or wanted in (a.lower() for a in p.aliases):
            return p
    return None


def update_project(
    db: sqlite3.Connection,
    id: int,
    name: str | None = None,
    aliases: list[str] | None = None,
    description: str | None = None,
) -> None:
    if name is not None:
        db.execute("UPDATE project SET name = ? WHERE id = ?", (name, id))
    if aliases is not None:
        db.execute("UPDATE project SET aliases = ? WHERE id = ?", (json.dumps(aliases), id))
    if description is not None:
        db.execute("UPDATE project SET description = ? WHERE id = ?", (description, id))


def delete_project(db: sqlite3.Connection, id: int) -> None:
    db.execute("DELETE FROM project WHERE id = ?", (id,))


def insert_workspace(
    db: sqlite3.Connection,
    project_id: int,
    name: str,
    path: str,
    kind: WorkspaceKind,
    parent_id: int | None = None,
    branch: str | None = None,
    description: str = "",
) -> Workspace:
    cursor = db.execute(
        "INSERT INTO workspace (project_id, name, path, kind, parent_id, branch, description)"
        " VALUES (?, ?, ?, ?, ?, ?, ?)",
        (project_id, name, path, kind, parent_id, branch, description),
    )
    return Workspace(
        id=cursor.lastrowid or 0,
        project_id=project_id,
        name=name,
        path=path,
        kind=kind,
        parent_id=parent_id,
        branch=branch,
        description=description,
    )


def get_workspace(db: sqlite3.Connection, id: int) -> Workspace | None:
    row = db.execute("SELECT * FROM workspace WHERE id = ?", (id,)).fetchone()
    return _workspace(row) if row else None


def workspaces_of(db: sqlite3.Connection, project_id: int) -> list[Workspace]:
    rows = db.execute("SELECT * FROM workspace WHERE project_id = ? ORDER BY id", (project_id,))
    return [_workspace(row) for row in rows]


def update_workspace(db: sqlite3.Connection, id: int, description: str) -> None:
    db.execute("UPDATE workspace SET description = ? WHERE id = ?", (description, id))


def delete_workspace(db: sqlite3.Connection, id: int) -> None:
    db.execute("DELETE FROM workspace WHERE id = ?", (id,))
