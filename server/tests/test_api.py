import asyncio
from pathlib import Path
from typing import Any

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.app import create_app
from controllers.projects import Projects
from events import EventBus
from tests.test_projects import FakeGit
from tests.test_sessions import Env


def test_health() -> None:
    assert TestClient(create_app()).get("/health").json() == {"status": "ok"}


def test_ws_streams_published_events() -> None:
    app = create_app()
    with TestClient(app) as client:
        assert client.portal
        app.state.bus = bus = EventBus(client.portal.call(asyncio.get_running_loop))
        with client.websocket_connect("/ws") as ws:
            bus.publish("voice_state", state="listening")

            event = ws.receive_json()

    assert (event["type"], event["state"]) == ("voice_state", "listening")


def test_clear_alfred() -> None:
    class FakeAlfred:
        cleared = 0

        async def reset(self) -> None:
            self.cleared += 1

    app = create_app()
    app.state.alfred = alfred = FakeAlfred()

    assert TestClient(app).post("/api/alfred/clear").status_code == 204
    assert alfred.cleared == 1


class Api:
    def __init__(self, app: FastAPI, client: TestClient, home: Path) -> None:
        self.client, self.home = client, home

        async def build() -> Env:
            bus = EventBus(asyncio.get_running_loop())
            return Env(bus, home)

        assert client.portal
        self.env = env = client.portal.call(build)
        app.state.bus = env.sessions._bus
        app.state.sessions = env.sessions
        app.state.settings = env.settings
        app.state.projects = Projects(env.db, env.sessions._bus, FakeGit())

    def __getattr__(self, method: str) -> Any:
        return getattr(self.client, method)


@pytest.fixture
def api(tmp_path: Path) -> Any:
    app = create_app()
    with TestClient(app) as client:
        yield Api(app, client, tmp_path)


def test_sessions_list_create_update(api: Api) -> None:
    created = api.post("/api/sessions", json={"kind": "geral", "name": "downloads"})
    duplicate = api.post("/api/sessions", json={"kind": "geral", "name": "downloads"})
    updated = api.patch("/api/sessions/downloads", json={"model": "haiku", "effort": "low"})
    bad = api.patch("/api/sessions/downloads", json={"effort": "turbo"})
    missing = api.patch("/api/sessions/nada", json={"model": "x"})
    body = api.get("/api/sessions").json()

    assert created.status_code == 201 and created.json()["name"] == "downloads"
    assert duplicate.status_code == 422 and "Já existe" in duplicate.json()["detail"]
    assert (updated.json()["model"], updated.json()["effort"]) == ("haiku", "low")
    assert bad.status_code == 422 and missing.status_code == 404
    assert [s["name"] for s in body] == ["sistema", "downloads"]
    assert body[0]["protected"] and body[0]["kind"] == "geral"


def test_session_aliases(api: Api) -> None:
    created = api.post(
        "/api/sessions", json={"kind": "geral", "name": "Site Sales", "aliases": ["seils"]}
    )
    updated = api.patch("/api/sessions/seils", json={"aliases": ["saite seils"]})
    taken = api.post("/api/sessions", json={"kind": "geral", "name": "x", "aliases": ["sistema"]})

    assert created.json()["aliases"] == ["seils"]
    assert updated.json()["aliases"] == ["saite seils"]
    assert taken.status_code == 422


def test_clear_and_delete_session(api: Api) -> None:
    api.post("/api/sessions", json={"kind": "geral", "name": "downloads"})

    assert api.post("/api/sessions/downloads/clear").json()["name"] == "downloads"
    assert api.post("/api/sessions/nada/clear").status_code == 404
    assert api.delete("/api/sessions/downloads").status_code == 204
    protected = api.delete("/api/sessions/sistema")
    assert protected.status_code == 409 and "limpa" in protected.json()["detail"]
    assert api.delete("/api/sessions/downloads").status_code == 404


def test_projects_and_workspaces(api: Api) -> None:
    (api.home / "api").mkdir()

    created = api.post("/api/projects", json={"name": "Recurve", "aliases": ["billing"]}).json()
    pid = created["id"]
    ws = api.post(
        f"/api/projects/{pid}/workspaces", json={"name": "back", "path": str(api.home / "api")}
    )
    missing_folder = api.post(
        f"/api/projects/{pid}/workspaces", json={"name": "x", "path": "/nada"}
    )
    wt = api.post(
        f"/api/projects/{pid}/worktrees", json={"parent_id": ws.json()["id"], "name": "cancel"}
    )
    renamed = api.patch(f"/api/projects/{pid}", json={"name": "Recurve 2"})
    listed = api.get("/api/projects").json()

    assert ws.status_code == 201 and missing_folder.status_code == 422
    assert wt.status_code == 201 and wt.json()["kind"] == "worktree"
    assert renamed.json()["name"] == "Recurve 2"
    assert [w["name"] for w in listed[0]["workspaces"]] == ["back", "cancel"]
    assert api.get(f"/api/projects/{pid}").json()["name"] == "Recurve 2"
    assert api.get("/api/projects/99").status_code == 404


def test_session_in_a_workspace_and_deleting_in_use(api: Api) -> None:
    (api.home / "api").mkdir()
    pid = api.post("/api/projects", json={"name": "Recurve"}).json()["id"]
    wid = api.post(
        f"/api/projects/{pid}/workspaces", json={"name": "back", "path": str(api.home / "api")}
    ).json()["id"]

    session = api.post(
        "/api/sessions", json={"kind": "implementacao", "name": "back", "workspace_id": wid}
    ).json()
    in_use = api.delete(f"/api/workspaces/{wid}")
    project_in_use = api.delete(f"/api/projects/{pid}")
    api.delete("/api/sessions/back")

    assert (session["project"], session["workspace"]) == ("Recurve", "back")
    assert in_use.status_code == 409 and project_in_use.status_code == 409
    assert api.delete(f"/api/workspaces/{wid}").status_code == 204
    assert api.delete(f"/api/projects/{pid}").status_code == 204


def test_settings(api: Api) -> None:
    current = api.get("/api/settings").json()
    saved = api.put(
        "/api/settings",
        json={
            "agents": [{"kind": "implementacao", "model": "opus", "effort": "max"}],
            "max_active_sessions": 4,
            "mcp_disabled": ["gmail"],
        },
    ).json()
    bad = api.put("/api/settings", json={"idle_minutes": 0})

    assert {a["kind"] for a in current["agents"]} == {"alfred", "geral", "implementacao"}
    assert saved["max_active_sessions"] == 4 and saved["mcp_disabled"] == ["gmail"]
    assert bad.status_code == 422
