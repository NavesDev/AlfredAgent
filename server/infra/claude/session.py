"""Named Claude Code session that runs tasks on the computer (Bash, files) for Alfred.

It never sees mail or web: no MCP servers, no WebSearch/WebFetch, no user settings. What it
does is decided by Claude Code's auto mode classifier (ADR 0006).
"""

import asyncio
from collections.abc import Awaitable, Callable
from pathlib import Path

import claude_agent_sdk as sdk

from errors import AgentError, DependencyError
from events import EventBus
from infra.claude.alfred import Client, Reply, connect_sdk, publish_progress
from infra.claude.summary import extract_summary

TOOLS = ["Bash", "Read", "Edit", "Write", "Glob", "Grep"]

SYSTEM_PROMPT = """Você é a sessão "{name}" do Alfred, assistente por voz de um desenvolvedor.
Você roda no computador Linux dele (diretório inicial {cwd}) e executa a tarefa recebida
usando o terminal e os arquivos. Faça o mínimo necessário e não apague nada que a tarefa não
peça explicitamente.
Comece SEMPRE a resposta final com uma linha no formato:
RESUMO: <até 2 frases em português do Brasil, sem código, sem caminhos longos, sem markdown>
Essa linha é falada para o usuário. Depois dela, detalhes só se forem úteis."""


class CodingSession:
    def __init__(
        self,
        bus: EventBus,
        name: str,
        cwd: Path,
        model: str,
        timeout_s: float,
        connect: Callable[[sdk.ClaudeAgentOptions], Awaitable[Client]] = connect_sdk,
    ) -> None:
        self.name = name
        self._bus, self._cwd, self._model = bus, cwd, model
        self._timeout_s, self._connect = timeout_s, connect
        self._client: Client | None = None

    async def start(self) -> None:
        try:
            self._client = await self._connect(self.options())
        except sdk.ClaudeSDKError as e:
            raise DependencyError(f"cannot start session {self.name!r}: {e}") from e

    async def run(self, task: str) -> Reply:
        try:
            async with asyncio.timeout(self._timeout_s):
                if self._client is None:
                    self._client = await self._connect(self.options())
                return await self._run(self._client, task)
        except (TimeoutError, sdk.ClaudeSDKError, AgentError) as e:
            await self._close()  # next task reconnects fresh
            if isinstance(e, AgentError):
                raise
            reason = f"timeout after {self._timeout_s}s" if isinstance(e, TimeoutError) else e
            raise AgentError(str(reason)) from e

    def options(self) -> sdk.ClaudeAgentOptions:
        return sdk.ClaudeAgentOptions(
            model=self._model,
            system_prompt=SYSTEM_PROMPT.format(name=self.name, cwd=self._cwd),
            tools=TOOLS,
            permission_mode="auto",
            strict_mcp_config=True,  # no mail, calendar, browser or other MCP servers
            setting_sources=[],  # no user hooks, plugins or permission rules
            cwd=self._cwd,
        )

    async def _run(self, client: Client, task: str) -> Reply:
        await client.query(task)
        result = None
        async for message in client.receive_response():
            if isinstance(message, sdk.AssistantMessage):
                publish_progress(self._bus, self.name, message)
            elif isinstance(message, sdk.ResultMessage):
                result = message
        if result is None:
            raise AgentError("stream ended without a result")
        if result.is_error or result.result is None:
            raise AgentError(f"session returned error: {result.errors or result.subtype}")
        reply = Reply(result.result, extract_summary(result.result))
        self._bus.publish("alfred_reply", session=self.name, text=reply.text, summary=reply.summary)
        return reply

    async def _close(self) -> None:
        client, self._client = self._client, None
        if client is not None:
            await client.disconnect()
