import asyncio
import sqlite3
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest

from controllers.portraits import Portraits
from controllers.sessions import Sessions
from controllers.settings import Settings, SettingsUpdate
from errors import AgentError, SessionError, SessionNotFound, SessionProtected
from events import EventBus
from infra.claude.agents import AgentKind, SessionContext
from infra.claude.alfred import Reply
from models import project
from models import session as records
from models import settings as model
from models.db import open_db
from tests.conftest import drain
from tests.test_portraits import FakePaint

DEFAULTS = model.Defaults(
    models={"alfred": "sonnet", "geral": "sonnet", "implementacao": "opus"},
    max_active_sessions=3,
    idle_minutes=10,
)

Script = Reply | Exception | str


class FakeSession:
    """Plays scripted replies; "hang" blocks until cancelled."""

    def __init__(self, kind: AgentKind, context: Callable[[], SessionContext]) -> None:
        self.kind, self.context = kind, context
        self.name = context().name
        self.replies: list[Script] = []
        self.tasks: list[str] = []
        self.contexts: list[SessionContext] = []
        self.connected = False
        self.disconnects = 0

    async def run(self, task: str) -> Reply:
        self.tasks.append(task)
        self.contexts.append(self.context())
        self.connected = True
        reply = self.replies.pop(0) if self.replies else Reply("x", "feito", session_id="sid")
        if reply == "hang":
            await asyncio.Event().wait()
        if isinstance(reply, Exception):
            self.connected = False
            raise reply
        assert isinstance(reply, Reply)
        return reply

    async def disconnect(self) -> None:
        self.disconnects += int(self.connected)
        self.connected = False


class FakeTalker:
    def __init__(self) -> None:
        self.said: list[str] = []

    def notify(self, text: str) -> None:
        self.said.append(text)


class Clock:
    def __init__(self) -> None:
        self.now = 1000.0

    def __call__(self) -> float:
        return self.now


class Env:
    def __init__(self, bus: EventBus, home: Path, max_active: int = 3) -> None:
        self.db: sqlite3.Connection = open_db(":memory:")
        model.seed(self.db, DEFAULTS)
        self.settings = Settings(self.db, bus)
        self.settings.update(SettingsUpdate(max_active_sessions=max_active))
        self.talker, self.clock = FakeTalker(), Clock()
        self.made: dict[str, FakeSession] = {}
        self.portraits = Portraits(self.db, bus, self.settings, home / ".portraits", FakePaint())
        self.sessions = Sessions(
            bus,
            self.talker,
            self.db,
            self.settings,
            self.factory,
            home,
            clock=self.clock,
            portrait=self.portraits.url,
        )
        self.sessions.load()

    def factory(self, kind: AgentKind, context: Callable[[], SessionContext]) -> FakeSession:
        session = FakeSession(kind, context)
        self.made[session.name.lower()] = session
        return session

    def script(self, name: str, *replies: Script) -> FakeSession:
        session = self.made[name.lower()]
        session.replies.extend(replies)
        return session


@pytest.fixture
def home(tmp_path: Path) -> Path:
    return tmp_path


@pytest.fixture
async def env(bus: EventBus, home: Path) -> Env:
    return Env(bus, home)


async def settle() -> None:
    for _ in range(10):
        await asyncio.sleep(0)


def of_type(events: list[dict[str, Any]], type: str) -> list[dict[str, Any]]:
    return [e for e in events if e["type"] == type]


def workspace(env: Env, path: Path, name: str = "back") -> int:
    path.mkdir(exist_ok=True)
    p = project.find_project(env.db, "Recurve") or project.insert_project(env.db, "Recurve", [])
    return project.insert_workspace(env.db, p.id, name, str(path), "folder", branch="main").id


# --- boot and create -------------------------------------------------------------------------


async def test_load_seeds_sistema_disconnected_and_protected(env: Env) -> None:
    [view] = env.sessions.list()

    assert (view.name, view.kind, view.label, view.model, view.cwd) == (
        "sistema",
        "geral",
        "Geral",
        "sonnet",
        "~",
    )
    assert view.protected and view.status == "idle" and not view.connected
    assert (view.project, view.workspace, view.phase, view.subagents) == (None, None, None, [])


async def test_load_restores_saved_sessions(bus: EventBus, home: Path) -> None:
    first = Env(bus, home)
    first.sessions.create("geral", "downloads")

    again = Sessions(bus, FakeTalker(), first.db, first.settings, first.factory, home)
    again.load()

    assert [v.name for v in again.list()] == ["sistema", "downloads"]


