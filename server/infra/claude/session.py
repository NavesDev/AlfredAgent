"""Named Claude Code session that runs the tasks Alfred delegates to it.

Its kind (infra/claude/agents.py) builds the options from a context read fresh on every connect,
so model, effort and resume changes apply to the next connection (ADR 0006, 0007, 0008).
"""

import asyncio
from collections.abc import Awaitable, Callable
from dataclasses import replace
from typing import Any

import claude_agent_sdk as sdk

from errors import AgentError
from events import EventBus
from infra.claude.agents import AgentKind, SessionContext
from infra.claude.alfred import Client, Reply, connect_sdk, publish_progress
from infra.claude.summary import extract_summary


class CodingSession:
    def __init__(
        self,
        bus: EventBus,
        kind: AgentKind,
        context: Callable[[], SessionContext],
        timeout_s: float,
        connect: Callable[[sdk.ClaudeAgentOptions], Awaitable[Client]] = connect_sdk,
    ) -> None:
        self.kind, self._context = kind, context
        self.name = context().name
        self._bus = bus
        self._timeout_s, self._connect = timeout_s, connect
        self._client: Client | None = None

    @property
    def connected(self) -> bool:
        return self._client is not None

    async def run(self, task: str) -> Reply:
        try:
            async with asyncio.timeout(self._timeout_s):
                if self._client is None:
                    self._client = await self._open()
                return await self._run(self._client, task)
        except (TimeoutError, sdk.ClaudeSDKError, AgentError) as e:
            await self.disconnect()  # next task reconnects fresh
            if isinstance(e, AgentError):
                raise
            reason = f"timeout after {self._timeout_s}s" if isinstance(e, TimeoutError) else e
            raise AgentError(str(reason)) from e

    async def disconnect(self) -> None:
        """Ends the CLI process; the next task resumes the conversation if the context says so."""
        client, self._client = self._client, None
        if client is not None:
            await client.disconnect()

    async def _open(self) -> Client:
        ctx = self._context()
        if not ctx.cwd.is_dir():
            raise AgentError(f"a pasta {ctx.cwd} da sessão {self.name} não existe mais")
        try:
            return await self._connect(self.kind.options(ctx))
        except sdk.ClaudeSDKError:
            if ctx.resume is None:
                raise
        self._bus.publish(
            "error",
            where=self.name,
            message=f"a sessão {self.name} perdeu o histórico e começou do zero",
        )
        return await self._connect(self.kind.options(_without_resume(ctx)))

    async def _run(self, client: Client, task: str) -> Reply:
        await client.query(task)
        result = None
        async for message in client.receive_response():
            if isinstance(message, sdk.AssistantMessage):
                publish_progress(self._bus, self.name, message)
            elif isinstance(message, sdk.ResultMessage):
                result = message
            elif isinstance(message, sdk.SystemMessage):
                self._publish_system(message)
        if result is None:
            raise AgentError("stream ended without a result")
        if result.is_error or result.result is None:
            raise AgentError(f"session returned error: {result.errors or result.subtype}")
        usage = result.usage or {}
        tokens = int(usage.get("input_tokens", 0)) + int(usage.get("output_tokens", 0))
        reply = Reply(result.result, extract_summary(result.result), tokens, result.session_id)
        self._bus.publish("alfred_reply", session=self.name, text=reply.text, summary=reply.summary)
        return reply

    def _publish_system(self, message: sdk.SystemMessage) -> None:
        name = self.name
        if isinstance(message, sdk.TaskStartedMessage):
            self._bus.publish(
                "subagent_started",
                session=name,
                id=message.task_id,
                subagent_type=message.task_type,
                description=message.description,
            )
        elif isinstance(message, sdk.TaskProgressMessage):
            self._bus.publish(
                "subagent_progress",
                session=name,
                id=message.task_id,
                last_tool=message.last_tool_name,
            )
        elif isinstance(message, sdk.TaskNotificationMessage):
            self._bus.publish(
                "subagent_finished", session=name, id=message.task_id, status=message.status
            )
        elif message.subtype == "init":
            servers: list[Any] = message.data.get("mcp_servers") or []
            names = [str(s["name"]) for s in servers if isinstance(s, dict) and "name" in s]
            self._bus.publish("mcp_servers_seen", session=name, names=names)


def _without_resume(ctx: SessionContext) -> SessionContext:
    return replace(ctx, resume=None)
