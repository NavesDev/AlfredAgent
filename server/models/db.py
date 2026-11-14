"""SQLite connection and schema. Operations are short and local, so they run on the loop."""

import sqlite3
from pathlib import Path

SCHEMA_VERSION = 2

_SCHEMA = """
CREATE TABLE IF NOT EXISTS project (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL UNIQUE COLLATE NOCASE,
    aliases TEXT NOT NULL DEFAULT '[]',
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
    db.execute(f"PRAGMA user_version = {SCHEMA_VERSION}")
    return db


def _migrate(db: sqlite3.Connection) -> None:
    """Columns added after a table first shipped; CREATE TABLE IF NOT EXISTS skips them."""
    columns = {row["name"] for row in db.execute("PRAGMA table_info(session)")}
    if "aliases" not in columns:  # version 2
        db.execute("ALTER TABLE session ADD COLUMN aliases TEXT NOT NULL DEFAULT '[]'")
