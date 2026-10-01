import asyncio
from collections.abc import Callable

from controllers.router import FAILURE_MESSAGE, Router
from errors import AgentError
from events import EventBus
from infra.claude.alfred import Reply
from tests.conftest import drain


class FakeAgent:
    def __init__(self, reply: Reply | Exception) -> None:
        self.reply = reply
        self.asked: list[str] = []

    async def ask(self, text: str, on_summary: Callable[[str], None]) -> Reply:
        self.asked.append(text)
        if isinstance(self.reply, Exception):
            raise self.reply
        if self.reply.summary:
            on_summary(self.reply.summary)
        return self.reply


class FakeTalker:
    def __init__(self) -> None:
        self.said: list[str] = []

    def say(self, text: str) -> None:
        self.said.append(text)


async def test_routes_text_to_alfred_and_speaks_summary(bus: EventBus) -> None:
    agent, talker = FakeAgent(Reply("longo", "curto")), FakeTalker()

    await Router(bus, agent, talker).handle("oi")

    assert agent.asked == ["oi"]
    assert talker.said == ["curto"]


async def test_publishes_thinking_while_agent_works(bus: EventBus) -> None:
    queue = bus.subscribe()

    await Router(bus, FakeAgent(Reply("x", "y")), FakeTalker()).handle("oi")
    await asyncio.sleep(0)

    first = drain(queue)[0]
    assert (first["type"], first["state"]) == ("voice_state", "thinking")


async def test_agent_error_is_published_and_spoken(bus: EventBus) -> None:
    queue, talker = bus.subscribe(), FakeTalker()

    await Router(bus, FakeAgent(AgentError("boom")), talker).handle("oi")
    await asyncio.sleep(0)

    errors = [e for e in drain(queue) if e["type"] == "error"]
    assert errors[0]["where"] == "alfred" and errors[0]["message"] == "boom"
    assert talker.said == [FAILURE_MESSAGE]


async def test_empty_summary_goes_back_to_idle_silently(bus: EventBus) -> None:
    queue, talker = bus.subscribe(), FakeTalker()

    await Router(bus, FakeAgent(Reply("", "")), talker).handle("oi")
    await asyncio.sleep(0)

    assert talker.said == []
    assert drain(queue)[-1]["state"] == "idle"
