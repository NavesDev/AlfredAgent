import asyncio

from controllers.sessions import Sessions
from errors import AgentError
from events import EventBus
from infra.claude.alfred import Reply
from tests.conftest import drain


class FakeSession:
    name = "sistema"

    def __init__(self, *replies: Reply | Exception) -> None:
        self.replies = list(replies)
        self.tasks: list[str] = []

    async def run(self, task: str) -> Reply:
        self.tasks.append(task)
        reply = self.replies.pop(0)
        if isinstance(reply, Exception):
            raise reply
        return reply


class FakeTalker:
    def __init__(self) -> None:
        self.said: list[str] = []

    def say(self, text: str) -> None:
        self.said.append(text)


async def test_delegate_returns_at_once_and_worker_speaks_the_summary(bus: EventBus) -> None:
    queue, session, talker = bus.subscribe(), FakeSession(Reply("x", "Tela girada.")), FakeTalker()
    sessions = Sessions(bus, talker, session)

    message = sessions.delegate("gira a tela")
    assert "sistema" in message and "fila" not in message

    worker = asyncio.create_task(sessions.run())
    await asyncio.sleep(0.01)
    worker.cancel()

    assert session.tasks == ["gira a tela"]
    assert talker.said == ["Tela girada."]
    statuses = [e["status"] for e in drain(queue) if e["type"] == "session_status"]
    assert statuses == ["busy", "idle"]


async def test_second_task_is_queued_behind_the_first(bus: EventBus) -> None:
    sessions = Sessions(bus, FakeTalker(), FakeSession())

    sessions.delegate("a")
    assert "posição 1" in sessions.delegate("b")


async def test_failure_is_published_and_spoken(bus: EventBus) -> None:
    queue, talker = bus.subscribe(), FakeTalker()
    sessions = Sessions(bus, talker, FakeSession(AgentError("boom")))

    await sessions.process_one("a")
    await asyncio.sleep(0)

    assert any(e["type"] == "error" and e["where"] == "sistema" for e in drain(queue))
    assert "não conseguiu" in talker.said[0]
