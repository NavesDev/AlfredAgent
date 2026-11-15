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
        self.git = FakeGit()
        self.projects = Projects(
            env.db, env.sessions._bus, self.git, mode=lambda: env.settings.app().implementation_mode
        )
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
        "ver_ambiente",
        "iniciar_feature",
        "definir_ambiente_padrao",
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


async def test_ver_ambiente_tells_branch_changes_and_commits(tools: Tools, tmp_path: Path) -> None:
    (tmp_path / "back").mkdir()
    tools.git.dirty = True
    await tools.call("criar_projeto", {"nome": "Recurve"})
    await tools.call(
        "criar_ambiente", {"projeto": "Recurve", "nome": "back", "pasta": str(tmp_path / "back")}
    )

    text = await tools.call("ver_ambiente", {"projeto": "Recurve", "ambiente": "back"})

    assert "main" in text and "2 arquivos alterados" in text and "add login" in text
    assert "fix/12-login" in text and "docs/3-sprint" in text


async def test_ver_ambiente_speaks_the_error(tools: Tools, tmp_path: Path) -> None:
    await tools.call("criar_projeto", {"nome": "Recurve"})
    assert "não tem o ambiente" in await tools.call(
        "ver_ambiente", {"projeto": "Recurve", "ambiente": "nada"}
    )
    (tmp_path / "solto").mkdir()
    await tools.call(
        "criar_ambiente", {"projeto": "Recurve", "nome": "solto", "pasta": str(tmp_path / "solto")}
    )
    tools.git.fail = True
    assert "not a git repository" in await tools.call(
        "ver_ambiente", {"projeto": "Recurve", "ambiente": "solto"}
    )


async def recurve_with(tools: Tools, tmp_path: Path, *names: str) -> None:
    await tools.call("criar_projeto", {"nome": "Recurve"})
    for name in names:
        (tmp_path / name).mkdir()
        await tools.call(
            "criar_ambiente", {"projeto": "Recurve", "nome": name, "pasta": str(tmp_path / name)}
        )


async def test_iniciar_feature_opens_worktree_and_session_and_delegates(
    tools: Tools, tmp_path: Path
) -> None:
    await recurve_with(tools, tmp_path, "back")

    text = await tools.call(
        "iniciar_feature",
        {"projeto": "Recurve", "feature": "Cancelamento", "tarefa": "implementa o cancelamento"},
    )
    await settle()

    assert "feat/cancelamento" in text and "cancelamento" in text
    [view] = [v for v in tools.env.sessions.list() if v.workspace == "cancelamento"]
    assert view.kind == "implementacao"
    assert view.status == "busy" or view.tasks_done or view.queue


async def test_iniciar_feature_in_workspace_mode_reuses_its_session(
    tools: Tools, tmp_path: Path
) -> None:
    await recurve_with(tools, tmp_path, "back")
    tools.env.settings.update(SettingsUpdate(implementation_mode="ambiente"))
    await tools.call(
        "criar_sessao",
        {"tipo": "implementacao", "nome": "api", "projeto": "Recurve", "ambiente": "back"},
    )

    text = await tools.call(
        "iniciar_feature", {"projeto": "Recurve", "feature": "login", "tarefa": "faz o login"}
    )

    assert "api" in text and "worktree" not in text.lower()
    assert len([v for v in tools.env.sessions.list() if v.project == "Recurve"]) == 1


async def test_iniciar_feature_without_default_asks(tools: Tools) -> None:
    await tools.call("criar_projeto", {"nome": "Recurve"})

    text = await tools.call(
        "iniciar_feature", {"projeto": "Recurve", "feature": "login", "tarefa": "faz"}
    )

    assert "ambiente padrão" in text
    assert not [v for v in tools.env.sessions.list() if v.project == "Recurve"]


async def test_definir_ambiente_padrao(tools: Tools, tmp_path: Path) -> None:
    await recurve_with(tools, tmp_path, "back", "front")

    text = await tools.call("definir_ambiente_padrao", {"projeto": "Recurve", "ambiente": "front"})

    found = tools.projects.find("Recurve")
    assert "front" in text
    assert found.default_workspace_id == next(w.id for w in found.workspaces if w.name == "front")


async def test_iniciar_feature_uses_alfreds_branch_and_choice(tools: Tools, tmp_path: Path) -> None:
    await recurve_with(tools, tmp_path, "back")

    text = await tools.call(
        "iniciar_feature",
        {
            "projeto": "Recurve",
            "feature": "issue 12 login",
            "tarefa": "implementa a issue 12",
            "branch": "fix/12-login",
        },
    )

    assert "fix/12-login" in text
    assert tools.git.added[-1][2] == "fix/12-login"


async def test_listar_projetos_tells_each_workspace_mode(tools: Tools, tmp_path: Path) -> None:
    await recurve_with(tools, tmp_path, "back", "front")
    found = tools.projects.find("Recurve")
    front = next(w for w in found.workspaces if w.name == "front")
    tools.projects.update_workspace(front.id, implementation_mode="ambiente")

    text = await tools.call("listar_projetos", {})

    assert "padrão" in text
    assert "features em worktree" in text and "features no próprio ambiente" in text
