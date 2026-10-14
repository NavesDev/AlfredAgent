import asyncio
from pathlib import Path

import pytest
from claude_agent_sdk import (
    AssistantMessage,
    ProcessError,
    SystemMessage,
    TaskNotificationMessage,
    TaskProgressMessage,
    TaskStartedMessage,
    ToolUseBlock,
    UserMessage,
)

from errors import AgentError
from events import EventBus
from infra.claude.agents import KINDS, SessionContext
from infra.claude.session import CodingSession
from tests.conftest import drain
from tests.test_alfred import FakeConnect, result


def session(
    bus: EventBus,
    connect: FakeConnect,
    cwd: Path = Path("/"),
    resume: str | None = None,
    kind: str = "geral",
) -> CodingSession:
    def context() -> SessionContext:
        return SessionContext(name="sistema", cwd=cwd, model="sonnet", resume=resume)

    return CodingSession(bus, KINDS[kind], context, connect=connect)


def tool(name: str, parent: str | None = None, **input: str) -> AssistantMessage:
    block = ToolUseBlock(id=f"t-{name}", name=name, input=input)
    return AssistantMessage(content=[block], model="m", parent_tool_use_id=parent)


def echo(prompt: str) -> UserMessage:
    """The CLI's replay of the prompt that starts a turn."""
    return UserMessage(content=prompt)


def usage() -> dict[str, int]:
    return {"total_tokens": 1, "tool_uses": 1, "duration_ms": 1}


async def test_options_come_from_the_kind_and_the_current_context(bus: EventBus) -> None:
    connect = FakeConnect([result("RESUMO: ok")])
    s = session(bus, connect, resume="abc", kind="implementacao")

    await s.run("a")

    [options] = connect.options
    assert options.setting_sources == ["user", "project", "local"]
    assert options.resume == "abc"
    assert s.name == "sistema" and s.kind is KINDS["implementacao"]


async def test_run_publishes_progress_with_phase_and_reply(bus: EventBus) -> None:
    queue = bus.subscribe()
    connect = FakeConnect(
        [tool("Bash", command="xrandr", description="Gira"), result("RESUMO: ok")]
    )
    s = session(bus, connect)

    reply = await s.run("gira a tela")
    await asyncio.sleep(0)

    assert reply.summary == "ok" and reply.session_id == "s1"
    assert connect.clients[0].prompts == ["gira a tela"]
    events = [(e["type"], e.get("session"), e.get("detail"), e.get("phase")) for e in drain(queue)]
    assert events == [
        ("agent_progress", "sistema", "Gira", "running"),
        ("alfred_reply", "sistema", None, None),
    ]


async def test_a_turn_left_unread_is_skipped_and_the_tasks_own_turn_answers(
    bus: EventBus,
) -> None:
    queue = bus.subscribe()
    connect = FakeConnect(
        [echo("sobe o web"), tool("Bash", description="Sobe"), result("RESUMO: subiu")],
        [echo("troca o botão"), tool("Edit", file_path="/c.tsx"), result("RESUMO: trocado")],
    )
    s = session(bus, connect)

    reply = await s.run("troca o botão")
    await asyncio.sleep(0)

    assert reply.summary == "trocado"
    events = [(e["type"], e.get("detail")) for e in drain(queue)]
    assert ("agent_progress", "Sobe") not in events
    assert [e for e in events if e[0] == "alfred_reply"] == [("alfred_reply", None)]


async def test_a_background_notification_turn_before_the_task_is_skipped(bus: EventBus) -> None:
    connect = FakeConnect(
        [echo("<task-notification>servidor parou</task-notification>"), result("RESUMO: ok")],
        [echo("lista os arquivos"), result("RESUMO: três arquivos")],
    )

    assert (await session(bus, connect).run("lista os arquivos")).summary == "três arquivos"


async def test_a_notification_merged_into_the_tasks_turn_still_answers(bus: EventBus) -> None:
    connect = FakeConnect(
        [echo("<task-notification>parou</task-notification>"), echo("a"), result("RESUMO: ok")]
    )

    assert (await session(bus, connect).run("a")).summary == "ok"


