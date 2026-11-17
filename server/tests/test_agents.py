from pathlib import Path

from infra.claude.agents import (
    KINDS,
    MAX_BUFFER,
    AgentKind,
    GeneralAgent,
    ImplementationAgent,
    SessionContext,
)

CTX = SessionContext(name="downloads", cwd=Path("/home/u"), model="sonnet")


def test_registry_has_both_kinds() -> None:
    assert isinstance(KINDS["geral"], GeneralAgent)
    assert isinstance(KINDS["implementacao"], ImplementationAgent)
    assert all(isinstance(k, AgentKind) and KINDS[k.kind] is k for k in KINDS.values())
    assert KINDS["implementacao"].needs_workspace and not KINDS["geral"].needs_workspace


def test_general_options_run_shell_and_files_isolated_from_mail_and_web() -> None:
    options = KINDS["geral"].options(CTX)

    assert {"Bash", "Read", "Edit", "Write"} <= set(options.tools)  # type: ignore[arg-type]
    assert not {"WebSearch", "WebFetch"} & set(options.tools)  # type: ignore[arg-type]
    assert options.strict_mcp_config and options.mcp_servers == {}
    assert options.setting_sources == []
    assert options.permission_mode == "auto"
    assert (options.cwd, options.model, options.resume) == (Path("/home/u"), "sonnet", None)
    assert '"downloads"' in options.system_prompt and "RESUMO:" in options.system_prompt  # type: ignore[operator]
    assert "APRESENTAR:" in options.system_prompt and "GUARDAR:" in options.system_prompt  # type: ignore[operator]
    assert KINDS["geral"].label == "Geral"


def test_options_carry_effort_and_resume() -> None:
    ctx = SessionContext(name="x", cwd=Path("/w"), model="opus", effort="high", resume="abc")

    options = KINDS["geral"].options(ctx)

    assert (options.model, options.effort, options.resume) == ("opus", "high", "abc")


def test_implementation_options_load_the_full_claude_code_harness() -> None:
    ctx = SessionContext(
        name="back",
        cwd=Path("/dev/api"),
        model="opus",
        effort="max",
        project="Recurve",
        workspace="back",
        mcp_disabled=("gmail", "plugin:engineering:google calendar", "claude.ai Gmail"),
    )

    options = KINDS["implementacao"].options(ctx)

    assert options.setting_sources == ["user", "project", "local"]
    assert options.skills == "all"
    assert options.tools is None and not options.strict_mcp_config
    assert options.permission_mode == "auto"
    assert options.disallowed_tools == [
        "mcp__gmail",
        "mcp__plugin_engineering_google_calendar",
        "mcp__claude_ai_Gmail",
    ]
    assert (options.cwd, options.model, options.effort) == (Path("/dev/api"), "opus", "max")
    prompt = options.system_prompt
    assert isinstance(prompt, dict) and prompt["type"] == "preset"
    assert prompt["preset"] == "claude_code"
    append = prompt["append"]
    assert '"back"' in append and "Recurve" in append and "RESUMO:" in append
    assert "APRESENTAR: relatório" in append
    assert "MCP" in append
    assert KINDS["implementacao"].label == "Implementação"


async def test_general_delegate_tool_defaults_to_sistema() -> None:
    calls: list[tuple[str, str]] = []

    def delegate(name: str, task: str) -> str:
        calls.append((name, task))
        return "enviado"

    tool = KINDS["geral"].delegate_tool(delegate)
    response = await tool.handler({"tarefa": "gira a tela"})
    await tool.handler({"tarefa": "baixa x", "sessao": "downloads"})

    assert tool.name == "delegar_geral"
    assert calls == [("sistema", "gira a tela"), ("downloads", "baixa x")]
    assert response["content"][0]["text"] == "enviado"
    assert tool.input_schema["required"] == ["tarefa"]


async def test_implementation_delegate_tool_needs_a_session() -> None:
    calls: list[tuple[str, str]] = []

    def delegate(name: str, task: str) -> str:
        calls.append((name, task))
        return "ok"

    tool = KINDS["implementacao"].delegate_tool(delegate)
    await tool.handler({"sessao": "back", "tarefa": "cria o endpoint"})

    assert tool.name == "delegar_implementacao"
    assert sorted(tool.input_schema["required"]) == ["sessao", "tarefa"]
    assert calls == [("back", "cria o endpoint")]


def test_every_kind_reads_big_cli_messages() -> None:
    # screenshots and long outputs overflow the SDK's 1 MB default and kill the task
    for kind in KINDS.values():
        assert kind.options(CTX).max_buffer_size == MAX_BUFFER >= 32 * 1024 * 1024
