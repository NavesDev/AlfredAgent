import asyncio

from fastapi.testclient import TestClient

from api.app import create_app
from events import EventBus


def test_health() -> None:
    assert TestClient(create_app()).get("/health").json() == {"status": "ok"}


def test_ws_streams_published_events() -> None:
    app = create_app()
    with TestClient(app) as client:
        app.state.bus = bus = EventBus(client.portal.call(asyncio.get_running_loop))
        with client.websocket_connect("/ws") as ws:
            bus.publish("voice_state", state="listening")

            event = ws.receive_json()

    assert (event["type"], event["state"]) == ("voice_state", "listening")
