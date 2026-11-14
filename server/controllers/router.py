"""Entry point for every command. Phase 1: everything goes to the main agent."""

import time
from collections.abc import Callable
from typing import Protocol

from errors import AgentError
from events import EventBus
from infra.claude.alfred import Reply

FAILURE_MESSAGE = "Não consegui falar com o Claude agora."
NARRATE_EVERY_S = 3.0
SILENT_ACTIVITIES = {"Mandando para uma sessão"}  # Alfred says it himself right after


class Agent(Protocol):
    async def ask(
        self,
        text: str,
        on_summary: Callable[[str], None],
        on_activity: Callable[[str], None],
    ) -> Reply: ...


class Speaker(Protocol):
    @property
    def is_speaking(self) -> bool: ...
    def say(self, text: str) -> None: ...
    def set_resting(self, state: str) -> None: ...


class Vocabulary(Protocol):
    def canonicalize(self, text: str) -> str: ...
    def hint(self) -> str: ...


class _NoVocabulary:
    def canonicalize(self, text: str) -> str:
        return text

    def hint(self) -> str:
        return ""


class Router:
    def __init__(
        self,
        bus: EventBus,
        agent: Agent,
        talker: Speaker,
        clock: Callable[[], float] = time.monotonic,
        vocabulary: Vocabulary | None = None,
    ) -> None:
        self._bus, self._agent, self._talker, self._clock = bus, agent, talker, clock
        self._vocabulary = vocabulary or _NoVocabulary()
        self._last_label: str | None = None
        self._last_at = float("-inf")

    async def handle(self, text: str) -> None:
        self._last_label, self._last_at = None, float("-inf")
        self._talker.set_resting("thinking")  # between spoken lines the orb keeps thinking
        self._bus.publish("voice_state", state="thinking")
        try:
            # Speaks the RESUMO as soon as it streams, and what it is doing meanwhile.
            await self._agent.ask(self._prompt(text), self._talker.say, self._narrate)
        except AgentError as e:
            self._bus.publish("error", where="alfred", message=str(e))
            self._talker.say(FAILURE_MESSAGE)
        finally:
            self._talker.set_resting("idle")
            if not self._talker.is_speaking:
                self._bus.publish("voice_state", state="idle")

    def _prompt(self, text: str) -> str:
        """Aliases become real names; the known names go first so Alfred can fix the rest."""
        text = self._vocabulary.canonicalize(text)
        hint = self._vocabulary.hint()
        return f"{hint}\n{text}" if hint else text

    def _narrate(self, label: str) -> None:
        """Say what Alfred is doing when it changes, without piling up speech."""
        now = self._clock()
        if (
            label == self._last_label
            or label in SILENT_ACTIVITIES
            or now - self._last_at < NARRATE_EVERY_S
            or self._talker.is_speaking
        ):
            return
        self._last_label, self._last_at = label, now
        self._talker.say(f"{label}.")
