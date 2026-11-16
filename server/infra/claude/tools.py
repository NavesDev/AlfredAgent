"""In-process MCP tools for the main agent. Logic lives in controllers; these only adapt.

One delegate tool per agent kind, generic tools for the session lifecycle (ADR 0007), and tools
for projects and workspaces. Errors come back as the sentence Alfred says.
"""

from collections.abc import Awaitable, Callable
from pathlib import Path
from typing import TYPE_CHECKING, Any

import claude_agent_sdk as sdk

from errors import GitError, GitHubError, ProjectError, ResultError, SessionError
from infra import github as real_github
from infra.claude.agents import KINDS
from models.project import MAX_DESCRIPTION
from models.result import PresentMode

if TYPE_CHECKING:
    from controllers.projects import Projects
    from controllers.results import Results
    from controllers.sessions import Sessions

SERVER = "alfred"  # MCP server name the main agent sees these tools under
EFFORTS = ["low", "medium", "high", "xhigh", "max"]

Result = dict[str, Any]


def session_tools(
    sessions: "Sessions",
    projects: "Projects",
    github: Any = real_github,
    results: "Results | None" = None,
) -> list[sdk.SdkMcpTool[Any]]:
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
        "nomes em inglês (\"saite seils\" para Site Sales). 'descricao': até 200 caracteres "
        "dizendo para que a sessão serve (contexto seu para delegar).",
        {
            "type": "object",
            "properties": {
                "tipo": {"type": "string", "enum": list(KINDS)},
                "nome": {"type": "string"},
                "apelidos": {"type": "array", "items": {"type": "string"}},
                "descricao": {"type": "string"},
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
            if len(" ".join(str(args.get("descricao") or "").split())) > MAX_DESCRIPTION:
                raise SessionError(f"A descrição passa de {MAX_DESCRIPTION} caracteres; encurte.")
            view = sessions.create(
                str(args["tipo"]),
                str(args["nome"]),
                ws,
                args.get("modelo"),
                args.get("effort"),
                aliases=[str(a) for a in args.get("apelidos", [])],
            )
            if args.get("descricao"):
                view = sessions.set_description(view.name, str(args["descricao"]))
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
                + ")"
                + (f" — {v.description}" if v.description else "")
                + f": {'esperando vaga' if v.waiting else v.status}"
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
        "projeto trata (contexto seu para delegar).",
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
                    + (", padrão" if w.id == p.default_workspace_id else "")
                    + (
                        ", features em worktree"
                        if projects.mode_of(w) == "worktree"
                        else ", features no próprio ambiente"
                    )
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
        "'descricao' curta opcional: o básico do que é, contexto seu para delegar.",
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
        "Troca a descrição curta (até 200 caracteres) de um projeto, de um ambiente dele (com "
        "'ambiente') ou de uma sessão (só 'sessao'). A descrição é contexto seu: o básico do que "
        "é e para que serve, para decidir onde delegar. Vazia apaga.",
        {
            "type": "object",
            "properties": {
                "projeto": {"type": "string"},
                "ambiente": {"type": "string"},
                "sessao": {"type": "string"},
                "descricao": {"type": "string"},
            },
            "required": ["descricao"],
        },
    )
    async def definir_descricao(args: Result) -> Result:
        async def run() -> str:
            text = str(args["descricao"])
            if session := str(args.get("sessao") or "").strip():
                view = sessions.set_description(session, text)
                return f"Descrição da sessão {view.name}: {view.description or 'nenhuma'}."
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
            branches = ", ".join(git.branches) or "nenhuma"
            return (
                f"{ws.name}: branch {git.branch}, {changed}. Últimos commits: {commits}. "
                f"Branches recentes: {branches}."
            )

        return await _speak(run)

    def repo_of(args: Result) -> Path:
        found = projects.find(str(args["projeto"]))
        if args.get("ambiente"):
            return Path(projects.workspace(found.name, str(args["ambiente"])).path)
        base = next((w for w in found.workspaces if w.id == found.default_workspace_id), None)
        if base is None:
            raise ProjectError(f"O projeto {found.name} não tem ambiente; diga em qual.")
        return Path(base.path)

    issue_args = {
        "projeto": {"type": "string"},
        "ambiente": {"type": "string", "description": "sem ele, o ambiente padrão"},
    }

    @sdk.tool(
        "ver_issue",
        "Lê uma issue do GitHub do repo do projeto: título, estado, labels, texto e os últimos "
        "comentários. Use antes de planejar uma feature ou para responder sobre ela.",
        {
            "type": "object",
            "properties": {**issue_args, "numero": {"type": "integer"}},
            "required": ["projeto", "numero"],
        },
    )
    async def ver_issue(args: Result) -> Result:
        async def run() -> str:
            i = await github.issue(repo_of(args), int(args["numero"]))
            labels = f" [{', '.join(i.labels)}]" if i.labels else ""
            comments = "\n".join(i.comments or []) or "sem comentários"
            return (
                f"#{i.number} {i.title} ({i.state}){labels} {i.url}\n{i.body}\n"
                f"Comentários:\n{comments}"
            )

        return await _speak(run)

    @sdk.tool(
        "listar_issues",
        "Lista até 20 issues do GitHub do repo do projeto, com 'busca' opcional (sintaxe de "
        "busca do GitHub) e 'estado' open, closed ou all.",
        {
            "type": "object",
            "properties": {
                **issue_args,
                "busca": {"type": "string"},
                "estado": {"type": "string", "enum": ["open", "closed", "all"]},
            },
            "required": ["projeto"],
        },
    )
    async def listar_issues(args: Result) -> Result:
        async def run() -> str:
            found = await github.issues(
                repo_of(args),
                str(args.get("busca") or "") or None,
                str(args.get("estado") or "open"),
            )
            return (
                "\n".join(
                    f"#{i.number} {i.title}" + (f" [{', '.join(i.labels)}]" if i.labels else "")
                    for i in found
                )
                or "Nenhuma issue encontrada."
            )

        return await _speak(run)

    @sdk.tool(
        "iniciar_feature",
        "Começa uma feature num projeto e manda a 'tarefa'. Antes, decida: veja as branches "
        "recentes (ver_ambiente) para seguir o padrão de nomes e leia a issue citada "
        "(ver_issue). 'worktree': true cria worktree e sessão novos a partir do ambiente "
        "('ambiente', ou o padrão do projeto); false usa a sessão do próprio ambiente; sem ele, "
        "segue o modo do ambiente (listar_projetos). 'branch' no padrão do repo (sem ela, "
        "feat/<feature>). Não precisa perguntar ao usuário.",
        {
            "type": "object",
            "properties": {
                "projeto": {"type": "string"},
                "feature": {"type": "string"},
                "tarefa": {"type": "string"},
                "branch": {"type": "string"},
                "worktree": {"type": "boolean"},
                "ambiente": {"type": "string"},
            },
            "required": ["projeto", "feature", "tarefa"],
        },
    )
    async def iniciar_feature(args: Result) -> Result:
        async def run() -> str:
            found = projects.find(str(args["projeto"]))
            worktree = args.get("worktree")
            ws = await projects.start_feature(
                found.name,
                str(args["feature"]),
                str(args.get("ambiente") or "") or None,
                str(args["branch"]) if args.get("branch") else None,
                worktree if isinstance(worktree, bool) else None,
            )
            views = sessions.list()
            view = next(
                (
                    v
                    for v in views
                    if v.kind == "implementacao"
                    and v.project == found.name
                    and v.workspace == ws.name
                ),
                None,
            )
            made = ""
            if view is None:
                taken = {v.name.lower() for v in views}
                name = ws.name if ws.name.lower() not in taken else f"{found.name}-{ws.name}"
                view = sessions.create("implementacao", name, ws.id)
                made = f" e a sessão {view.name}"
            sent = delegate(view.name, str(args["tarefa"]))
            if ws.kind == "worktree" and ws.branch:
                return f"Worktree {ws.name} na branch {ws.branch}{made}. {sent}"
            return f"Ambiente {ws.name}, sessão {view.name}{made and ' (nova)'}. {sent}"

        return await _speak(run)

    @sdk.tool(
        "definir_ambiente_padrao",
        "Define o ambiente padrão de um projeto: o principal, base dos worktrees de feature.",
        {
            "type": "object",
            "properties": {"projeto": {"type": "string"}, "ambiente": {"type": "string"}},
            "required": ["projeto", "ambiente"],
        },
    )
    async def definir_ambiente_padrao(args: Result) -> Result:
        async def run() -> str:
            ws = projects.workspace(str(args["projeto"]), str(args["ambiente"]))
            updated = projects.update(ws.project_id, default_workspace_id=ws.id)
            return f"Ambiente padrão do {updated.name}: {ws.name}."

        return await _speak(run)

    @sdk.tool(
        "apresentar",
        "Abre na tela, grande e no centro, o que o usuário pediu para ver: com 'sessao', o último "
        "resultado dela (imagem, vídeo, documento ou relatório de mudanças); com 'caminhos', um "
        "ou mais arquivos da home que você achou (vários viram um resultado só, com setas para "
        "passar de um a outro). Use só quando o usuário pedir para mostrar, apresentar ou ver; "
        "o cartão no canto aparece sozinho quando uma sessão termina. Não fale o que está na "
        "tela, só que mostrou.",
        {
            "type": "object",
            "properties": {
                "sessao": {"type": "string"},
                "caminhos": {"type": "array", "items": {"type": "string"}},
                "caminho": {"type": "string"},
            },
        },
    )
    async def apresentar(args: Result) -> Result:
        async def run() -> str:
            if results is None:
                return "Não consigo mostrar resultados agora."
            # Asked for by the user: always the expanded view; the card is for a session that
            # finished on its own (APRESENTAR line).
            mode: PresentMode = "ampliado"
            paths = [str(p) for p in args.get("caminhos") or []]
            if args.get("caminho"):
                paths.insert(0, str(args["caminho"]))
            if paths:
                results.present_paths(paths, mode)
            elif args.get("sessao"):
                results.present_last(str(args["sessao"]), mode)
            else:
                return "Diga de qual sessão ou qual arquivo quer ver."
            return "Mostrei na tela."

        return await _speak(run)

    @sdk.tool(
        "fechar_apresentacao",
        "Fecha o que está na tela (cartão ou janela ampliada), quando o usuário pedir "
        '("pode fechar", "tira da tela").',
        {},
    )
    async def fechar_apresentacao(args: Result) -> Result:
        async def run() -> str:
            if results is None:
                return "Não consigo mostrar resultados agora."
            results.close()
            return "Fechei."

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
        iniciar_feature,
        definir_ambiente_padrao,
        ver_issue,
        listar_issues,
        apresentar,
        fechar_apresentacao,
    ]


async def _speak(run: Callable[[], Awaitable[str]]) -> Result:
    try:
        text = await run()
    except (SessionError, ProjectError, GitError, GitHubError, ResultError) as e:
        text = str(e)
    return {"content": [{"type": "text", "text": text}]}
