"""Kinds of agent Alfred can delegate to (ADR 0007).

Each kind decides the Claude Code tools and prompt of its sessions and builds the tool Alfred
uses to delegate to it. Adding a kind is a subclass plus an entry in KINDS.
"""

from abc import ABC, abstractmethod
from collections.abc import Callable
from pathlib import Path
from typing import Any, ClassVar

import claude_agent_sdk as sdk

# (session name, task) -> what Alfred says
Delegate = Callable[[str, str], str]

DEFAULT_SESSION = "sistema"

SUMMARY_RULE = """Comece SEMPRE a resposta final com uma linha no formato:
RESUMO: <até 2 frases em português do Brasil, sem código, sem caminhos longos, sem markdown>
Essa linha é falada para o usuário. Depois dela, detalhes só se forem úteis."""


class AgentKind(ABC):
    kind: ClassVar[str]  # registry key and delegate tool suffix
    label: ClassVar[str]  # shown on the panel and spoken
    tools: ClassVar[list[str]]  # Claude Code tools of the session

    @abstractmethod
    def prompt(self, name: str, cwd: Path) -> str: ...

    @abstractmethod
    def delegate_tool(self, delegate: Delegate) -> sdk.SdkMcpTool[Any]: ...


class GeneralAgent(AgentKind):
    """Runs anything on the computer: commands, files, settings, apps."""

    kind, label = "geral", "Geral"
    tools: ClassVar[list[str]] = ["Bash", "Read", "Edit", "Write", "Glob", "Grep"]

    def prompt(self, name: str, cwd: Path) -> str:
        return f"""Você é a sessão "{name}" do Alfred, assistente por voz de um desenvolvedor.
Você roda no computador Linux dele (diretório inicial {cwd}) e executa a tarefa recebida
usando o terminal e os arquivos. Faça o mínimo necessário e não apague nada que a tarefa não
peça explicitamente.
{SUMMARY_RULE}"""

    def delegate_tool(self, delegate: Delegate) -> sdk.SdkMcpTool[Any]:
        @sdk.tool(
            f"delegar_{self.kind}",
            "Manda uma tarefa no computador do usuário (comandos, arquivos, projetos, "
            "configurações, apps) para uma sessão do tipo geral, que roda em segundo plano e "
            "fala o resultado quando terminar. Descreva a tarefa completa com suas palavras. "
            f"Sem 'sessao', vai para a sessão '{DEFAULT_SESSION}'.",
            {
                "type": "object",
                "properties": {"tarefa": {"type": "string"}, "sessao": {"type": "string"}},
                "required": ["tarefa"],
            },
        )
        async def handler(args: dict[str, Any]) -> dict[str, Any]:
            name = str(args.get("sessao") or DEFAULT_SESSION)
            return {"content": [{"type": "text", "text": delegate(name, str(args["tarefa"]))}]}

        return handler


KINDS: dict[str, AgentKind] = {k.kind: k for k in (GeneralAgent(),)}
