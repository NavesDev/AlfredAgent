import asyncio
from pathlib import Path
from typing import Any

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.app import create_app
from controllers.projects import Projects
from events import EventBus
from tests.test_portrait import PNG
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
        app.state.portraits = env.portraits
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


def test_session_portrait(api: Api) -> None:
    missing = api.get("/api/sessions/sistema/portrait")
    asked = api.post("/api/sessions/sistema/portrait")
    unknown = api.post("/api/sessions/ninguem/portrait")
    folder = api.home / ".portraits"
    folder.mkdir()
    (folder / "1.png").write_bytes(PNG)
    found = api.get("/api/sessions/sistema/portrait")

    assert (missing.status_code, asked.status_code, unknown.status_code) == (404, 202, 404)
    assert (found.status_code, found.content) == (200, PNG)
    assert found.headers["content-type"] == "image/png"
    assert api.get("/api/sessions").json()[0]["portrait"].startswith("/api/sessions/sistema/")


def test_project_and_workspace_descriptions(api: Api) -> None:
    (api.home / "api").mkdir()
    pid = api.post("/api/projects", json={"name": "Recurve", "description": "Cobrança"}).json()[
        "id"
    ]
    wid = api.post(
        f"/api/projects/{pid}/workspaces",
        json={"name": "back", "path": str(api.home / "api"), "description": "API"},
    ).json()["id"]

    changed = api.patch(f"/api/workspaces/{wid}", json={"description": "API em Spring"})
    too_long = api.patch(f"/api/projects/{pid}", json={"description": "x" * 201})
    missing = api.patch("/api/workspaces/99", json={"description": "nada"})
    [listed] = api.get("/api/projects").json()

    assert changed.status_code == 200 and changed.json()["description"] == "API em Spring"
    assert too_long.status_code == 422 and missing.status_code == 404
    assert listed["description"] == "Cobrança"
    assert listed["workspaces"][0]["description"] == "API em Spring"


def test_default_workspace_and_implementation_modes(api: Api) -> None:
    for name in ("api", "web"):
        (api.home / name).mkdir()
    pid = api.post("/api/projects", json={"name": "Recurve"}).json()["id"]
    first, second = (
        api.post(
            f"/api/projects/{pid}/workspaces", json={"name": n, "path": str(api.home / n)}
        ).json()["id"]
        for n in ("api", "web")
    )

    assert api.get(f"/api/projects/{pid}").json()["default_workspace_id"] == first
    moved = api.patch(f"/api/projects/{pid}", json={"default_workspace_id": second})
    own = api.patch(f"/api/workspaces/{second}", json={"implementation_mode": "ambiente"})
    back = api.patch(f"/api/workspaces/{second}", json={"implementation_mode": None})
    kept = api.patch(f"/api/workspaces/{second}", json={"description": "Front"})
    bad = api.patch(f"/api/workspaces/{second}", json={"implementation_mode": "nada"})
    alien = api.patch(f"/api/projects/{pid}", json={"default_workspace_id": 99})
    settings = api.put("/api/settings", json={"implementation_mode": "ambiente"}).json()

    assert moved.json()["default_workspace_id"] == second
    assert own.json()["implementation_mode"] == "ambiente"
    assert back.json()["implementation_mode"] is None
    assert kept.json()["implementation_mode"] is None and kept.json()["description"] == "Front"
    assert bad.status_code == 422 and alien.status_code == 404
    assert settings["implementation_mode"] == "ambiente"


def test_session_description(api: Api) -> None:
    changed = api.patch("/api/sessions/sistema", json={"description": "Tarefas no computador"})
    too_long = api.patch("/api/sessions/sistema", json={"description": "x" * 201})

    assert changed.status_code == 200
    assert changed.json()["description"] == "Tarefas no computador"
    assert too_long.status_code == 422


def test_update_routes(tmp_path: Path) -> None:
    from controllers.updates import Updates
    from tests.test_updates import FakeGit

    app = create_app()
    spawned: list[str] = []
    fake = FakeGit()
    with TestClient(app) as client:
        assert client.portal
        bus = EventBus(client.portal.call(asyncio.get_running_loop))
        app.state.updates = Updates(
            bus, tmp_path, git=fake, spawn=spawned.append, result_path=tmp_path / "u.json"
        )

        assert client.get("/api/update").json()["available"] is False
        assert client.post("/api/update/check").json()["latest"] == "v0.2.0"
        fake.dirty = True
        refused = client.post("/api/update/apply")
        fake.dirty = False
        applied = client.post("/api/update/apply")

    assert refused.status_code == 409 and "não commitadas" in refused.json()["detail"]
    assert applied.status_code == 202 and applied.json()["status"] == "updating"
    assert spawned == ["v0.2.0"]


# --- results (ADR 0014) ----------------------------------------------------------------------


def _results_client(tmp_path: Path, host: str) -> Any:
    from controllers.results import Results

    app = create_app()
    with TestClient(app, client=(host, 5000)) as client:
        api: Any = Api(app, client, tmp_path)
        api.results = app.state.results = Results(api.env.db, api.env.sessions._bus, tmp_path)
        yield api


