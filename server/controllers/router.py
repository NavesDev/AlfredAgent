"""Entry point for every command. Phase 1: everything goes to the main agent."""

from collections.abc import Callable
from typing import Protocol

from errors import AgentError
from events import EventBus
from infra.claude.alfred import Reply

FAILURE_MESSAGE = "Não consegui falar com o Claude agora."


class Agent(Protocol):
    async def ask(self, text: str, on_summary: Callable[[str], None]) -> Reply: ...


class Speaker(Protocol):
    def say(self, text: str) -> None: ...


class Router:
    def __init__(self, bus: EventBus, agent: Agent, talker: Speaker) -> None:
        self._bus, self._agent, self._talker = bus, agent, talker

    async def handle(self, text: str) -> None:
        self._bus.publish("voice_state", state="thinking")
        try:
            reply = await self._agent.ask(text, self._talker.say)  # speaks as soon as it streams
        except AgentError as e:
            self._bus.publish("error", where="alfred", message=str(e))
            self._talker.say(FAILURE_MESSAGE)
            return
        if not reply.summary:
            self._bus.publish("voice_state", state="idle")
