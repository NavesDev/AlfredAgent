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
from infra.claude import permissions
from infra.claude.alfred import AlfredAgent, check_cli, setup_version, tool_detail
from infra.claude.state import DailyState
from tests.conftest import drain

TODAY = date(2026, 10, 1)
VERSION = setup_version([])  # what an agent built without tools runs under
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

    A callable in a run is invoked at that point of the stream instead of being yielded;
    "pause" suspends the stream briefly and "hang" past any timeout.
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
            elif message == "pause":
                await asyncio.sleep(0.01)
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


async def test_client_reads_only_streams_and_asks_for_resumo_first(
    bus: EventBus, tmp_path: Path
) -> None:
    connect = FakeConnect()
    await started(bus, tmp_path, connect)

    options = connect.options[0]
    assert options.tools == ["WebSearch", "WebFetch"]
    assert options.permission_mode == "auto"
    assert "mcp__claude_ai_Gmail__search_threads" in options.allowed_tools
    assert "mcp__claude_ai_Gmail__send_message" not in options.allowed_tools
    assert options.model == "sonnet"
    assert options.include_partial_messages
    assert "verificador automático" in str(options.system_prompt)
    assert "Comece" in str(options.system_prompt) and "RESUMO:" in str(options.system_prompt)


async def test_start_resumes_todays_session(bus: EventBus, tmp_path: Path) -> None:
    DailyState(tmp_path / "s.json").save("s1", TODAY, VERSION)
    connect = FakeConnect()

    await started(bus, tmp_path, connect)

    assert connect.options[0].resume == "s1"


async def test_reset_forgets_the_conversation(bus: EventBus, tmp_path: Path) -> None:
    queue = bus.subscribe()
    connect = FakeConnect([result(session_id="s1")], [result(session_id="s2")])
    alfred = await started(bus, tmp_path, connect)
    await spoken_for(alfred)

    await alfred.reset()
    await asyncio.sleep(0)

    assert connect.clients[0].closed
    assert DailyState(tmp_path / "s.json").session_for(TODAY, VERSION) is None
    assert [e["type"] for e in drain(queue)][-1] == "alfred_cleared"
    await spoken_for(alfred)
    assert connect.options[-1].resume is None


async def test_reset_waits_for_the_current_answer(bus: EventBus, tmp_path: Path) -> None:
    connect = FakeConnect(["pause", result()])
    alfred = await started(bus, tmp_path, connect)
    asking = asyncio.create_task(spoken_for(alfred))
    await asyncio.sleep(0)  # the answer is now streaming

    await alfred.reset()

    assert asking.done() and await asking == ["JWT é stateless; sessão fica no server."]
    assert connect.clients[0].closed


async def test_changed_setup_starts_a_fresh_session(bus: EventBus, tmp_path: Path) -> None:
    DailyState(tmp_path / "s.json").save("s1", TODAY, "older-setup")
    connect = FakeConnect()

    await started(bus, tmp_path, connect)

    assert connect.options[0].resume is None


def test_setup_version_follows_the_tools() -> None:
    from infra.claude.tools import session_tools

    tools = session_tools(None, None)  # type: ignore[arg-type]
    assert setup_version(tools) == setup_version(tools) != setup_version(tools[1:])


async def test_failed_resume_connects_fresh(bus: EventBus, tmp_path: Path) -> None:
    DailyState(tmp_path / "s.json").save("stale", TODAY, VERSION)
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

    assert DailyState(tmp_path / "s.json").session_for(TODAY, VERSION) == "s9"


async def test_streams_progress_and_publishes_reply(bus: EventBus, tmp_path: Path) -> None:
    queue = bus.subscribe()
    stream = AssistantMessage(
        content=[
            ToolUseBlock(id="t", name="WebSearch", input={"query": "notícias de IA"}),
            TextBlock(text="Pensando"),
        ],
        model="sonnet",
    )
    alfred = await started(bus, tmp_path, FakeConnect([stream, result()]))
    activities: list[str] = []

    await alfred.ask("oi", lambda _: None, activities.append)
    await asyncio.sleep(0)

    assert activities == ["Pesquisando na web"]
    events = [(e["type"], e.get("kind"), e.get("content"), e.get("detail")) for e in drain(queue)]
    assert events[0][:4] == ("agent_progress", "tool", "WebSearch", "notícias de IA")
    assert events == [
        ("agent_progress", "tool", "WebSearch", "notícias de IA"),
        ("agent_progress", "text", "Pensando", None),
        ("alfred_reply", None, None, None),
    ]


