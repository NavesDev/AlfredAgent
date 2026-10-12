from pathlib import Path

from infra.claude.agents import KINDS, AgentKind, GeneralAgent


def test_registry_has_the_general_kind() -> None:
    assert isinstance(KINDS["geral"], GeneralAgent)
    assert all(isinstance(k, AgentKind) and KINDS[k.kind] is k for k in KINDS.values())


def test_general_kind_runs_shell_and_files_but_no_web() -> None:
    kind = KINDS["geral"]

    assert {"Bash", "Read", "Edit", "Write"} <= set(kind.tools)
    assert not {"WebSearch", "WebFetch"} & set(kind.tools)
    assert kind.label == "Geral"


def test_general_prompt_names_the_session_and_asks_for_resumo() -> None:
    prompt = KINDS["geral"].prompt("downloads", Path("/home/u"))

    assert '"downloads"' in prompt and "/home/u" in prompt and "RESUMO:" in prompt


async def test_delegate_tool_defaults_to_sistema() -> None:
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