@pytest.fixture
def results_api(tmp_path: Path) -> Any:
    """A client on this computer (loopback)."""
    yield from _results_client(tmp_path, "127.0.0.1")


@pytest.fixture
def phone_api(tmp_path: Path) -> Any:
    """A phone on the local network."""
    yield from _results_client(tmp_path, "192.168.0.20")


def _record(api: Any, reply: str) -> int:
    view = api.client.portal.call(api.results.record, "sistema", reply, None, None)
    return int(view.id)


def test_results_list_get_and_serve_a_file(results_api: Any) -> None:
    api = results_api
    (api.home / "a.png").write_bytes(b"PNG!")
    rid = _record(api, f"RESUMO: pronto\nAPRESENTAR: {api.home / 'a.png'}")

    listed = api.get("/api/results", params={"session": "sistema"})
    one = api.get(f"/api/results/{rid}")
    served = api.get(f"/api/results/{rid}/files/0")

    assert [r["id"] for r in listed.json()] == [rid]
    assert one.json()["files"] == [{"name": "a.png", "kind": "image", "size": 4, "exists": True}]
    assert served.status_code == 200 and served.content == b"PNG!"
    assert api.get("/api/results", params={"session": "nada"}).status_code == 404
    assert api.get("/api/results", params={"session": "sistema", "limit": 31}).status_code == 422
    assert api.get("/api/results/999").status_code == 404
    assert api.get(f"/api/results/{rid}/files/1").status_code == 404


def test_a_file_is_only_served_to_this_computer(phone_api: Any) -> None:
    api = phone_api
    (api.home / "a.png").write_bytes(b"PNG!")
    rid = _record(api, f"APRESENTAR: {api.home / 'a.png'}")

    assert api.get(f"/api/results/{rid}/files/0").status_code == 403
    assert api.get(f"/api/results/{rid}").status_code == 200  # text still reaches it


@pytest.mark.parametrize(
    ("host", "local"),
    [("127.0.0.1", True), ("::1", True), ("::ffff:127.0.0.1", True), ("192.168.0.20", False),
     ("testclient", False), ("", False)],
)  # fmt: skip
def test_loopback_is_fail_closed(host: str, local: bool) -> None:
    from types import SimpleNamespace

    from api.routes.results import _loopback

    request = SimpleNamespace(client=SimpleNamespace(host=host) if host else None)
    assert _loopback(request) is local  # type: ignore[arg-type]


def test_a_deleted_file_is_gone_and_a_secret_forbidden(results_api: Any) -> None:
    api = results_api
    png = api.home / "a.png"
    png.write_bytes(b"PNG!")
    rid = _record(api, f"APRESENTAR: {png}")

    png.unlink()
    assert api.get(f"/api/results/{rid}/files/0").status_code == 410
    (api.home / ".ssh").mkdir()
    (api.home / ".ssh/id_rsa").write_text("k")
    png.symlink_to(api.home / ".ssh/id_rsa")
    assert api.get(f"/api/results/{rid}/files/0").status_code == 403


def test_present_and_close(results_api: Any) -> None:
    api = results_api
    rid = _record(api, "GUARDAR: relatório")

    assert api.post(f"/api/results/{rid}/present", json={"mode": "ampliado"}).status_code == 204
    assert api.post(f"/api/results/{rid}/present", json={"mode": "grande"}).status_code == 422
    assert api.post("/api/results/999/present", json={"mode": "card"}).status_code == 404
    assert api.post("/api/presentation/close").status_code == 204


def test_settings_overlay_position(api: Api) -> None:
    ok = api.put("/api/settings", json={"overlay_position": "bottom_center"})
    bad = api.put("/api/settings", json={"overlay_position": "meio"})

    assert ok.json()["overlay_position"] == "bottom_center"
    assert bad.status_code == 422
    assert api.get("/api/settings").json()["overlay_position"] == "bottom_center"


def test_open_a_file_on_this_computer_only(results_api: Any, tmp_path: Path) -> None:
    api = results_api
    opened: list[tuple[Path, bool]] = []

    async def fake_open(path: Path, reveal: bool) -> None:
        opened.append((path, reveal))

    api.results._open = fake_open
    (api.home / "a.png").write_bytes(b"PNG!")
    rid = _record(api, f"APRESENTAR: {api.home / 'a.png'}")

    assert api.post(f"/api/results/{rid}/files/0/open", json={"reveal": True}).status_code == 204
    assert api.post(f"/api/results/{rid}/files/3/open", json={}).status_code == 404
    assert opened == [(api.home / "a.png", True)]


def test_open_is_refused_to_a_phone(phone_api: Any) -> None:
    api = phone_api
    (api.home / "a.png").write_bytes(b"PNG!")
    rid = _record(api, f"APRESENTAR: {api.home / 'a.png'}")
    assert api.post(f"/api/results/{rid}/files/0/open", json={}).status_code == 403
