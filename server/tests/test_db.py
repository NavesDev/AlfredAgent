import sqlite3
from pathlib import Path

import pytest

from models import project, session, settings
from models.db import SCHEMA_VERSION, open_db


@pytest.fixture
def db() -> sqlite3.Connection:
    return open_db(":memory:")


def test_open_creates_the_schema_and_version(tmp_path: Path) -> None:
    db = open_db(tmp_path / "data" / "alfred.sqlite3")

    tables = {r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    assert {"project", "workspace", "session", "agent_settings", "app_settings"} <= tables
    assert db.execute("PRAGMA user_version").fetchone()[0] == SCHEMA_VERSION
    assert db.execute("PRAGMA foreign_keys").fetchone()[0] == 1


def test_reopening_keeps_the_data(tmp_path: Path) -> None:
    path = tmp_path / "alfred.sqlite3"
    project.insert_project(open_db(path), "Recurve", ["billing"])

    assert [p.name for p in project.list_projects(open_db(path))] == ["Recurve"]


def test_projects_with_workspaces(db: sqlite3.Connection) -> None:
    p = project.insert_project(db, "Recurve", ["recurve", "billing"])
    back = project.insert_workspace(db, p.id, "back", "/dev/api", "folder")
    wt = project.insert_workspace(
        db, p.id, "cancel", "/dev/api-wt/cancel", "worktree", back.id, "cancel"
    )

    [loaded] = project.list_projects(db)
    assert loaded.aliases == ["recurve", "billing"]
    assert [w.name for w in loaded.workspaces] == ["back", "cancel"]
    assert (wt.kind, wt.parent_id, wt.branch) == ("worktree", back.id, "cancel")
    assert project.get_workspace(db, wt.id) == wt


def test_find_project_by_name_or_alias_ignoring_case(db: sqlite3.Connection) -> None:
    p = project.insert_project(db, "Recurve", ["billing"])

    assert project.find_project(db, "RECURVE") == p
    assert project.find_project(db, "Billing") == p
    assert project.find_project(db, "outro") is None


def test_update_and_delete_project(db: sqlite3.Connection) -> None:
    p = project.insert_project(db, "Recurve", [])

    project.update_project(db, p.id, name="Recurve 2", aliases=["r2"])
    assert project.get_project(db, p.id).name == "Recurve 2"  # type: ignore[union-attr]

    project.delete_project(db, p.id)
    assert project.get_project(db, p.id) is None


def test_session_records(db: sqlite3.Connection) -> None:
    p = project.insert_project(db, "Recurve", [])
    ws = project.insert_workspace(db, p.id, "back", "/dev/api", "folder")

    session.insert_session(db, "sistema", "geral", protected=True)
    session.insert_session(db, "back", "implementacao", workspace_id=ws.id, model="opus")
    session.update_session(db, "back", claude_session_id="abc", effort="high")

    records = {r.name: r for r in session.list_sessions(db)}
    assert records["sistema"].protected and records["sistema"].workspace_id is None
    assert (records["back"].model, records["back"].effort) == ("opus", "high")
    assert records["back"].claude_session_id == "abc"
    assert session.sessions_in_workspace(db, ws.id) == ["back"]

    session.delete_session(db, "back")
    assert [r.name for r in session.list_sessions(db)] == ["sistema"]


def test_session_aliases(db: sqlite3.Connection) -> None:
    session.insert_session(db, "Site Sales", "geral", aliases=["saite seils"])
    assert session.get_session(db, "site sales").aliases == ["saite seils"]  # type: ignore[union-attr]

    session.update_session(db, "Site Sales", aliases=["vendas"])

    assert session.get_session(db, "Site Sales").aliases == ["vendas"]  # type: ignore[union-attr]
    assert session.get_session(db, "sistema") is None


def test_opening_an_old_database_adds_session_aliases(tmp_path: Path) -> None:
    path = tmp_path / "old.sqlite3"
    old = sqlite3.connect(path)
    old.execute(
        "CREATE TABLE session (id INTEGER PRIMARY KEY, name TEXT NOT NULL UNIQUE,"
        " kind TEXT NOT NULL, workspace_id INTEGER, model TEXT, effort TEXT,"
        " claude_session_id TEXT, protected INTEGER NOT NULL DEFAULT 0,"
        " created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP)"
    )
    old.execute("INSERT INTO session (name, kind) VALUES ('sistema', 'geral')")
    old.commit()
    old.close()

    [record] = session.list_sessions(open_db(path))

    assert record.aliases == []


def test_seed_writes_defaults_only_once(db: sqlite3.Connection) -> None:
    defaults = settings.Defaults(
        models={"alfred": "sonnet", "geral": "sonnet", "implementacao": "opus"},
        max_active_sessions=3,
        idle_minutes=10,
    )
    settings.seed(db, defaults)
    settings.save_agent(db, settings.AgentSettings(kind="geral", model="haiku", effort="low"))
    settings.save_app(db, settings.AppSettings(max_active_sessions=5, idle_minutes=2))

    settings.seed(db, defaults)

    agents = settings.load_agents(db)
    assert agents["implementacao"].model == "opus" and agents["implementacao"].effort is None
    assert (agents["geral"].model, agents["geral"].effort) == ("haiku", "low")
    assert settings.load_app(db) == settings.AppSettings(
        max_active_sessions=5, idle_minutes=2, mcp_disabled=[]
    )


def test_descriptions_persist_and_old_databases_gain_the_columns(tmp_path: Path) -> None:
    path = tmp_path / "old.sqlite3"
    old = sqlite3.connect(path)
    old.executescript(
        "CREATE TABLE project (id INTEGER PRIMARY KEY, name TEXT NOT NULL UNIQUE,"
        " aliases TEXT NOT NULL DEFAULT '[]');"
        "CREATE TABLE workspace (id INTEGER PRIMARY KEY, project_id INTEGER NOT NULL,"
        " name TEXT NOT NULL, path TEXT NOT NULL, kind TEXT NOT NULL, parent_id INTEGER,"
        " branch TEXT);"
        "INSERT INTO project (name) VALUES ('Recurve');"
    )
    old.close()
    db = open_db(path)

    [legacy] = project.list_projects(db)
    p = project.insert_project(db, "Vrummy", [], "App de aluguel de carros")
    ws = project.insert_workspace(db, p.id, "back", "/dev/api", "folder", description="API")
    project.update_project(db, legacy.id, description="Cobrança recorrente")
    project.update_workspace(db, ws.id, description="API em Spring")

    assert legacy.description == ""
    assert project.get_project(db, legacy.id).description == "Cobrança recorrente"  # type: ignore[union-attr]
    assert project.get_workspace(db, ws.id).description == "API em Spring"  # type: ignore[union-attr]
    assert project.get_project(db, p.id).description == "App de aluguel de carros"  # type: ignore[union-attr]