async def test_create_implementation_session_in_a_workspace(env: Env, home: Path) -> None:
    queue = env.sessions._bus.subscribe()
    ws = workspace(env, home / "api")

    view = env.sessions.create("implementacao", "back", workspace_id=ws, effort="high")
    await settle()

    assert (view.kind, view.label, view.project, view.workspace, view.branch) == (
        "implementacao",
        "Implementação",
        "Recurve",
        "back",
        "main",
    )
    assert (view.cwd, view.model, view.effort) == ("~/api", "opus", "high")
    assert records.get_session(env.db, "back") is not None
    [created] = of_type(drain(queue), "session_created")
    assert created["session"] == view.model_dump()


@pytest.mark.parametrize(
    ("kind", "name", "with_workspace", "match"),
    [
        ("chef", "x", False, "tipo"),
        ("geral", " ", False, "nome"),
        ("geral", "SISTEMA", False, "Já existe"),
        ("implementacao", "back", False, "ambiente"),
    ],
)
async def test_create_rejects_bad_requests(
    env: Env, kind: str, name: str, with_workspace: bool, match: str
) -> None:
    with pytest.raises(SessionError, match=match):
        env.sessions.create(kind, name)


async def test_create_rejects_an_unknown_workspace(env: Env) -> None:
    with pytest.raises(SessionError, match="ambiente"):
        env.sessions.create("implementacao", "back", workspace_id=99)


async def test_creating_does_not_count_against_the_limit(bus: EventBus, home: Path) -> None:
    env = Env(bus, home, max_active=1)

    env.sessions.create("geral", "a")
    env.sessions.create("geral", "b")

    assert len(env.sessions.list()) == 3


async def test_update_overrides_model_and_effort(env: Env) -> None:
    env.sessions.create("geral", "downloads")

    view = env.sessions.update("downloads", model="haiku", effort="low")

    assert (view.model, view.effort) == ("haiku", "low")
    assert env.sessions.update("downloads", model="").model == "sonnet"


async def test_aliases_are_cleaned_listed_and_find_the_session(env: Env) -> None:
    env.sessions.create("geral", "Site Sales", aliases=[" saite seils ", "", "vendas"])

    assert env.sessions.list()[1].aliases == ["saite seils", "vendas"]
    assert "Site Sales" in env.sessions.delegate("Saite Seils", "a")

    view = env.sessions.set_aliases("site sales", ["seils"])

    assert view.aliases == ["seils"]
    with pytest.raises(SessionNotFound):
        env.sessions.delegate("vendas", "b")


async def test_an_alias_cannot_be_another_sessions_name_or_alias(env: Env) -> None:
    env.sessions.create("geral", "Developer", aliases=["dev"])

    with pytest.raises(SessionError, match="Developer"):
        env.sessions.create("geral", "Design", aliases=["Dev"])
    with pytest.raises(SessionError, match="sistema"):
        env.sessions.set_aliases("Developer", ["Sistema"])
    with pytest.raises(SessionError, match="Developer"):
        env.sessions.create("geral", "dev")


async def test_update_rejects_a_bad_effort(env: Env) -> None:
    with pytest.raises(SessionError, match="Effort"):
        env.sessions.update("sistema", effort="turbo")


# --- running tasks ---------------------------------------------------------------------------


async def test_delegate_runs_the_task_speaks_and_saves_the_conversation(env: Env) -> None:
    queue = env.sessions._bus.subscribe()
    session = env.script("sistema", Reply("x", "Tela girada.", tokens=500, session_id="abc"))

    message = env.sessions.delegate("Sistema", "gira a tela")
    await settle()

    assert "sistema" in message and "fila" not in message
    assert session.tasks == ["gira a tela"]
    assert env.talker.said == ["sistema terminou: Tela girada."]
    [view] = env.sessions.list()
    assert (view.tasks_done, view.tokens, view.last_summary) == (1, 500, "Tela girada.")
    assert view.connected
    assert records.get_session(env.db, "sistema").claude_session_id == "abc"  # type: ignore[union-attr]
    statuses = [e["session"]["status"] for e in of_type(drain(queue), "session_status")]
    assert statuses[-2:] == ["busy", "idle"]


async def test_the_next_connection_resumes_with_current_settings(env: Env) -> None:
    session = env.script("sistema", Reply("x", "a", session_id="abc"), Reply("x", "b"))
    env.sessions.delegate("sistema", "a")
    await settle()
    env.settings.update(
        SettingsUpdate(agents=[model.AgentSettings(kind="geral", model="haiku", effort="low")])
    )

    env.sessions.delegate("sistema", "b")
    await settle()

    first, second = session.contexts
    assert (first.resume, first.model) == (None, "sonnet")
    assert (second.resume, second.model, second.effort) == ("abc", "haiku", "low")


async def test_delegate_to_unknown_session_raises(env: Env) -> None:
    with pytest.raises(SessionNotFound, match="backend"):
        env.sessions.delegate("backend", "a")


