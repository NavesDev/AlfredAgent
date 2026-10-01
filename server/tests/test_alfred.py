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
    StreamEvent,
    TextBlock,
    ToolUseBlock,
)

from errors import AgentError, DependencyError
from events import EventBus
from infra.claude.alfred import AlfredAgent, check_cli
from infra.claude.state import DailyState
from tests.conftest import drain

TODAY = date(2026, 10, 1)
REPLY = "RESUMO: JWT é stateless; sessão fica no server.\nJWT guarda o estado no token."
Run = list[Any] | Exception


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


def delta(text: str) -> StreamEvent:
    event = {"type": "content_block_delta", "delta": {"type": "text_delta", "text": text}}
    return StreamEvent(uuid="u", session_id="s1", event=event)


class FakeClient:
    """Stands in for ClaudeSDKClient: each query plays the next scripted run.

    A callable in a run is invoked at that point of the stream instead of being yielded.
    """

    def __init__(self, runs: list[Run]) -> None:
        self.runs, self.closed = runs, False
        self.prompts: list[str] = []

    async def query(self, prompt: str) -> None:
        self.prompts.append(prompt)

    async def receive_response(self) -> AsyncIterator[Any]:
        run = self.runs.pop(0)
        if isinstance(run, Exception):
            raise run
        for message in run:
            if message == "hang":
                await asyncio.sleep(10)
            elif callable(message):
                message()
            else:
                yield message

    async def disconnect(self) -> None:
        self.closed = True


class FakeConnect:
    """Stands in for connecting a ClaudeSDKClient; records the options of each connection."""

    def __init__(self, *runs: Run, fail_resume: bool = False) -> None:
        self.runs, self.fail_resume = list(runs), fail_resume
        self.options: list[ClaudeAgentOptions] = []
        self.clients: list[FakeClient] = []

    async def __call__(self, options: ClaudeAgentOptions) -> FakeClient:
        self.options.append(options)
        if options.resume and self.fail_resume:
            raise ProcessError("no such session")
        self.clients.append(FakeClient(self.runs))
        return self.clients[-1]


def agent(bus: EventBus, tmp_path: Path, connect: FakeConnect, **kw: Any) -> AlfredAgent:
    return AlfredAgent(
        bus,
        DailyState(tmp_path / "s.json"),
        model="sonnet",
        timeout_s=kw.get("timeout_s", 1),
        connect=connect,
        today=kw.get("today", lambda: TODAY),
    )


async def started(bus: EventBus, tmp_path: Path, connect: FakeConnect, **kw: Any) -> AlfredAgent:
    alfred = agent(bus, tmp_path, connect, **kw)
    await alfred.start()
    return alfred


async def spoken_for(alfred: AlfredAgent, text: str = "oi") -> list[str]:
    spoken: list[str] = []
    await alfred.ask(text, spoken.append)
    return spoken


async def test_speaks_resumo_line_as_soon_as_it_streams(bus: EventBus, tmp_path: Path) -> None:
    spoken: list[str] = []
    heard_mid_stream: list[str] = []
    stream = [
        delta("RESUMO: JWT é "),
        delta("stateless.\nDetalhes"),
        lambda: heard_mid_stream.extend(spoken),
        result(),
    ]
    alfred = await started(bus, tmp_path, FakeConnect(stream))

    await alfred.ask("oi", spoken.append)

    assert heard_mid_stream == ["JWT é stateless."]
    assert spoken == ["JWT é stateless."]


async def test_without_early_resumo_speaks_extracted_summary_at_end(
    bus: EventBus, tmp_path: Path
) -> None:
    stream = [delta("Python é de 1991.\n"), result("Python é de 1991. Por Guido.")]
    alfred = await started(bus, tmp_path, FakeConnect(stream))

    assert await spoken_for(alfred) == ["Python é de 1991."]


async def test_reply_carries_full_text_and_spoken_summary(bus: EventBus, tmp_path: Path) -> None:
    alfred = await started(bus, tmp_path, FakeConnect([result()]))

    reply = await alfred.ask("oi", lambda _: None)

    assert reply.text == REPLY
    assert reply.summary == "JWT é stateless; sessão fica no server."


