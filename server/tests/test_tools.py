from pathlib import Path
from typing import Any

import pytest

from controllers.sessions import Sessions
from errors import SessionNotFound
from events import EventBus
from infra.claude import permissions
from infra.claude.activity import describe_tool
from infra.claude.tools import SERVER, alfred_tools, session_tools
from tests.test_sessions import Factory, FakeSession, FakeTalker, settle


@pytest.fixture
async def sessions(bus: EventBus, tmp_path: Path) -> Sessions:
    s = Sessions(bus, FakeTalker(), Factory(), max_active=3, home=tmp_path)
    s.add(FakeSession("sistema"), protected=True)
    return s


async def call(sessions: Sessions, name: str, args: dict[str, Any]) -> str:
    tool = next(t for t in session_tools(sessions) if t.name == name)
    response = await tool.handler(args)
    return str(response["content"][0]["text"])


def test_every_tool_is_allowed_without_asking(sessions: Sessions) -> None:
    names = {t.name for t in session_tools(sessions)}

    assert names == {
        "delegar_geral",
        "criar_sessao",
        "limpar_sessao",
        "apagar_sessao",
        "listar_sessoes",
    }
    assert {f"mcp__{SERVER}__{n}" for n in names} <= set(permissions.ALLOWED)
    assert not {"Bash", "Edit", "Write"} & set(permissions.ALLOWED)


async def test_delegar_geral_reaches_the_session(sessions: Sessions) -> None:
    assert "sistema" in await call(sessions, "delegar_geral", {"tarefa": "gira a tela"})


async def test_errors_become_spoken_messages(sessions: Sessions) -> None:
    text = await call(sessions, "delegar_geral", {"tarefa": "a", "sessao": "backend"})

    assert text == "Não existe sessão chamada backend."
    with pytest.raises(SessionNotFound):
        sessions.delegate("backend", "a")


async def test_lifecycle_tools(sessions: Sessions) -> None:
    created = await call(sessions, "criar_sessao", {"tipo": "geral", "nome": "downloads"})
    listed = await call(sessions, "listar_sessoes", {})
    cleared = await call(sessions, "limpar_sessao", {"nome": "downloads"})
    deleted = await call(sessions, "apagar_sessao", {"nome": "downloads"})
    refused = await call(sessions, "apagar_sessao", {"nome": "sistema"})
    await settle()

    assert "downloads" in created and "Geral" in created
    assert "sistema" in listed and "downloads" in listed
    assert "limpa" in cleared and "apagada" in deleted
    assert "só limpa" in refused
    assert [v.name for v in sessions.list()] == ["sistema"]


def test_activity_labels() -> None:
    assert describe_tool("mcp__alfred__delegar_geral") == "Mandando para uma sessão"
    assert describe_tool("mcp__alfred__criar_sessao") == "Criando uma sessão"
    assert describe_tool("mcp__alfred__limpar_sessao") == "Limpando uma sessão"
    assert describe_tool("mcp__alfred__apagar_sessao") == "Apagando uma sessão"
    assert describe_tool("mcp__alfred__listar_sessoes") == "Vendo as sessões"


def test_server_is_named_alfred(sessions: Sessions) -> None:
    assert alfred_tools(sessions)["name"] == SERVER == "alfred"