async def test_second_task_is_queued_behind_the_first(env: Env) -> None:
    env.script("sistema", "hang")

    env.sessions.delegate("sistema", "a")
    await settle()

    assert "posição 1" in env.sessions.delegate("sistema", "b")
    assert env.sessions.list()[0].queue == 1


async def test_failure_marks_error_and_is_spoken(env: Env) -> None:
    queue = env.sessions._bus.subscribe()
    env.script("sistema", AgentError("boom"))

    env.sessions.delegate("sistema", "a")
    await settle()

    view = env.sessions.list()[0]
    assert view.status == "error" and not view.connected
    assert view.last_error == "boom"
    assert any(e["where"] == "sistema" for e in of_type(drain(queue), "error"))
    assert "não conseguiu" in env.talker.said[0]


async def test_the_reason_stays_until_the_next_task_or_a_clear(env: Env) -> None:
    env.script("sistema", AgentError("boom"))
    env.sessions.delegate("sistema", "a")
    await settle()
    assert env.sessions.list()[0].last_error == "boom"

    env.sessions.delegate("sistema", "b")
    await settle()
    assert env.sessions.list()[0].last_error is None

    env.script("sistema", AgentError("boom"))
    env.sessions.delegate("sistema", "c")
    await settle()
    await env.sessions.clear("sistema")
    assert env.sessions.list()[0].last_error is None


# --- slots -----------------------------------------------------------------------------------


async def test_a_full_house_evicts_the_oldest_idle_connection(bus: EventBus, home: Path) -> None:
    env = Env(bus, home, max_active=2)
    env.sessions.create("geral", "a")
    env.sessions.create("geral", "b")
    for name in ("sistema", "a"):
        env.sessions.delegate(name, "x")
        await settle()
        env.clock.now += 1

    env.sessions.delegate("b", "x")
    await settle()

    connected = {v.name for v in env.sessions.list() if v.connected}
    assert connected == {"a", "b"}
    assert env.made["sistema"].disconnects == 1


async def test_when_every_slot_works_the_task_waits_its_turn(bus: EventBus, home: Path) -> None:
    env = Env(bus, home, max_active=1)
    env.sessions.create("geral", "a")
    env.script("sistema", "hang")
    env.sessions.delegate("sistema", "long")
    await settle()

    message = env.sessions.delegate("a", "x")
    await settle()

    assert "vagas" in message and "fila" in message
    assert env.made["a"].tasks == []
    waiting = next(v for v in env.sessions.list() if v.name == "a")
    assert waiting.waiting and waiting.task == "x"  # not "idle with nothing to do"

    await env.sessions.clear("sistema")
    await settle()

    assert env.made["a"].tasks == ["x"]
    assert not next(v for v in env.sessions.list() if v.name == "a").waiting


async def test_a_finished_task_frees_its_slot_for_a_waiting_one(bus: EventBus, home: Path) -> None:
    env = Env(bus, home, max_active=1)
    env.sessions.create("geral", "a")
    gate = asyncio.Event()

    async def slow() -> Reply:
        await gate.wait()
        return Reply("x", "ok")

    sistema = env.made["sistema"]
    original = sistema.run

    async def run(task: str) -> Reply:
        await original(task)
        return await slow()

    sistema.run = run  # type: ignore[method-assign]
    env.sessions.delegate("sistema", "first")
    await settle()
    env.sessions.delegate("a", "second")
    await settle()
    assert env.made["a"].tasks == []

    gate.set()
    await settle()

    assert env.made["a"].tasks == ["second"]
    assert not env.made["sistema"].connected


async def test_idle_sessions_disconnect_after_the_configured_minutes(env: Env) -> None:
    env.sessions.delegate("sistema", "x")
    await settle()

    env.clock.now += 9 * 60
    await env.sessions.reap_idle()
    assert env.sessions.list()[0].connected

    env.clock.now += 2 * 60
    await env.sessions.reap_idle()
    assert not env.sessions.list()[0].connected
    assert records.get_session(env.db, "sistema").claude_session_id == "sid"  # type: ignore[union-attr]


# --- clear and delete ------------------------------------------------------------------------


async def test_clear_cancels_the_task_drops_the_queue_and_forgets(env: Env) -> None:
    queue = env.sessions._bus.subscribe()
    session = env.script("sistema", Reply("x", "a", tokens=10, session_id="abc"), "hang")
    env.sessions.delegate("sistema", "a")
    await settle()
    env.sessions.delegate("sistema", "b")
    env.sessions.delegate("sistema", "dropped")
    await settle()

    view = await env.sessions.clear("sistema")
    await settle()

    assert not session.connected
    assert (view.status, view.task, view.queue, view.tasks_done, view.tokens) == (
        "idle",
        None,
        0,
        0,
        0,
    )
    assert records.get_session(env.db, "sistema").claude_session_id is None  # type: ignore[union-attr]
    assert session.tasks == ["a", "b"]
    assert of_type(drain(queue), "session_cleared")
    assert env.talker.said == ["sistema terminou: a"]


