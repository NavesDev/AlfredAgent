import asyncio

import pytest

from controllers.settings import Settings, SettingsUpdate
from errors import SettingsError
from events import EventBus
from models import settings as model
from models.db import open_db
from tests.conftest import drain

DEFAULTS = model.Defaults(
    models={"alfred": "sonnet", "geral": "sonnet", "implementacao": "opus"},
    max_active_sessions=3,
    idle_minutes=10,
)


def make(bus: EventBus) -> Settings:
    db = open_db(":memory:")
    model.seed(db, DEFAULTS)
    return Settings(db, bus)


async def test_get_returns_seeded_values(bus: EventBus) -> None:
    view = make(bus).get()

    assert {a.kind: a.model for a in view.agents} == DEFAULTS.models
    assert (view.max_active_sessions, view.idle_minutes, view.mcp_disabled) == (3, 10, [])
    assert "figure_scale" not in view.model_dump()  # went with the map characters
    assert view.known_mcp_servers == []


async def test_update_saves_and_publishes(bus: EventBus) -> None:
    queue, s = bus.subscribe(), make(bus)

    view = s.update(
        SettingsUpdate(
            agents=[model.AgentSettings(kind="implementacao", model="sonnet", effort="max")],
            max_active_sessions=5,
            mcp_disabled=["gmail"],
        )
    )
    await asyncio.sleep(0)

    impl = next(a for a in view.agents if a.kind == "implementacao")
    assert (impl.model, impl.effort) == ("sonnet", "max")
    assert (view.max_active_sessions, view.idle_minutes, view.mcp_disabled) == (5, 10, ["gmail"])
    assert s.get() == view
    [event] = [e for e in drain(queue) if e["type"] == "settings_updated"]
    assert event["settings"] == view.model_dump()


@pytest.mark.parametrize(
    "update",
    [
        SettingsUpdate(agents=[model.AgentSettings(kind="chef", model="opus")]),
        SettingsUpdate(agents=[model.AgentSettings(kind="geral", model=" ")]),
        SettingsUpdate(agents=[model.AgentSettings(kind="geral", model="opus", effort="turbo")]),
        SettingsUpdate(max_active_sessions=0),
        SettingsUpdate(idle_minutes=0),
    ],
)
async def test_update_rejects_bad_values(bus: EventBus, update: SettingsUpdate) -> None:
    s = make(bus)

    with pytest.raises(SettingsError):
        s.update(update)
    assert s.get().max_active_sessions == 3


async def test_resolve_prefers_the_session_then_the_kind(bus: EventBus) -> None:
    s = make(bus)
    s.update(
        SettingsUpdate(agents=[model.AgentSettings(kind="geral", model="haiku", effort="low")])
    )

    assert s.resolve("geral", None, None) == ("haiku", "low")
    assert s.resolve("geral", "opus", None) == ("opus", "low")
    assert s.resolve("geral", "opus", "high") == ("opus", "high")


async def test_remembers_mcp_servers_seen_by_sessions(bus: EventBus) -> None:
    s = make(bus)
    worker = asyncio.create_task(s.run())
    await asyncio.sleep(0)

    bus.publish("mcp_servers_seen", session="back", names=["gmail", "context7"])
    bus.publish("mcp_servers_seen", session="front", names=["context7", "figma"])
    for _ in range(5):
        await asyncio.sleep(0)
    worker.cancel()

    assert s.get().known_mcp_servers == ["context7", "figma", "gmail"]

