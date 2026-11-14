from pathlib import Path
from typing import Any

import pytest

from controllers.projects import Projects
from controllers.settings import SettingsUpdate
from errors import AgentError, SessionNotFound
from events import EventBus
from infra.claude import permissions
from infra.claude.activity import describe_tool
from infra.claude.alfred import AlfredAgent
from infra.claude.tools import SERVER, session_tools
from tests.test_projects import FakeGit
from tests.test_sessions import Env, settle


class Tools:
    def __init__(self, env: Env, home: Path) -> None:
        self.env, self.home = env, home
        self.projects = Projects(env.db, env.sessions._bus, FakeGit())
        self.list = session_tools(env.sessions, self.projects)

    async def call(self, name: str, args: dict[str, Any]) -> str:
        tool = next(t for t in self.list if t.name == name)
        response = await tool.handler(args)
        return str(response["content"][0]["text"])


@pytest.fixture
async def tools(bus: EventBus, tmp_path: Path) -> Tools:
    return Tools(Env(bus, tmp_path), tmp_path)


def test_every_tool_is_allowed_without_asking(tools: Tools) -> None:
    names = {t.name for t in tools.list}

    assert names == {
        "delegar_geral",
        "delegar_implementacao",
        "criar_sessao",
        "limpar_sessao",
        "apagar_sessao",
        "listar_sessoes",
        "criar_projeto",
        "listar_projetos",
        "criar_ambiente",
        "criar_worktree",
        "apagar_ambiente",
        "definir_apelidos",
        "definir_descricao",
    }
    assert {f"mcp__{SERVER}__{n}" for n in names} <= set(permissions.ALLOWED)
    assert not {"Bash", "Edit", "Write"} & set(permissions.ALLOWED)


async def test_delegar_geral_reaches_the_session(tools: Tools) -> None:
    assert "sistema" in await tools.call("delegar_geral", {"tarefa": "gira a tela"})


async def test_errors_become_spoken_messages(tools: Tools) -> None:
    text = await tools.call("delegar_geral", {"tarefa": "a", "sessao": "backend"})

    assert text == "Não existe sessão chamada backend."
    with pytest.raises(SessionNotFound):
        tools.env.sessions.delegate("backend", "a")
    assert "Não existe projeto" in await tools.call(
        "criar_ambiente", {"projeto": "nada", "nome": "x", "pasta": "/"}
    )


async def test_listing_tells_why_a_session_failed(tools: Tools) -> None:
    tools.env.script("sistema", AgentError("Prompt is too long"))
    tools.env.sessions.delegate("sistema", "x")
    await settle()

    listed = await tools.call("listar_sessoes", {})

    assert "sistema" in listed and "último erro: Prompt is too long" in listed


async def test_listing_tells_a_task_waiting_for_a_slot(tools: Tools) -> None:
    tools.env.settings.update(SettingsUpdate(max_active_sessions=1))
    tools.env.sessions.create("geral", "downloads")
    tools.env.script("sistema", "hang")
    tools.env.sessions.delegate("sistema", "longa")
    await settle()
    tools.env.sessions.delegate("downloads", "baixar")
    await settle()

    listed = await tools.call("listar_sessoes", {})

    assert "downloads (Geral, " in listed
    assert "esperando vaga, vai fazer: baixar" in listed


async def test_lifecycle_tools(tools: Tools) -> None:
    created = await tools.call("criar_sessao", {"tipo": "geral", "nome": "downloads"})
    listed = await tools.call("listar_sessoes", {})
    cleared = await tools.call("limpar_sessao", {"nome": "downloads"})
    deleted = await tools.call("apagar_sessao", {"nome": "downloads"})
    refused = await tools.call("apagar_sessao", {"nome": "sistema"})
    await settle()

    assert "downloads" in created and "Geral" in created
    assert "sistema" in listed and "downloads" in listed
    assert "limpa" in cleared and "apagada" in deleted
    assert "só limpa" in refused
    assert [v.name for v in tools.env.sessions.list()] == ["sistema"]


async def test_project_workspace_worktree_and_implementation_session(tools: Tools) -> None:
    (tools.home / "api").mkdir()

    project = await tools.call("criar_projeto", {"nome": "Recurve", "apelidos": ["billing"]})
    workspace = await tools.call(
        "criar_ambiente", {"projeto": "billing", "nome": "back", "pasta": str(tools.home / "api")}
    )
    worktree = await tools.call(
        "criar_worktree", {"projeto": "Recurve", "ambiente_pai": "back", "nome": "cancel"}
    )
    session = await tools.call(
        "criar_sessao",
        {
            "tipo": "implementacao",
            "nome": "back",
            "projeto": "Recurve",
            "ambiente": "cancel",
            "modelo": "opus",
            "effort": "high",
        },
    )
    sent = await tools.call(
        "delegar_implementacao", {"sessao": "back", "tarefa": "cria o endpoint"}
    )
    listed = await tools.call("listar_projetos", {})
    await settle()

    assert "Recurve" in project and "back" in workspace and "cancel" in worktree
    assert "back" in session and "Implementação" in session
    assert "back" in sent
    assert "Recurve" in listed and "cancel" in listed and "back" in listed
    [view] = [v for v in tools.env.sessions.list() if v.name == "back"]
    assert (view.project, view.workspace, view.model, view.effort) == (
        "Recurve",
        "cancel",
        "opus",
        "high",
    )
    assert tools.env.made["back"].tasks == ["cria o endpoint"]


