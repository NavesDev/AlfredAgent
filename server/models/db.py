"""SQLite connection and schema. Operations are short and local, so they run on the loop."""

import sqlite3
from pathlib import Path

SCHEMA_VERSION = 4

_SCHEMA = """
CREATE TABLE IF NOT EXISTS project (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL UNIQUE COLLATE NOCASE,
    aliases TEXT NOT NULL DEFAULT '[]',
    description TEXT NOT NULL DEFAULT '',
    default_workspace_id INTEGER REFERENCES workspace(id) ON DELETE SET NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS workspace (
    id INTEGER PRIMARY KEY,
    project_id INTEGER NOT NULL REFERENCES project(id),
    name TEXT NOT NULL COLLATE NOCASE,
    path TEXT NOT NULL,
    kind TEXT NOT NULL CHECK (kind IN ('folder', 'worktree')),
    parent_id INTEGER REFERENCES workspace(id),
    branch TEXT,
    description TEXT NOT NULL DEFAULT '',
    implementation_mode TEXT CHECK (implementation_mode IN ('worktree', 'ambiente')),
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (project_id, name)
);
CREATE TABLE IF NOT EXISTS session (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL UNIQUE COLLATE NOCASE,
    aliases TEXT NOT NULL DEFAULT '[]',
    kind TEXT NOT NULL,
    workspace_id INTEGER REFERENCES workspace(id),
    model TEXT,
    effort TEXT,
    claude_session_id TEXT,
    protected INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS agent_settings (
    kind TEXT PRIMARY KEY,
    model TEXT NOT NULL,
    effort TEXT
);
CREATE TABLE IF NOT EXISTS app_settings (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
"""


def open_db(path: Path | str) -> sqlite3.Connection:
    if str(path) != ":memory:":
        Path(path).parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(path, isolation_level=None)  # autocommit: every call is one statement
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA foreign_keys = ON")
    db.executescript(_SCHEMA)
    _migrate(db)
    _default_workspaces(db)
    db.execute(f"PRAGMA user_version = {SCHEMA_VERSION}")
    return db


def _migrate(db: sqlite3.Connection) -> None:
    """Columns added after a table first shipped; CREATE TABLE IF NOT EXISTS skips them."""
    added = {
        ("session", "aliases"): "TEXT NOT NULL DEFAULT '[]'",  # version 2
        ("project", "description"): "TEXT NOT NULL DEFAULT ''",  # version 3
        ("workspace", "description"): "TEXT NOT NULL DEFAULT ''",  # version 3
        (
            "project",
            "default_workspace_id",
        ): "INTEGER REFERENCES workspace(id) ON DELETE SET NULL",  # version 4
        (
            "workspace",
            "implementation_mode",
        ): "TEXT CHECK (implementation_mode IN ('worktree', 'ambiente'))",  # version 4
    }
    for (table, column), kind in added.items():
        columns = {row["name"] for row in db.execute(f"PRAGMA table_info({table})")}
        if column not in columns:
            db.execute(f"ALTER TABLE {table} ADD COLUMN {column} {kind}")


def _default_workspaces(db: sqlite3.Connection) -> None:
    """A project without a default workspace gets its first folder (version 4)."""
    db.execute(
        "UPDATE project SET default_workspace_id = (SELECT MIN(id) FROM workspace"
        " WHERE workspace.project_id = project.id AND kind = 'folder')"
        " WHERE default_workspace_id IS NULL"
    )
