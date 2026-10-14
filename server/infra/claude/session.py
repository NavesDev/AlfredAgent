"""Named Claude Code session that runs the tasks Alfred delegates to it.

Its kind (infra/claude/agents.py) builds the options from a context read fresh on every connect,
so model, effort and resume changes apply to the next connection (ADR 0006, 0007, 0008).
"""

import logging
from collections.abc import Awaitable, Callable
from dataclasses import replace
from typing import Any

import claude_agent_sdk as sdk

from errors import AgentError
from events import EventBus
from infra.claude.agents import AgentKind, SessionContext
from infra.claude.alfred import (
    Client,
    Reply,
    connect_sdk,
    failure,
    publish_progress,
    publish_rate_limit,
    read_context,
)
from infra.claude.summary import extract_summary

log = logging.getLogger(__name__)


class CodingSession:
    def __init__(
        self,
        bus: EventBus,
        kind: AgentKind,
        context: Callable[[], SessionContext],
        connect: Callable[[sdk.ClaudeAgentOptions], Awaitable[Client]] = connect_sdk,
    ) -> None:
        self.kind, self._context = kind, context
        self.name = context().name
        self._bus = bus
        self._connect = connect
        self._client: Client | None = None

    @property
    def connected(self) -> bool:
        return self._client is not None

    async def run(self, task: str) -> Reply:
        """No time limit: a task runs until it ends or someone clears or deletes the session."""
        try:
            if self._client is None:
                self._client = await self._open()
            return await self._run(self._client, task)
        except (sdk.ClaudeSDKError, AgentError) as e:
            await self.disconnect()  # next task reconnects fresh
            if isinstance(e, AgentError):
                raise
            raise AgentError(str(e)) from e

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
        while True:
            result, prompts = await self._turn(client, task)
            if not prompts or _ours(prompts, task):
                break
            # a background job's notification, or a turn left unread, ended before ours
            log.info("session %s skipped a turn it did not ask for: %s", self.name, prompts)
        if result is None:
            raise AgentError("stream ended without a result")
        if result.is_error or result.result is None:
            raise AgentError(failure(result))
        usage = result.usage or {}
        tokens = int(usage.get("input_tokens", 0)) + int(usage.get("output_tokens", 0))
        context = await read_context(client)
        reply = Reply(
            result.result, extract_summary(result.result), tokens, result.session_id, context
        )
        self._bus.publish("alfred_reply", session=self.name, text=reply.text, summary=reply.summary)
        return reply

    async def _turn(self, client: Client, task: str) -> tuple[sdk.ResultMessage | None, list[str]]:
        """Reads one turn; returns its result and the prompts the CLI echoed starting it."""
        result, prompts = None, []
        async for message in client.receive_response():
            if (prompt := _prompt(message)) is not None:
                prompts.append(prompt)
            if prompts and not _ours(prompts, task):
                continue  # not our turn: its steps belong to no task on the panel
            if isinstance(message, sdk.AssistantMessage):
                publish_progress(self._bus, self.name, message)
            elif isinstance(message, sdk.ResultMessage):
                result = message
            elif isinstance(message, sdk.SystemMessage):
                self._publish_system(message)
            elif isinstance(message, sdk.RateLimitEvent):
                publish_rate_limit(self._bus, message)
        return result, prompts

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


def _prompt(message: Any) -> str | None:
    """The text of a prompt the CLI echoed (a task or a notification); None for anything else."""
    if not isinstance(message, sdk.UserMessage) or message.parent_tool_use_id:
        return None
    if isinstance(message.content, str):
        return message.content.strip()
    if any(isinstance(b, sdk.ToolResultBlock) for b in message.content):
        return None
    return "".join(b.text for b in message.content if isinstance(b, sdk.TextBlock)).strip()


def _ours(prompts: list[str], task: str) -> bool:
    return any(task.strip() in prompt for prompt in prompts)


def _without_resume(ctx: SessionContext) -> SessionContext:
    return replace(ctx, resume=None)