async def test_session_with_an_unknown_workspace_is_refused(tools: Tools) -> None:
    await tools.call("criar_projeto", {"nome": "Recurve"})

    text = await tools.call(
        "criar_sessao",
        {"tipo": "implementacao", "nome": "back", "projeto": "Recurve", "ambiente": "nada"},
    )

    assert "ambiente nada" in text


async def test_delete_workspace(tools: Tools) -> None:
    (tools.home / "api").mkdir()
    await tools.call("criar_projeto", {"nome": "Recurve"})
    await tools.call(
        "criar_ambiente", {"projeto": "Recurve", "nome": "back", "pasta": str(tools.home / "api")}
    )

    text = await tools.call("apagar_ambiente", {"projeto": "Recurve", "nome": "back"})

    assert "apagado" in text
    assert tools.projects.find("Recurve").workspaces == []


async def test_aliases_for_sessions_and_projects(tools: Tools) -> None:
    await tools.call("criar_sessao", {"tipo": "geral", "nome": "Site Sales", "apelidos": ["seils"]})
    tools.projects.create("Vrummy", [])

    said = await tools.call(
        "definir_apelidos", {"alvo": "sessao", "nome": "seils", "apelidos": ["saite seils"]}
    )
    assert said == "Apelidos da sessão Site Sales: saite seils."
    assert tools.env.sessions.list()[1].aliases == ["saite seils"]

    said = await tools.call(
        "definir_apelidos", {"alvo": "projeto", "nome": "vrummy", "apelidos": ["vrumi"]}
    )
    assert said == "Apelidos do projeto Vrummy: vrumi."
    assert tools.projects.find("vrumi").name == "Vrummy"

    said = await tools.call("definir_apelidos", {"alvo": "sessao", "nome": "x", "apelidos": []})
    assert said == "Não existe sessão chamada x."


def test_activity_labels() -> None:
    assert describe_tool("mcp__alfred__delegar_geral") == "Mandando para uma sessão"
    assert describe_tool("mcp__alfred__delegar_implementacao") == "Mandando para uma sessão"
    assert describe_tool("mcp__alfred__criar_sessao") == "Criando uma sessão"
    assert describe_tool("mcp__alfred__criar_projeto") == "Criando um projeto"
    assert describe_tool("mcp__alfred__listar_projetos") == "Vendo os projetos"
    assert describe_tool("mcp__alfred__criar_ambiente") == "Criando um ambiente"
    assert describe_tool("mcp__alfred__criar_worktree") == "Criando um worktree"
    assert describe_tool("mcp__alfred__apagar_ambiente") == "Apagando um ambiente"


def test_server_is_named_alfred(tools: Tools) -> None:
    agent = AlfredAgent(None, None, "sonnet", 1, tools=tools.list)  # type: ignore[arg-type]
    servers = agent._options(None).mcp_servers
    assert isinstance(servers, dict)
    assert dict(servers[SERVER])["name"] == SERVER == "alfred"


async def test_descriptions_by_voice_show_up_when_listing_projects(tools: Tools) -> None:
    (tools.home / "api").mkdir()
    await tools.call("criar_projeto", {"nome": "Recurve", "descricao": "Cobrança recorrente"})
    await tools.call(
        "criar_ambiente",
        {
            "projeto": "Recurve",
            "nome": "back",
            "pasta": str(tools.home / "api"),
            "descricao": "API",
        },
    )

    project = await tools.call(
        "definir_descricao", {"projeto": "Recurve", "descricao": "SaaS de cobrança recorrente"}
    )
    workspace = await tools.call(
        "definir_descricao",
        {"projeto": "Recurve", "ambiente": "back", "descricao": "API em Spring Boot"},
    )
    too_long = await tools.call("definir_descricao", {"projeto": "Recurve", "descricao": "x" * 201})
    listed = await tools.call("listar_projetos", {})

    assert "Recurve" in project and "back" in workspace
    assert "200" in too_long
    assert "SaaS de cobrança recorrente" in listed and "API em Spring Boot" in listed
    assert describe_tool("mcp__alfred__definir_descricao") == "Ajustando uma descrição"
