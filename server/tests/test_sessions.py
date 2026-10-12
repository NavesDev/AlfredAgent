import asyncio
from pathlib import Path

import pytest

from controllers.sessions import Sessions
from errors import AgentError, SessionError, SessionNotFound, SessionProtected
from events import EventBus
from infra.claude.agents import KINDS, AgentKind
from infra.claude.alfred import Reply
from tests.conftest import drain

HOME = Path("/home/u")


class FakeSession:
    def __init__(self, name: str, *replies: Reply | Exception | str, cwd: Path = HOME) -> None:
        self.name, self.kind, self.model, self.cwd = name, KINDS["geral"], "sonnet", cwd
        self.replies = list(replies)
        self.tasks: list[str] = []
        self.cleared = 0

    async def run(self, task: str) -> Reply:
        self.tasks.append(task)
        reply = self.replies.pop(0)
        if reply == "hang":
            await asyncio.Event().wait()
        if isinstance(reply, Exception):
            raise reply
        assert isinstance(reply, Reply)
        return reply

    async def clear(self) -> None:
        self.cleared += 1


class FakeTalker:
    def __init__(self) -> None:
        self.said: list[str] = []

    def say(self, text: str) -> None:
        self.said.append(text)


class Factory:
    def __init__(self) -> None:
        self.made: list[FakeSession] = []

    def __call__(self, kind: AgentKind, name: str, cwd: Path) -> FakeSession:
        self.made.append(FakeSession(name, cwd=cwd))
        return self.made[-1]


def sessions(bus: EventBus, talker: FakeTalker | None = None, max_active: int = 3) -> Sessions:
    return Sessions(bus, talker or FakeTalker(), Factory(), max_active=max_active, home=HOME)


async def settle() -> None:
    for _ in range(5):
        await asyncio.sleep(0)


def of_type(events: list[dict[str, object]], type: str) -> list[dict[str, object]]:
    return [e for e in events if e["type"] == type]


async def test_add_registers_and_announces_the_session(bus: EventBus) -> None:
    queue, s = bus.subscribe(), sessions(bus)

    s.add(FakeSession("sistema"), protected=True)
    await settle()

    [view] = s.list()
    assert (view.name, view.kind, view.label, view.model, view.cwd) == (
        "sistema",
        "geral",
        "Geral",
        "sonnet",
        "~",
    )
    assert view.status == "idle" and view.protected
    [created] = of_type(drain(queue), "session_created")
    assert created["session"] == view.model_dump()


async def test_create_builds_a_session_of_the_kind_in_the_folder(
    bus: EventBus, tmp_path: Path
) -> None:
    s = Sessions(bus, FakeTalker(), Factory(), max_active=3, home=tmp_path)

    view = s.create("geral", "downloads", str(tmp_path))

    assert (view.name, view.kind, view.cwd, view.protected) == ("downloads", "geral", "~", False)


@pytest.mark.parametrize(
    ("kind", "name", "cwd", "match"),
    [
        ("chef", "x", None, "tipo"),
        ("geral", " ", None, "nome"),
        ("geral", "SISTEMA", None, "Já existe"),
        ("geral", "x", "/nao/existe", "pasta"),
    ],
)
async def test_create_rejects_bad_requests(
    bus: EventBus, kind: str, name: str, cwd: str | None, match: str
) -> None:
    s = Sessions(bus, FakeTalker(), Factory(), max_active=3, home=Path("/"))
    s.add(FakeSession("sistema"))

    with pytest.raises(SessionError, match=match):
        s.create(kind, name, cwd)


async def test_create_respects_the_session_limit(bus: EventBus) -> None:
    s = Sessions(bus, FakeTalker(), Factory(), max_active=1, home=Path("/"))
    s.add(FakeSession("sistema"))

    with pytest.raises(SessionError, match="limite"):
        s.create("geral", "outra")