async def test_connects_once_and_reuses_client(bus: EventBus, tmp_path: Path) -> None:
    connect = FakeConnect([result()], [result()])
    alfred = await started(bus, tmp_path, connect)

    await spoken_for(alfred, "oi")
    await spoken_for(alfred, "e aí?")

    assert len(connect.options) == 1
    assert connect.clients[0].prompts == ["oi", "e aí?"]


async def test_client_runs_without_tools_streams_and_asks_for_resumo_first(
    bus: EventBus, tmp_path: Path
) -> None:
    connect = FakeConnect()
    await started(bus, tmp_path, connect)

    options = connect.options[0]
    assert options.tools == []
    assert options.model == "sonnet"
    assert options.include_partial_messages
    assert "Comece" in str(options.system_prompt) and "RESUMO:" in str(options.system_prompt)


async def test_start_resumes_todays_session(bus: EventBus, tmp_path: Path) -> None:
    DailyState(tmp_path / "s.json").save("s1", TODAY)
    connect = FakeConnect()

    await started(bus, tmp_path, connect)

    assert connect.options[0].resume == "s1"


async def test_failed_resume_connects_fresh(bus: EventBus, tmp_path: Path) -> None:
    DailyState(tmp_path / "s.json").save("stale", TODAY)
    connect = FakeConnect(fail_resume=True)

    await started(bus, tmp_path, connect)

    assert [o.resume for o in connect.options] == ["stale", None]


async def test_start_failure_raises_dependency_error(bus: EventBus, tmp_path: Path) -> None:
    class Broken(FakeConnect):
        async def __call__(self, options: ClaudeAgentOptions) -> FakeClient:
            raise ProcessError("not logged in")

    with pytest.raises(DependencyError, match="not logged in"):
        await started(bus, tmp_path, Broken())


async def test_new_day_reconnects_with_fresh_session(bus: EventBus, tmp_path: Path) -> None:
    day = [TODAY]
    connect = FakeConnect([result()], [result(session_id="s2")])
    alfred = await started(bus, tmp_path, connect, today=lambda: day[0])
    await spoken_for(alfred)

    day[0] = date(2026, 10, 2)
    await spoken_for(alfred)

    assert [o.resume for o in connect.options] == [None, None]
    assert connect.clients[0].closed


async def test_saves_session_id_after_reply(bus: EventBus, tmp_path: Path) -> None:
    alfred = await started(bus, tmp_path, FakeConnect([result(session_id="s9")]))

    await spoken_for(alfred)

    assert DailyState(tmp_path / "s.json").session_for(TODAY) == "s9"


async def test_streams_progress_and_publishes_reply(bus: EventBus, tmp_path: Path) -> None:
    queue = bus.subscribe()
    stream = AssistantMessage(
        content=[ToolUseBlock(id="t", name="WebSearch", input={}), TextBlock(text="Pensando")],
        model="sonnet",
    )
    alfred = await started(bus, tmp_path, FakeConnect([stream, result()]))

    await spoken_for(alfred)
    await asyncio.sleep(0)

    events = [(e["type"], e.get("kind"), e.get("content")) for e in drain(queue)]
    assert events == [
        ("agent_progress", "tool", "WebSearch"),
        ("agent_progress", "text", "Pensando"),
        ("alfred_reply", None, None),
    ]


async def test_failure_raises_agent_error_and_next_ask_reconnects_fresh(
    bus: EventBus, tmp_path: Path
) -> None:
    DailyState(tmp_path / "s.json").save("s1", TODAY)
    connect = FakeConnect(ProcessError("boom"), [result()])
    alfred = await started(bus, tmp_path, connect)

    with pytest.raises(AgentError):
        await spoken_for(alfred)
    await spoken_for(alfred)

    assert [o.resume for o in connect.options] == ["s1", None]
    assert connect.clients[0].closed


async def test_error_result_raises_agent_error(bus: EventBus, tmp_path: Path) -> None:
    alfred = await started(bus, tmp_path, FakeConnect([result(is_error=True)]))

    with pytest.raises(AgentError):
        await spoken_for(alfred)


async def test_timeout_raises_agent_error(bus: EventBus, tmp_path: Path) -> None:
    alfred = await started(bus, tmp_path, FakeConnect(["hang"]), timeout_s=0.01)

    with pytest.raises(AgentError, match="timeout"):
        await spoken_for(alfred)


def test_check_cli_fails_fast_when_claude_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PATH", "")
    with pytest.raises(DependencyError, match="claude"):
        check_cli()
