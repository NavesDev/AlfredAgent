"""In-process MCP tools for the main agent. Logic lives in controllers; these only adapt.

One delegate tool per agent kind, plus generic tools for the session lifecycle (ADR 0007).
Session errors come back as the sentence Alfred says.
"""

from collections.abc import Awaitable, Callable
from typing import TYPE_CHECKING, Any

import claude_agent_sdk as sdk

from errors import SessionError
from infra.claude.agents import KINDS

if TYPE_CHECKING:
    from controllers.sessions import Sessions

SERVER = "alfred"

Result = dict[str, Any]


def alfred_tools(sessions: "Sessions") -> sdk.McpSdkServerConfig:
    return sdk.create_sdk_mcp_server(SERVER, tools=session_tools(sessions))


def session_tools(sessions: "Sessions") -> list[sdk.SdkMcpTool[Any]]:
    def delegate(name: str, task: str) -> str:
        try:
            return sessions.delegate(name, task)
        except SessionError as e:
            return str(e)

    @sdk.tool(
        "criar_sessao",
        "Cria uma sessão nomeada que fica disponível para delegar tarefas. "
        f"Tipos: {', '.join(f'{k} ({v.label})' for k, v in KINDS.items())}. "
        "'pasta' é opcional (padrão: a home do usuário).",
        {
            "type": "object",
            "properties": {
                "tipo": {"type": "string", "enum": list(KINDS)},
                "nome": {"type": "string"},
                "pasta": {"type": "string"},
            },
            "required": ["tipo", "nome"],
        },
    )
    async def criar_sessao(args: Result) -> Result:
        async def run() -> str:
            view = sessions.create(str(args["tipo"]), str(args["nome"]), args.get("pasta"))
            return f"Sessão {view.name} criada, tipo {view.label}, em {view.cwd}."

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

    @sdk.tool("listar_sessoes", "Lista as sessões com tipo, pasta, status e tarefa atual.", {})
    async def listar_sessoes(args: Result) -> Result:
        async def run() -> str:
            return "\n".join(
                f"{v.name} ({v.label}, {v.cwd}): {v.status}"
                + (f", fazendo: {v.task}" if v.task else "")
                + (f", {v.queue} na fila" if v.queue else "")
                for v in sessions.list()
            )

        return await _speak(run)

    delegates = [kind.delegate_tool(delegate) for kind in KINDS.values()]
    return [*delegates, criar_sessao, limpar_sessao, apagar_sessao, listar_sessoes]


async def _speak(run: Callable[[], Awaitable[str]]) -> Result:
    try:
        text = await run()
    except SessionError as e:
        text = str(e)
    return {"content": [{"type": "text", "text": text}]}