async def test_delegate_runs_the_task_and_speaks_the_summary(bus: EventBus) -> None:
    queue, talker = bus.subscribe(), FakeTalker()
    s = sessions(bus, talker)
    session = FakeSession("sistema", Reply("x", "Tela girada.", tokens=500))
    s.add(session)

    message = s.delegate("Sistema", "gira a tela")
    await settle()

    assert "sistema" in message and "fila" not in message
    assert session.tasks == ["gira a tela"]
    assert talker.said == ["Tela girada."]
    [view] = s.list()
    assert (view.tasks_done, view.tokens, view.last_summary) == (1, 500, "Tela girada.")
    statuses = [e["session"]["status"] for e in of_type(drain(queue), "session_status")]  # type: ignore[index]
    assert statuses[-2:] == ["busy", "idle"]


async def test_delegate_to_unknown_session_raises(bus: EventBus) -> None:
    with pytest.raises(SessionNotFound, match="backend"):
        sessions(bus).delegate("backend", "a")


async def test_second_task_is_queued_behind_the_first(bus: EventBus) -> None:
    s = sessions(bus)
    s.add(FakeSession("sistema", "hang"))

    s.delegate("sistema", "a")
    await settle()

    assert "posição 1" in s.delegate("sistema", "b")
    assert s.list()[0].queue == 1


async def test_failure_marks_error_and_is_spoken(bus: EventBus) -> None:
    queue, talker = bus.subscribe(), FakeTalker()
    s = sessions(bus, talker)
    s.add(FakeSession("sistema", AgentError("boom")))

    s.delegate("sistema", "a")
    await settle()

    assert s.list()[0].status == "error"
    assert any(e["where"] == "sistema" for e in of_type(drain(queue), "error"))
    assert "não conseguiu" in talker.said[0]


async def test_clear_cancels_the_task_drops_the_queue_and_resets(bus: EventBus) -> None:
    queue, talker = bus.subscribe(), FakeTalker()
    s = sessions(bus, talker)
    session = FakeSession("sistema", Reply("x", "a", tokens=10), "hang", Reply("x", "c"))
    s.add(session)
    s.delegate("sistema", "a")
    await settle()
    s.delegate("sistema", "b")
    s.delegate("sistema", "dropped")
    await settle()

    view = await s.clear("sistema")
    await settle()

    assert session.cleared == 1
    assert (view.status, view.task, view.queue, view.tasks_done, view.tokens) == (
        "idle",
        None,
        0,
        0,
        0,
    )
    assert of_type(drain(queue), "session_cleared")
    s.delegate("sistema", "c")
    await settle()
    assert session.tasks == ["a", "b", "c"]
    assert talker.said == ["a", "c"]


async def test_delete_removes_the_session(bus: EventBus) -> None:
    queue, s = bus.subscribe(), sessions(bus)
    session = FakeSession("downloads")
    s.add(session)

    await s.delete("downloads")
    await settle()

    assert s.list() == [] and session.cleared == 1
    [deleted] = of_type(drain(queue), "session_deleted")
    assert deleted["name"] == "downloads"
    with pytest.raises(SessionNotFound):
        s.delegate("downloads", "a")


async def test_protected_session_cannot_be_deleted(bus: EventBus) -> None:
    s = sessions(bus)
    s.add(FakeSession("sistema"), protected=True)

    with pytest.raises(SessionProtected, match="limpa"):
        await s.delete("sistema")
    assert len(s.list()) == 1


async def test_run_keeps_the_last_activity_of_a_busy_session(bus: EventBus) -> None:
    s = sessions(bus)
    s.add(FakeSession("sistema", "hang"))
    watcher = asyncio.create_task(s.run())
    await settle()
    s.delegate("sistema", "a")
    await settle()

    bus.publish("agent_progress", session="sistema", kind="tool", content="Bash", label="Rodando")
    bus.publish("agent_progress", session="alfred", kind="text", content="ignorado")
    await settle()
    watcher.cancel()

    assert s.list()[0].activity == "Rodando"
