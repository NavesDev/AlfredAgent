import asyncio
from collections.abc import AsyncIterator
from datetime import date
from pathlib import Path
from typing import Any

import pytest
from claude_agent_sdk import (
    AssistantMessage,
    ClaudeAgentOptions,
    ProcessError,
    ResultMessage,
    TextBlock,
    ToolUseBlock,
)

from errors import AgentError, DependencyError
from events import EventBus
from infra.claude.alfred import AlfredAgent, check_cli
from infra.claude.state import DailyState
from tests.conftest import drain

TODAY = date(2026, 10, 1)
REPLY = "JWT guarda o estado no token.\nRESUMO: JWT é stateless; sessão fica no server."


def result(text: str = REPLY, session_id: str = "s1", is_error: bool = False) -> ResultMessage:
    return ResultMessage(
        subtype="success",
        duration_ms=1,
        duration_api_ms=1,
        is_error=is_error,
        num_turns=1,
        session_id=session_id,
        result=text,
    )


class FakeQuery:
    """Stands in for claude_agent_sdk.query, recording the options of each call."""

    def __init__(self, *runs: list[Any] | Exception) -> None:
        self.runs = list(runs)
        self.calls: list[ClaudeAgentOptions] = []

    async def __call__(self, *, prompt: str, options: ClaudeAgentOptions) -> AsyncIterator[Any]:
        self.calls.append(options)
        run = self.runs.pop(0)
        if isinstance(run, Exception):
            raise run
        for message in run:
            if message == "hang":
                await asyncio.sleep(10)
            yield message


def agent(bus: EventBus, tmp_path: Path, query: FakeQuery, timeout_s: float = 1) -> AlfredAgent:
    return AlfredAgent(
        bus,
        DailyState(tmp_path / "s.json"),
        model="sonnet",
        timeout_s=timeout_s,
        query=query,
        today=lambda: TODAY,
    )


async def test_ask_returns_reply_with_summary(bus: EventBus, tmp_path: Path) -> None:
    reply = await agent(bus, tmp_path, FakeQuery([result()])).ask("JWT ou sessão?")

    assert reply.text == REPLY
    assert reply.summary == "JWT é stateless; sessão fica no server."


async def test_ask_runs_without_tools_and_asks_for_resumo(bus: EventBus, tmp_path: Path) -> None:
    query = FakeQuery([result()])
    await agent(bus, tmp_path, query).ask("oi")

    options = query.calls[0]
    assert options.tools == []
    assert options.model == "sonnet"
    assert "RESUMO:" in str(options.system_prompt)


async def test_ask_streams_progress_and_publishes_reply(bus: EventBus, tmp_path: Path) -> None:
    queue = bus.subscribe()
    stream = AssistantMessage(
        content=[ToolUseBlock(id="t", name="WebSearch", input={}), TextBlock(text="Pensando")],
        model="sonnet",
    )
    await agent(bus, tmp_path, FakeQuery([stream, result()])).ask("oi")
    await asyncio.sleep(0)

    events = [(e["type"], e.get("kind"), e.get("content")) for e in drain(queue)]
    assert events == [
        ("agent_progress", "tool", "WebSearch"),
        ("agent_progress", "text", "Pensando"),
        ("alfred_reply", None, None),
    ]


async def test_second_ask_same_day_resumes_session(bus: EventBus, tmp_path: Path) -> None:
    query = FakeQuery([result(session_id="s1")], [result(session_id="s1")])
    alfred = agent(bus, tmp_path, query)

    await alfred.ask("oi")
    await alfred.ask("e aí?")

    assert [c.resume for c in query.calls] == [None, "s1"]


async def test_failed_resume_retries_with_fresh_session(bus: EventBus, tmp_path: Path) -> None:
    DailyState(tmp_path / "s.json").save("stale", TODAY)
    query = FakeQuery(ProcessError("no such session"), [result(session_id="s2")])

    await agent(bus, tmp_path, query).ask("oi")

    assert [c.resume for c in query.calls] == ["stale", None]
    assert DailyState(tmp_path / "s.json").session_for(TODAY) == "s2"


async def test_sdk_failure_raises_agent_error(bus: EventBus, tmp_path: Path) -> None:
    with pytest.raises(AgentError):
        await agent(bus, tmp_path, FakeQuery(ProcessError("boom"))).ask("oi")


async def test_error_result_raises_agent_error(bus: EventBus, tmp_path: Path) -> None:
    with pytest.raises(AgentError):
        await agent(bus, tmp_path, FakeQuery([result(is_error=True)])).ask("oi")


async def test_timeout_raises_agent_error(bus: EventBus, tmp_path: Path) -> None:
    with pytest.raises(AgentError, match="timeout"):
        await agent(bus, tmp_path, FakeQuery(["hang"]), timeout_s=0.01).ask("oi")


def test_check_cli_fails_fast_when_claude_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PATH", "")
    with pytest.raises(DependencyError, match="claude"):
        check_cli()
