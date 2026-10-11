import asyncio
from pathlib import Path

import pytest
from claude_agent_sdk import AssistantMessage, ProcessError, ToolUseBlock

from errors import AgentError
from events import EventBus
from infra.claude.session import CodingSession
from tests.conftest import drain
from tests.test_alfred import FakeConnect, result


def session(bus: EventBus, connect: FakeConnect, timeout_s: float = 1) -> CodingSession:
    return CodingSession(bus, "sistema", Path("/home/u"), "sonnet", timeout_s, connect=connect)


async def test_options_give_shell_and_files_but_no_mail_or_web(bus: EventBus) -> None:
    options = session(bus, FakeConnect()).options()

    assert "Bash" in options.tools and "Write" in options.tools  # type: ignore[operator]
    assert not {"WebSearch", "WebFetch"} & set(options.tools)  # type: ignore[arg-type]
    assert options.permission_mode == "auto"
    assert options.strict_mcp_config and options.mcp_servers == {}
    assert options.setting_sources == []
    assert options.cwd == Path("/home/u")
    assert "RESUMO:" in str(options.system_prompt)


async def test_run_publishes_progress_and_reply_with_summary(bus: EventBus) -> None:
    queue = bus.subscribe()
    bash = ToolUseBlock(id="t", name="Bash", input={"command": "xrandr", "description": "Gira"})
    connect = FakeConnect(
        [AssistantMessage(content=[bash], model="m"), result("RESUMO: Tela girada.\nok")]
    )
    s = session(bus, connect)
    await s.start()

    reply = await s.run("gira a tela")
    await asyncio.sleep(0)

    assert reply.summary == "Tela girada."
    assert connect.clients[0].prompts == ["gira a tela"]
    events = [(e["type"], e.get("session"), e.get("detail")) for e in drain(queue)]
    assert events == [("agent_progress", "sistema", "Gira"), ("alfred_reply", "sistema", None)]


async def test_failure_raises_agent_error_and_reconnects_next_time(bus: EventBus) -> None:
    connect = FakeConnect(ProcessError("boom"), [result("RESUMO: ok")])
    s = session(bus, connect)
    await s.start()

    with pytest.raises(AgentError):
        await s.run("a")
    assert connect.clients[0].closed

    assert (await s.run("b")).summary == "ok"
    assert len(connect.clients) == 2


async def test_timeout_raises_agent_error(bus: EventBus) -> None:
    s = session(bus, FakeConnect(["hang"]), timeout_s=0.05)

    with pytest.raises(AgentError, match="timeout"):
        await s.run("a")
