"""Kinds of agent Alfred can delegate to (ADR 0007, 0008).

Each kind builds the Claude Code options of its sessions and the tool Alfred uses to delegate to
it. Adding a kind is a subclass plus an entry in KINDS.
"""

from abc import ABC, abstractmethod
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any, ClassVar

import claude_agent_sdk as sdk

# One CLI message can carry a screenshot, a big file or a long command output; the SDK's 1 MB
# default turns those into a failed task ("JSON message exceeded maximum buffer size").
MAX_BUFFER = 64 * 1024 * 1024

# (session name, task) -> what Alfred says
Delegate = Callable[[str, str], str]

DEFAULT_SESSION = "sistema"

SUMMARY_RULE = """Comece SEMPRE a resposta final com uma linha no formato:
RESUMO: <até 2 frases em português do Brasil, sem código, sem caminhos longos, sem markdown>
Essa linha é falada para o usuário. Depois dela, detalhes só se forem úteis."""


@dataclass(frozen=True)
class SessionContext:
    """Everything a kind needs to open a session; rebuilt on every connect."""

    name: str
    cwd: Path
    model: str
    effort: Any = None  # sdk EffortLevel
    resume: str | None = None
    project: str | None = None
    workspace: str | None = None
    mcp_disabled: tuple[str, ...] = ()


class AgentKind(ABC):
    kind: ClassVar[str]  # registry key and delegate tool suffix
    label: ClassVar[str]  # shown on the panel and spoken
    needs_workspace: ClassVar[bool] = False

    @abstractmethod
    def options(self, ctx: SessionContext) -> sdk.ClaudeAgentOptions: ...

    @abstractmethod
    def delegate_tool(self, delegate: Delegate) -> sdk.SdkMcpTool[Any]: ...


class GeneralAgent(AgentKind):
    """Runs anything on the computer: commands, files, settings, apps. Never sees mail or web."""

    kind, label = "geral", "Geral"
    tools: ClassVar[list[str]] = ["Bash", "Read", "Edit", "Write", "Glob", "Grep"]

    def options(self, ctx: SessionContext) -> sdk.ClaudeAgentOptions:
        return sdk.ClaudeAgentOptions(
            model=ctx.model,
            effort=ctx.effort,
            resume=ctx.resume,
            system_prompt=f"""Você é a sessão "{ctx.name}" do Alfred, assistente por voz de um
desenvolvedor. Você roda no computador Linux dele (diretório inicial {ctx.cwd}) e executa a
tarefa recebida usando o terminal e os arquivos. Faça o mínimo necessário e não apague nada que
a tarefa não peça explicitamente.
{SUMMARY_RULE}""",
            tools=self.tools,
            permission_mode="auto",
            strict_mcp_config=True,  # no mail, calendar, browser or other MCP servers
            setting_sources=[],  # no user hooks, plugins or permission rules
            cwd=ctx.cwd,
            max_buffer_size=MAX_BUFFER,
        )

    def delegate_tool(self, delegate: Delegate) -> sdk.SdkMcpTool[Any]:
        @sdk.tool(
            f"delegar_{self.kind}",
            "Manda uma tarefa no computador do usuário (comandos, arquivos, configurações, apps) "
            "para uma sessão do tipo geral, que roda em segundo plano e fala o resultado quando "
            "terminar. Descreva a tarefa completa com suas palavras. "
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


class ImplementationAgent(AgentKind):
    """Works on a project's code with the full Claude Code harness (ADR 0008)."""

    kind, label = "implementacao", "Implementação"
    needs_workspace = True

    def options(self, ctx: SessionContext) -> sdk.ClaudeAgentOptions:
        where = f'do projeto {ctx.project}, workspace "{ctx.workspace}"' if ctx.project else ""
        append = f"""Você é a sessão "{ctx.name}" do Alfred, assistente por voz de um
desenvolvedor, trabalhando {where} em {ctx.cwd}. As tarefas chegam por voz, resumidas pelo
Alfred: implemente, rode os testes do projeto e conte o que fez.
Use MCPs externos (e-mail, agenda, navegador) só quando a tarefa pedir isso explicitamente.
{SUMMARY_RULE}"""
        return sdk.ClaudeAgentOptions(
            model=ctx.model,
            effort=ctx.effort,
            resume=ctx.resume,
            system_prompt={"type": "preset", "preset": "claude_code", "append": append},
            setting_sources=["user", "project", "local"],  # CLAUDE.md, skills, plugins, hooks, MCPs
            skills="all",
            permission_mode="auto",
            disallowed_tools=[f"mcp__{name}" for name in ctx.mcp_disabled],
            cwd=ctx.cwd,
            max_buffer_size=MAX_BUFFER,
        )

    def delegate_tool(self, delegate: Delegate) -> sdk.SdkMcpTool[Any]:
        @sdk.tool(
            f"delegar_{self.kind}",
            "Manda uma tarefa de código (implementar, corrigir, testar, revisar) para uma sessão "
            "de implementação de um projeto. Ela roda em segundo plano e fala o resultado quando "
            "terminar. Descreva a tarefa completa com suas palavras.",
            {
                "type": "object",
                "properties": {"sessao": {"type": "string"}, "tarefa": {"type": "string"}},
                "required": ["sessao", "tarefa"],
            },
        )
        async def handler(args: dict[str, Any]) -> dict[str, Any]:
            text = delegate(str(args["sessao"]), str(args["tarefa"]))
            return {"content": [{"type": "text", "text": text}]}

        return handler


KINDS: dict[str, AgentKind] = {k.kind: k for k in (GeneralAgent(), ImplementationAgent())}
