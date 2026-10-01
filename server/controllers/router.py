"""Entry point for every command. Phase 1: everything goes to the main agent."""

from typing import Protocol

from errors import AgentError
from events import EventBus
from infra.claude.alfred import Reply

FAILURE_MESSAGE = "Não consegui falar com o Claude agora."


class Agent(Protocol):
    async def ask(self, text: str) -> Reply: ...


class Speaker(Protocol):
    def say(self, text: str) -> None: ...


class Router:
    def __init__(self, bus: EventBus, agent: Agent, talker: Speaker) -> None:
        self._bus, self._agent, self._talker = bus, agent, talker

    async def handle(self, text: str) -> None:
        self._bus.publish("voice_state", state="thinking")
        try:
            summary = (await self._agent.ask(text)).summary
        except AgentError as e:
            self._bus.publish("error", where="alfred", message=str(e))
            summary = FAILURE_MESSAGE
        if summary:
            self._talker.say(summary)
        else:
            self._bus.publish("voice_state", state="idle")