async def test_delete_removes_and_protects_sistema(env: Env) -> None:
    queue = env.sessions._bus.subscribe()
    env.sessions.create("geral", "downloads")

    await env.sessions.delete("Downloads")
    await settle()

    assert [v.name for v in env.sessions.list()] == ["sistema"]
    assert records.get_session(env.db, "downloads") is None
    assert of_type(drain(queue), "session_deleted")[0]["name"] == "downloads"
    with pytest.raises(SessionProtected):
        await env.sessions.delete("sistema")
    with pytest.raises(SessionNotFound):
        await env.sessions.delete("downloads")


# --- phase, activity and subagents -----------------------------------------------------------


async def test_tracks_activity_phase_and_subagents_of_the_running_task(env: Env) -> None:
    env.script("sistema", "hang")
    bus = env.sessions._bus
    worker = asyncio.create_task(env.sessions.run())
    env.sessions.delegate("sistema", "a")
    await settle()

    bus.publish(
        "agent_progress",
        session="sistema",
        kind="tool",
        content="Grep",
        label="Lendo arquivos",
        phase="exploring",
    )
    bus.publish("agent_progress", session="sistema", kind="tool", content="TodoWrite", phase=None)
    bus.publish(
        "subagent_started",
        session="sistema",
        id="k1",
        subagent_type="Explore",
        description="Acha o billing",
    )
    bus.publish("subagent_progress", session="sistema", id="k1", last_tool="Grep")
    bus.publish("subagent_started", session="sistema", id="k2", subagent_type=None, description="b")
    bus.publish("subagent_finished", session="sistema", id="k2", status="completed")
    bus.publish("agent_progress", session="alfred", kind="text", content="ignorado")
    await settle()
    worker.cancel()

    view = env.sessions.list()[0]
    assert view.phase == "exploring"
    assert view.activity == "TodoWrite"
    assert [(s.id, s.type, s.last_tool, s.status) for s in view.subagents] == [
        ("k1", "Explore", "Grep", "running"),
        ("k2", "agente", None, "completed"),
    ]


async def test_a_new_task_resets_phase_and_subagents(env: Env) -> None:
    worker = asyncio.create_task(env.sessions.run())
    env.sessions.delegate("sistema", "a")
    await settle()
    bus = env.sessions._bus
    bus.publish("subagent_started", session="sistema", id="k1", subagent_type="x", description="d")
    await settle()

    env.script("sistema", "hang")
    env.sessions.delegate("sistema", "b")
    await settle()
    worker.cancel()

    view = env.sessions.list()[0]
    assert (view.phase, view.subagents) == (None, [])


# --- portraits -------------------------------------------------------------------------------


async def test_a_new_portrait_republishes_the_session_with_its_url(env: Env, bus: EventBus) -> None:
    assert env.sessions.list()[0].portrait is None
    queue = bus.subscribe()
    task = asyncio.create_task(env.sessions.run())
    env.portraits.request("sistema")
    worker = asyncio.create_task(env.portraits.run())
    for _ in range(10):
        await asyncio.sleep(0.01)
    task.cancel()
    worker.cancel()

    [status] = [e for e in of_type(drain(queue), "session_status")]
    assert status["session"]["portrait"].startswith("/api/sessions/sistema/portrait?v=")


# --- results (ADR 0014) ----------------------------------------------------------------------


class FakeResults:
    def __init__(self) -> None:
        self.heads: list[Path] = []
        self.recorded: list[tuple[str, str, Path | None, str | None]] = []

    async def head(self, cwd: Path) -> str | None:
        self.heads.append(cwd)
        return "abc"

    async def record(self, session: str, reply: str, cwd: Path | None, head: str | None) -> None:
        self.recorded.append((session, reply, cwd, head))


async def test_a_finished_task_records_its_result_from_the_start_head(
    bus: EventBus, home: Path
) -> None:
    env = Env(bus, home)
    results = FakeResults()
    env.sessions._results = results
    session = env.script("sistema", Reply("RESUMO: ok\nAPRESENTAR: relatório", "ok"))

    env.sessions.delegate("sistema", "faz")
    await settle()

    assert session.tasks == ["faz"]
    assert results.heads == [home]
    assert results.recorded == [("sistema", "RESUMO: ok\nAPRESENTAR: relatório", home, "abc")]
    assert env.talker.said == ["sistema terminou: ok"]


async def test_a_failed_task_records_nothing(env: Env) -> None:
    results = FakeResults()
    env.sessions._results = results
    env.script("sistema", AgentError("caiu"))

    env.sessions.delegate("sistema", "faz")
    await settle()

    assert results.recorded == []
