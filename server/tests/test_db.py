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
