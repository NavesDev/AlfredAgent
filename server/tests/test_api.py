import asyncio

from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.app import create_app
from controllers.sessions import Sessions
from events import EventBus


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


def add_sessions(app: FastAPI, client: TestClient) -> Sessions:
    """Builds the sessions on the app's loop, as main does."""
    from tests.test_sessions import HOME, Factory, FakeSession, FakeTalker

    async def build() -> Sessions:
        app.state.bus = bus = EventBus(asyncio.get_running_loop())
        sessions = Sessions(bus, FakeTalker(), Factory(), max_active=3, home=HOME)
        sessions.add(FakeSession("sistema"), protected=True)
        sessions.add(FakeSession("downloads"))
        return sessions

    assert client.portal
    app.state.sessions = sessions = client.portal.call(build)
    return sessions


def test_list_sessions() -> None:
    app = create_app()
    with TestClient(app) as client:
        add_sessions(app, client)
        body = client.get("/api/sessions").json()

    assert [s["name"] for s in body] == ["sistema", "downloads"]
    assert body[0]["protected"] and body[0]["kind"] == "geral"


def test_clear_session() -> None:
    app = create_app()
    with TestClient(app) as client:
        add_sessions(app, client)
        ok = client.post("/api/sessions/downloads/clear")
        missing = client.post("/api/sessions/nada/clear")

    assert ok.status_code == 200 and ok.json()["name"] == "downloads"
    assert missing.status_code == 404


def test_delete_session() -> None:
    app = create_app()
    with TestClient(app) as client:
        sessions = add_sessions(app, client)
        ok = client.delete("/api/sessions/downloads")
        protected = client.delete("/api/sessions/sistema")
        missing = client.delete("/api/sessions/downloads")

    assert ok.status_code == 204
    assert protected.status_code == 409 and "limpa" in protected.json()["detail"]
    assert missing.status_code == 404
    assert [v.name for v in sessions.list()] == ["sistema"]
