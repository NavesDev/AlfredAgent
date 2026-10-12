"""In-process MCP tools for the main agent. Logic lives in controllers; these only adapt.

One delegate tool per agent kind, generic tools for the session lifecycle (ADR 0007), and tools
for projects and workspaces. Errors come back as the sentence Alfred says.
"""

from collections.abc import Awaitable, Callable
from typing import TYPE_CHECKING, Any

import claude_agent_sdk as sdk

from errors import GitError, ProjectError, SessionError
from infra.claude.agents import KINDS

if TYPE_CHECKING:
    from controllers.projects import Projects
    from controllers.sessions import Sessions

SERVER = "alfred"  # MCP server name the main agent sees these tools under
EFFORTS = ["low", "medium", "high", "xhigh", "max"]

Result = dict[str, Any]


def session_tools(sessions: "Sessions", projects: "Projects") -> list[sdk.SdkMcpTool[Any]]:
    def delegate(name: str, task: str) -> str:
        try:
            return sessions.delegate(name, task)
        except SessionError as e:
            return str(e)

    def workspace_id(project_name: str, name: str) -> int:
        found = projects.find(project_name)
        ws = next((w for w in found.workspaces if w.name.lower() == name.strip().lower()), None)
        if ws is None:
            raise ProjectError(f"O projeto {found.name} não tem o workspace {name}.")
        return ws.id

    @sdk.tool(
        "criar_sessao",
        "Cria uma sessão nomeada que fica disponível para delegar tarefas. "
        f"Tipos: {', '.join(f'{k} ({v.label})' for k, v in KINDS.items())}. "
        "Implementação precisa de 'projeto' e 'workspace'; geral aceita os dois opcionais "
        "(sem eles, roda na home). 'modelo' e 'effort' só quando o usuário pedir.",
        {
            "type": "object",
            "properties": {
                "tipo": {"type": "string", "enum": list(KINDS)},
                "nome": {"type": "string"},
                "projeto": {"type": "string"},
                "workspace": {"type": "string"},
                "modelo": {"type": "string"},
                "effort": {"type": "string", "enum": EFFORTS},
            },
            "required": ["tipo", "nome"],
        },
    )
    async def criar_sessao(args: Result) -> Result:
        async def run() -> str:
            ws = None
            if args.get("projeto") or args.get("workspace"):
                ws = workspace_id(str(args.get("projeto", "")), str(args.get("workspace", "")))
            view = sessions.create(
                str(args["tipo"]), str(args["nome"]), ws, args.get("modelo"), args.get("effort")
            )
            where = f"{view.project}, workspace {view.workspace}" if view.project else view.cwd
            return f"Sessão {view.name} criada, tipo {view.label}, em {where}."

        return await _speak(run)

    @sdk.tool(
        "limpar_sessao",
        "Limpa uma sessão: cancela o que ela está fazendo, esvazia a fila e apaga o contexto "
        "da conversa. A sessão continua existindo.",
        {"nome": str},
    )
    async def limpar_sessao(args: Result) -> Result:
        async def run() -> str:
            view = await sessions.clear(str(args["nome"]))
            return f"Sessão {view.name} limpa."

        return await _speak(run)

    @sdk.tool(
        "apagar_sessao",
        "Apaga uma sessão e todo o contexto dela. Confirme com o usuário antes de chamar.",
        {"nome": str},
    )
    async def apagar_sessao(args: Result) -> Result:
        async def run() -> str:
            await sessions.delete(str(args["nome"]))
            return f"Sessão {args['nome']} apagada."

        return await _speak(run)

    @sdk.tool(
        "listar_sessoes",
        "Lista as sessões com tipo, projeto, workspace, status, tarefa atual e, quando a "
        "última tarefa falhou, o motivo do erro.",
        {},
    )
    async def listar_sessoes(args: Result) -> Result:
        async def run() -> str:
            return "\n".join(
                f"{v.name} ({v.label}, "
                + (f"{v.project}/{v.workspace}" if v.project else v.cwd)
                + f"): {v.status}"
                + (f", fazendo: {v.task}" if v.task else "")
                + (f", {v.queue} na fila" if v.queue else "")
                + (f", último erro: {v.last_error}" if v.last_error else "")
                for v in sessions.list()
            )

        return await _speak(run)

    @sdk.tool(
        "criar_projeto",
        "Cadastra um projeto: um nome que agrupa workspaces (pastas) e sessões. "
        "'apelidos' ajudam a reconhecer o nome falado.",
        {
            "type": "object",
            "properties": {
                "nome": {"type": "string"},
                "apelidos": {"type": "array", "items": {"type": "string"}},
            },
            "required": ["nome"],
        },
    )
    async def criar_projeto(args: Result) -> Result:
        async def run() -> str:
            created = projects.create(str(args["nome"]), [str(a) for a in args.get("apelidos", [])])
            return f"Projeto {created.name} criado."

        return await _speak(run)

    @sdk.tool("listar_projetos", "Lista os projetos com seus workspaces e sessões.", {})
    async def listar_projetos(args: Result) -> Result:
        async def run() -> str:
            by_workspace: dict[tuple[str | None, str | None], list[str]] = {}
            for v in sessions.list():
                by_workspace.setdefault((v.project, v.workspace), []).append(v.name)
            lines = []
            for p in projects.all():
                parts = [
                    f"{w.name} ({w.path}"
                    + (f", branch {w.branch}" if w.branch else "")
                    + ")"
                    + (
                        f": sessões {', '.join(names)}"
                        if (names := by_workspace.get((p.name, w.name)))
                        else ""
                    )
                    for w in p.workspaces
                ]
                lines.append(f"{p.name}: " + ("; ".join(parts) or "sem workspaces"))
            return "\n".join(lines) or "Nenhum projeto cadastrado."

        return await _speak(run)

    @sdk.tool(
        "criar_workspace",
        "Cadastra uma pasta existente como workspace de um projeto (ex: back e front).",
        {"projeto": str, "nome": str, "pasta": str},
    )
    async def criar_workspace(args: Result) -> Result:
        async def run() -> str:
            found = projects.find(str(args["projeto"]))
            ws = projects.add_workspace(found.id, str(args["nome"]), str(args["pasta"]))
            return f"Workspace {ws.name} cadastrado no projeto {found.name}."

        return await _speak(run)

    @sdk.tool(
        "criar_worktree",
        "Cria um git worktree a partir de um workspace do projeto, numa branch com o nome dado, "
        "e cadastra como workspace novo.",
        {"projeto": str, "workspace_pai": str, "nome": str},
    )
    async def criar_worktree(args: Result) -> Result:
        async def run() -> str:
            found = projects.find(str(args["projeto"]))
            parent = workspace_id(found.name, str(args["workspace_pai"]))
            ws = await projects.add_worktree(found.id, parent, str(args["nome"]))
            return f"Worktree {ws.name} criado no projeto {found.name}, branch {ws.branch}."

        return await _speak(run)

    @sdk.tool(
        "apagar_workspace",
        "Tira um workspace do projeto. Pasta comum continua no disco; worktree é removido com "
        "git. Confirme com o usuário antes, e de novo antes de usar 'forcar' (perde mudanças "
        "não commitadas).",
        {
            "type": "object",
            "properties": {
                "projeto": {"type": "string"},
                "nome": {"type": "string"},
                "forcar": {"type": "boolean"},
            },
            "required": ["projeto", "nome"],
        },
    )
    async def apagar_workspace(args: Result) -> Result:
        async def run() -> str:
            ws = workspace_id(str(args["projeto"]), str(args["nome"]))
            await projects.delete_workspace(ws, force=bool(args.get("forcar")))
            return f"Workspace {args['nome']} apagado."

        return await _speak(run)

    delegates = [kind.delegate_tool(delegate) for kind in KINDS.values()]
    return [
        *delegates,
        criar_sessao,
        limpar_sessao,
        apagar_sessao,
        listar_sessoes,
        criar_projeto,
        listar_projetos,
        criar_workspace,
        criar_worktree,
        apagar_workspace,
    ]


async def _speak(run: Callable[[], Awaitable[str]]) -> Result:
    try:
        text = await run()
    except (SessionError, ProjectError, GitError) as e:
        text = str(e)
    return {"content": [{"type": "text", "text": text}]}
