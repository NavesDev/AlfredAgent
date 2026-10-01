"""Main agent: answers through the logged-in Claude Code CLI, one conversation per day."""

import asyncio
import shutil
from collections.abc import Callable
from dataclasses import dataclass
from datetime import date
from typing import Any

import claude_agent_sdk as sdk

from errors import AgentError, DependencyError
from events import EventBus
from infra.claude.state import DailyState
from infra.claude.summary import extract_summary

SYSTEM_PROMPT = """Você é o Alfred, assistente pessoal por voz de um desenvolvedor.
Responda em português do Brasil, curto e direto, num texto que soe natural falado.
Sempre termine com uma linha no formato:
RESUMO: <até 2 frases, sem código, sem caminhos de arquivo, sem markdown>"""


@dataclass(frozen=True)
class Reply:
    text: str
    summary: str


def check_cli() -> None:
    if shutil.which("claude") is None:
        raise DependencyError("claude CLI not found in PATH; install and log in to Claude Code")


class AlfredAgent:
    def __init__(
        self,
        bus: EventBus,
        state: DailyState,
        model: str,
        timeout_s: float,
        query: Callable[..., Any] = sdk.query,
        today: Callable[[], date] = date.today,
    ) -> None:
        self._bus, self._state, self._model = bus, state, model
        self._timeout_s, self._query, self._today = timeout_s, query, today

    async def ask(self, text: str) -> Reply:
        resume = self._state.session_for(self._today())
        try:
            async with asyncio.timeout(self._timeout_s):
                try:
                    return await self._run(text, resume)
                except sdk.ClaudeSDKError:
                    if resume is None:
                        raise
                    return await self._run(text, None)
        except TimeoutError as e:
            raise AgentError(f"timeout after {self._timeout_s}s") from e
        except sdk.ClaudeSDKError as e:
            raise AgentError(str(e)) from e

    async def _run(self, text: str, resume: str | None) -> Reply:
        options = sdk.ClaudeAgentOptions(
            model=self._model, system_prompt=SYSTEM_PROMPT, tools=[], resume=resume
        )
        async for message in self._query(prompt=text, options=options):
            if isinstance(message, sdk.AssistantMessage):
                self._publish_progress(message)
            elif isinstance(message, sdk.ResultMessage):
                return self._finish(message)
        raise AgentError("stream ended without a result")

    def _publish_progress(self, message: sdk.AssistantMessage) -> None:
        for block in message.content:
            if isinstance(block, sdk.TextBlock):
                self._bus.publish("agent_progress", session="alfred", kind="text", content=block.text)
            elif isinstance(block, sdk.ToolUseBlock):
                self._bus.publish("agent_progress", session="alfred", kind="tool", content=block.name)

    def _finish(self, message: sdk.ResultMessage) -> Reply:
        if message.is_error or message.result is None:
            raise AgentError(f"agent returned error: {message.errors or message.subtype}")
        self._state.save(message.session_id, self._today())
        reply = Reply(message.result, extract_summary(message.result))
        self._bus.publish("alfred_reply", session="alfred", text=reply.text, summary=reply.summary)
        return reply