async def test_failure_raises_agent_error_and_next_ask_reconnects_fresh(
    bus: EventBus, tmp_path: Path
) -> None:
    DailyState(tmp_path / "s.json").save("s1", TODAY, VERSION)
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


def test_main_agent_never_gets_exec_or_file_tools() -> None:
    """ADR 0003: whoever reads external content must not execute or write."""
    exec_tools = {"Bash", "Edit", "Write", "NotebookEdit", "MultiEdit"}
    assert not exec_tools & set(permissions.BUILTIN_TOOLS)
    assert not exec_tools & set(permissions.ALLOWED)


def test_no_write_tool_is_both_allowed_and_hidden() -> None:
    assert not set(permissions.ALLOWED) & set(permissions.HIDDEN)


@pytest.mark.parametrize(
    ("tool_input", "expected"),
    [
        ({"query": "previsão do tempo"}, "previsão do tempo"),
        ({"url": "https://www.linkedin.com/feed/"}, "www.linkedin.com"),
        ({"selector": "#x"}, None),
        ({"query": ""}, None),
    ],
)
def test_tool_detail(tool_input: dict[str, Any], expected: str | None) -> None:
    assert tool_detail(tool_input) == expected


@pytest.mark.parametrize(
    ("url", "denied"),
    [
        ("https://www.linkedin.com", False),
        ("HTTP://example.com", False),
        ("file:///home/naves/Projetos/", True),
        (" file:///etc/passwd", True),
        ("chrome://settings", True),
        ("javascript:alert(1)", True),
    ],
)
async def test_block_local_urls(url: str, denied: bool) -> None:
    out = await permissions.block_local_urls(
        {"tool_name": "navigate_page", "tool_input": {"url": url}}, None, {"signal": None}
    )
    assert ("'deny'" in repr(out)) is denied


async def test_block_local_urls_ignores_tools_without_url() -> None:
    assert (
        await permissions.block_local_urls({"tool_input": {"query": "x"}}, None, {"signal": None})
        == {}
    )


def test_options_install_the_url_hook() -> None:
    import claude_agent_sdk as sdk

    from infra.claude.alfred import AlfredAgent

    options = AlfredAgent(None, None, "sonnet", 1)._options(None)  # type: ignore[arg-type]
    [matcher] = options.hooks["PreToolUse"]  # type: ignore[index]
    assert isinstance(matcher, sdk.HookMatcher) and matcher.matcher is None
    assert matcher.hooks == [permissions.block_local_urls]


def test_agent_exposes_tools_server_as_alfred() -> None:
    from infra.claude.tools import session_tools

    tools = session_tools(None, None)  # type: ignore[arg-type]
    options = AlfredAgent(None, None, "sonnet", 1, tools=tools)._options(None)  # type: ignore[arg-type]
    assert isinstance(options.mcp_servers, dict)
    assert list(options.mcp_servers) == ["alfred"]
    assert dict(options.mcp_servers["alfred"])["name"] == "alfred"
    assert "delegar_geral" in str(options.system_prompt)
    assert "apagar_sessao" in str(options.system_prompt)
    assert options.model == "sonnet"


async def test_settings_change_reopens_with_the_new_model_and_same_conversation(
    bus: EventBus, tmp_path: Path
) -> None:
    current: list[tuple[str, str | None]] = [("sonnet", None)]
    connect = FakeConnect([result(session_id="s1")], [result(session_id="s1")])
    alfred = AlfredAgent(
        bus,
        DailyState(tmp_path / "s.json"),
        model=lambda: current[0],
        timeout_s=1,
        connect=connect,
        today=lambda: TODAY,
    )
    await alfred.start()
    await spoken_for(alfred)

    current[0] = ("opus", "high")
    await spoken_for(alfred)

    assert [(o.model, o.effort, o.resume) for o in connect.options] == [
        ("sonnet", None, None),
        ("opus", "high", "s1"),
    ]
    assert connect.clients[0].closed


def test_prompt_routes_code_to_implementation_sessions() -> None:
    from infra.claude.alfred import SYSTEM_PROMPT

    for name in ("delegar_implementacao", "criar_projeto", "criar_worktree", "apagar_workspace"):
        assert name in SYSTEM_PROMPT