async def test_subagents_are_published_but_their_tools_are_not_the_sessions(
    bus: EventBus,
) -> None:
    queue = bus.subscribe()
    connect = FakeConnect(
        [
            tool("Agent", subagent_type="Explore", description="Acha o billing"),
            TaskStartedMessage(
                subtype="task_started",
                data={},
                task_id="k1",
                description="Acha o billing",
                uuid="u",
                session_id="s1",
                tool_use_id="t-Agent",
                task_type="Explore",
            ),
            tool("Grep", parent="t-Agent", pattern="refund"),
            TaskProgressMessage(
                subtype="task_progress",
                data={},
                task_id="k1",
                description="Acha o billing",
                usage=usage(),  # type: ignore[arg-type]
                uuid="u",
                session_id="s1",
                last_tool_name="Grep",
            ),
            TaskNotificationMessage(
                subtype="task_notification",
                data={},
                task_id="k1",
                status="completed",
                output_file="",
                summary="achei",
                uuid="u",
                session_id="s1",
            ),
            result("RESUMO: ok"),
        ]
    )

    await session(bus, connect).run("a")
    await asyncio.sleep(0)

    events = drain(queue)
    progress = [e["content"] for e in events if e["type"] == "agent_progress"]
    assert progress == ["Agent"]
    subagents = [(e["type"], e["id"]) for e in events if e["type"].startswith("subagent_")]
    assert subagents == [
        ("subagent_started", "k1"),
        ("subagent_progress", "k1"),
        ("subagent_finished", "k1"),
    ]
    started = next(e for e in events if e["type"] == "subagent_started")
    assert (started["session"], started["subagent_type"], started["description"]) == (
        "sistema",
        "Explore",
        "Acha o billing",
    )
    assert next(e for e in events if e["type"] == "subagent_progress")["last_tool"] == "Grep"
    assert next(e for e in events if e["type"] == "subagent_finished")["status"] == "completed"


async def test_init_message_announces_the_mcp_servers(bus: EventBus) -> None:
    queue = bus.subscribe()
    init = SystemMessage(
        subtype="init",
        data={"mcp_servers": [{"name": "gmail", "status": "connected"}, {"name": "context7"}]},
    )

    await session(bus, FakeConnect([init, result("RESUMO: ok")])).run("a")
    await asyncio.sleep(0)

    [seen] = [e for e in drain(queue) if e["type"] == "mcp_servers_seen"]
    assert seen["names"] == ["gmail", "context7"]


async def test_a_lost_resume_starts_fresh_and_says_so(bus: EventBus) -> None:
    queue = bus.subscribe()
    connect = FakeConnect([result("RESUMO: ok")], fail_resume=True)

    reply = await session(bus, connect, resume="gone").run("a")
    await asyncio.sleep(0)

    assert reply.summary == "ok"
    assert [o.resume for o in connect.options] == ["gone", None]
    [error] = [e for e in drain(queue) if e["type"] == "error"]
    assert "histórico" in error["message"]


async def test_missing_folder_fails_before_connecting(bus: EventBus, tmp_path: Path) -> None:
    connect = FakeConnect()

    with pytest.raises(AgentError, match="não existe"):
        await session(bus, connect, cwd=tmp_path / "gone").run("a")
    assert connect.options == []


async def test_failure_raises_agent_error_and_reconnects_next_time(bus: EventBus) -> None:
    connect = FakeConnect(ProcessError("boom"), [result("RESUMO: ok")])
    s = session(bus, connect)

    with pytest.raises(AgentError):
        await s.run("a")
    assert connect.clients[0].closed and not s.connected

    assert (await s.run("b")).summary == "ok"
    assert len(connect.clients) == 2


async def test_disconnect_closes_and_the_next_task_reconnects(bus: EventBus) -> None:
    connect = FakeConnect([result("RESUMO: a")], [result("RESUMO: b")])
    s = session(bus, connect)
    await s.run("a")
    assert s.connected

    await s.disconnect()

    assert connect.clients[0].closed and not s.connected
    assert (await s.run("b")).summary == "b"
    assert len(connect.clients) == 2


async def test_reply_carries_the_tokens_of_the_turn(bus: EventBus) -> None:
    done = result("RESUMO: ok")
    done.usage = {"input_tokens": 1200, "output_tokens": 300, "cache_read_input_tokens": 9}
    s = session(bus, FakeConnect([done]))

    assert (await s.run("a")).tokens == 1500
