"""In-process MCP tools for the main agent. Logic lives in controllers; these only adapt."""

from collections.abc import Callable
from typing import Any

import claude_agent_sdk as sdk

SERVER = "alfred"


def alfred_tools(delegate: Callable[[str], str]) -> sdk.McpSdkServerConfig:
    return sdk.create_sdk_mcp_server(SERVER, tools=[delegar_tool(delegate)])


def delegar_tool(delegate: Callable[[str], str]) -> sdk.SdkMcpTool[Any]:
    @sdk.tool(
        "delegar",
        "Manda uma tarefa no computador do usuário (comandos, arquivos, projetos, "
        "configurações, apps) para a sessão 'sistema', que roda em segundo plano e fala o "
        "resultado quando terminar. Descreva a tarefa completa com suas palavras.",
        {"tarefa": str},
    )
    async def delegar(args: dict[str, Any]) -> dict[str, Any]:
        return {"content": [{"type": "text", "text": delegate(str(args["tarefa"]))}]}

    return delegar
