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
        return projects.workspace(project_name, name).id

    @sdk.tool(
        "criar_sessao",
        "Cria uma sessão nomeada que fica disponível para delegar tarefas. "
        f"Tipos: {', '.join(f'{k} ({v.label})' for k, v in KINDS.items())}. "
        "Implementação precisa de 'projeto' e 'ambiente'; geral aceita os dois opcionais "
        "(sem eles, roda na home). 'modelo' e 'effort' só quando o usuário pedir. "
        "'apelidos': jeitos de falar o nome que o reconhecimento de voz entende, úteis para "
        'nomes em inglês ("saite seils" para Site Sales).',
        {
            "type": "object",
            "properties": {
                "tipo": {"type": "string", "enum": list(KINDS)},
                "nome": {"type": "string"},
                "apelidos": {"type": "array", "items": {"type": "string"}},
                "projeto": {"type": "string"},
                "ambiente": {"type": "string"},
                "modelo": {"type": "string"},
                "effort": {"type": "string", "enum": EFFORTS},
            },
            "required": ["tipo", "nome"],
        },
    )
    async def criar_sessao(args: Result) -> Result:
        async def run() -> str:
            ws = None
            if args.get("projeto") or args.get("ambiente"):
                ws = workspace_id(str(args.get("projeto", "")), str(args.get("ambiente", "")))
            view = sessions.create(
                str(args["tipo"]),
                str(args["nome"]),
                ws,
                args.get("modelo"),
                args.get("effort"),
                aliases=[str(a) for a in args.get("apelidos", [])],
            )
            where = f"{view.project}, ambiente {view.workspace}" if view.project else view.cwd
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
        "Lista as sessões com tipo, projeto, ambiente, status, tarefa atual e, quando a "
        "última tarefa falhou, o motivo do erro.",
        {},
    )
    async def listar_sessoes(args: Result) -> Result:
        async def run() -> str:
            return "\n".join(
                f"{v.name} ({v.label}, "
                + (f"{v.project}/{v.workspace}" if v.project else v.cwd)
                + f"): {'esperando vaga' if v.waiting else v.status}"
                + (f", {'vai fazer' if v.waiting else 'fazendo'}: {v.task}" if v.task else "")
                + (f", {v.queue} na fila" if v.queue else "")
                + (f", último erro: {v.last_error}" if v.last_error else "")
                for v in sessions.list()
            )

        return await _speak(run)

    @sdk.tool(
        "criar_projeto",
        "Cadastra um projeto: um nome que agrupa ambientes (pastas) e sessões. "
        "'apelidos' ajudam a reconhecer o nome falado; 'descricao' diz em uma frase do que o "
        "projeto trata.",
        {
            "type": "object",
            "properties": {
                "nome": {"type": "string"},
                "apelidos": {"type": "array", "items": {"type": "string"}},
                "descricao": {"type": "string"},
            },
            "required": ["nome"],
        },
    )
    async def criar_projeto(args: Result) -> Result:
        async def run() -> str:
            created = projects.create(
                str(args["nome"]),
                [str(a) for a in args.get("apelidos", [])],
                str(args.get("descricao", "")),
            )
            return f"Projeto {created.name} criado."

        return await _speak(run)

    @sdk.tool(
        "listar_projetos",
        "Lista os projetos com descrição, ambientes (com descrição) e sessões. Use para saber do "
        "que cada projeto trata e escolher o ambiente certo.",
        {},
    )
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
                    + (f" — {w.description}" if w.description else "")
                    + (
                        f": sessões {', '.join(names)}"
                        if (names := by_workspace.get((p.name, w.name)))
                        else ""
                    )
                    for w in p.workspaces
                ]
                about = f" — {p.description}" if p.description else ""
                lines.append(f"{p.name}{about}: " + ("; ".join(parts) or "sem ambientes"))
            return "\n".join(lines) or "Nenhum projeto cadastrado."

        return await _speak(run)

    @sdk.tool(
        "criar_ambiente",
        "Cadastra uma pasta existente como ambiente de um projeto (ex: back e front), com uma "
        "'descricao' curta opcional.",
        {
            "type": "object",
            "properties": {
                "projeto": {"type": "string"},
                "nome": {"type": "string"},
                "pasta": {"type": "string"},
                "descricao": {"type": "string"},
            },
            "required": ["projeto", "nome", "pasta"],
        },
    )
    async def criar_ambiente(args: Result) -> Result:
        async def run() -> str:
            found = projects.find(str(args["projeto"]))
            ws = projects.add_workspace(
                found.id, str(args["nome"]), str(args["pasta"]), str(args.get("descricao", ""))
            )
            return f"Ambiente {ws.name} cadastrado no projeto {found.name}."

        return await _speak(run)

    @sdk.tool(
        "criar_worktree",
        "Cria um git worktree a partir de um ambiente do projeto, numa branch com o nome dado, "
        "e cadastra como ambiente novo, com uma 'descricao' curta opcional.",
        {
            "type": "object",
            "properties": {
                "projeto": {"type": "string"},
                "ambiente_pai": {"type": "string"},
                "nome": {"type": "string"},
                "descricao": {"type": "string"},
            },
            "required": ["projeto", "ambiente_pai", "nome"],
        },
    )
    async def criar_worktree(args: Result) -> Result:
        async def run() -> str:
            found = projects.find(str(args["projeto"]))
            parent = workspace_id(found.name, str(args["ambiente_pai"]))
            ws = await projects.add_worktree(
                found.id, parent, str(args["nome"]), str(args.get("descricao", ""))
            )
            return f"Worktree {ws.name} criado no projeto {found.name}, branch {ws.branch}."

        return await _speak(run)

    @sdk.tool(
        "apagar_ambiente",
        "Tira um ambiente do projeto. Pasta comum continua no disco; worktree é removido com "
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
    async def apagar_ambiente(args: Result) -> Result:
        async def run() -> str:
            ws = workspace_id(str(args["projeto"]), str(args["nome"]))
            await projects.delete_workspace(ws, force=bool(args.get("forcar")))
            return f"Ambiente {args['nome']} apagado."

        return await _speak(run)

    @sdk.tool(
        "definir_apelidos",
        "Troca os apelidos de uma sessão ou projeto: jeitos de falar o nome que o "
        "reconhecimento de voz entende. Use quando um nome vive sendo mal entendido ou o "
        "usuário pedir. A lista substitui a anterior; vazia apaga todos.",
        {
            "type": "object",
            "properties": {
                "alvo": {"type": "string", "enum": ["sessao", "projeto"]},
                "nome": {"type": "string"},
                "apelidos": {"type": "array", "items": {"type": "string"}},
            },
            "required": ["alvo", "nome", "apelidos"],
        },
    )
    async def definir_apelidos(args: Result) -> Result:
        async def run() -> str:
            aliases = [str(a) for a in args["apelidos"]]
            if args["alvo"] == "projeto":
                found = projects.find(str(args["nome"]))
                updated = projects.update(found.id, aliases=aliases)
                what, name, saved = "do projeto", updated.name, updated.aliases
            else:
                view = sessions.set_aliases(str(args["nome"]), aliases)
                what, name, saved = "da sessão", view.name, view.aliases
            return f"Apelidos {what} {name}: {', '.join(saved) or 'nenhum'}."

        return await _speak(run)

    @sdk.tool(
        "definir_descricao",
        "Troca a descrição curta (até 200 caracteres) de um projeto ou, com 'ambiente', de um "
        "ambiente dele. Vazia apaga.",
        {
            "type": "object",
            "properties": {
                "projeto": {"type": "string"},
                "ambiente": {"type": "string"},
                "descricao": {"type": "string"},
            },
            "required": ["projeto", "descricao"],
        },
    )
    async def definir_descricao(args: Result) -> Result:
        async def run() -> str:
            text = str(args["descricao"])
            if name := str(args.get("ambiente") or "").strip():
                ws = projects.update_workspace(workspace_id(str(args["projeto"]), name), text)
                return f"Descrição do ambiente {ws.name}: {ws.description or 'nenhuma'}."
            updated = projects.update(projects.find(str(args["projeto"])).id, description=text)
            return f"Descrição do projeto {updated.name}: {updated.description or 'nenhuma'}."

        return await _speak(run)

    delegates = [kind.delegate_tool(delegate) for kind in KINDS.values()]

    @sdk.tool(
        "ver_ambiente",
        "Mostra o estado git de um ambiente: branch, quantos arquivos estão alterados e os "
        "últimos commits. Use para verificações, sem abrir sessão.",
        {
            "type": "object",
            "properties": {"projeto": {"type": "string"}, "ambiente": {"type": "string"}},
            "required": ["projeto", "ambiente"],
        },
    )
    async def ver_ambiente(args: Result) -> Result:
        async def run() -> str:
            ws, git = await projects.summary(str(args["projeto"]), str(args["ambiente"]))
            changed = (
                "nada alterado"
                if git.changed == 0
                else f"{git.changed} arquivo{'s' if git.changed > 1 else ''} "
                f"alterado{'s' if git.changed > 1 else ''}"
            )
            commits = "; ".join(git.commits) or "sem commits"
            return f"{ws.name}: branch {git.branch}, {changed}. Últimos commits: {commits}."

        return await _speak(run)

    return [
        *delegates,
        criar_sessao,
        limpar_sessao,
        apagar_sessao,
        listar_sessoes,
        criar_projeto,
        listar_projetos,
        criar_ambiente,
        criar_worktree,
        apagar_ambiente,
        definir_apelidos,
        definir_descricao,
        ver_ambiente,
    ]


async def _speak(run: Callable[[], Awaitable[str]]) -> Result:
    try:
        text = await run()
    except (SessionError, ProjectError, GitError) as e:
        text = str(e)
    return {"content": [{"type": "text", "text": text}]}
