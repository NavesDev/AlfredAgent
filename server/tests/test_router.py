import asyncio
from collections.abc import Callable

from controllers.router import FAILURE_MESSAGE, Router
from errors import AgentError
from events import EventBus
from infra.claude.alfred import Reply
from tests.conftest import drain


class FakeAgent:
    def __init__(self, reply: Reply | Exception, activities: list[str] | None = None) -> None:
        self.reply, self.activities = reply, activities or []
        self.asked: list[str] = []

    async def ask(
        self, text: str, on_summary: Callable[[str], None], on_activity: Callable[[str], None]
    ) -> Reply:
        self.asked.append(text)
        for label in self.activities:
            on_activity(label)
        if isinstance(self.reply, Exception):
            raise self.reply
        if self.reply.summary:
            on_summary(self.reply.summary)
        return self.reply


class FakeTalker:
    def __init__(self, speaking: bool = False) -> None:
        self.said: list[str] = []
        self.resting: list[str] = []
        self.is_speaking = speaking

    def say(self, text: str) -> None:
        self.said.append(text)

    def set_resting(self, state: str) -> None:
        self.resting.append(state)


async def test_routes_text_to_alfred_and_speaks_summary(bus: EventBus) -> None:
    agent, talker = FakeAgent(Reply("longo", "curto")), FakeTalker()

    await Router(bus, agent, talker).handle("oi")

    assert agent.asked == ["oi"]
    assert talker.said == ["curto"]


async def test_publishes_thinking_while_agent_works(bus: EventBus) -> None:
    queue = bus.subscribe()

    await Router(bus, FakeAgent(Reply("x", "y")), FakeTalker()).handle("oi")
    await asyncio.sleep(0)

    first = drain(queue)[0]
    assert (first["type"], first["state"]) == ("voice_state", "thinking")


async def test_agent_error_is_published_and_spoken(bus: EventBus) -> None:
    queue, talker = bus.subscribe(), FakeTalker()

    await Router(bus, FakeAgent(AgentError("boom")), talker).handle("oi")
    await asyncio.sleep(0)

    errors = [e for e in drain(queue) if e["type"] == "error"]
    assert errors[0]["where"] == "alfred" and errors[0]["message"] == "boom"
    assert talker.said == [FAILURE_MESSAGE]


async def test_empty_summary_goes_back_to_idle_silently(bus: EventBus) -> None:
    queue, talker = bus.subscribe(), FakeTalker()

    await Router(bus, FakeAgent(Reply("", "")), talker).handle("oi")
    await asyncio.sleep(0)

    assert talker.said == []
    assert drain(queue)[-1]["state"] == "idle"


class Clock:
    def __init__(self, *times: float) -> None:
        self.times = list(times)

    def __call__(self) -> float:
        return self.times.pop(0)


async def test_narrates_activity_changes_at_most_every_three_seconds(bus: EventBus) -> None:
    talker = FakeTalker()
    agent = FakeAgent(
        Reply("x", ""),
        [
            "Analisando seus e-mails",
            "Analisando seus e-mails",
            "Lendo um e-mail",
            "Olhando a página",
        ],
    )

    await Router(bus, agent, talker, clock=Clock(0, 1, 2, 5)).handle("oi")

    assert talker.said == ["Analisando seus e-mails.", "Olhando a página."]


async def test_does_not_narrate_over_speech_or_the_delegation(bus: EventBus) -> None:
    talker = FakeTalker(speaking=True)
    await Router(bus, FakeAgent(Reply("x", ""), ["Pesquisando na web"]), talker).handle("oi")
    assert talker.said == []

    talker = FakeTalker()
    agent = FakeAgent(Reply("x", ""), ["Mandando para uma sessão"])
    await Router(bus, agent, talker).handle("oi")
    assert talker.said == []


async def test_talker_rests_in_thinking_during_the_turn_then_idle(bus: EventBus) -> None:
    talker = FakeTalker()

    await Router(bus, FakeAgent(Reply("x", "y")), talker).handle("oi")

    assert talker.resting == ["thinking", "idle"]


class FakeVocabulary:
    def canonicalize(self, text: str) -> str:
        return text.replace("saite seils", "Site Sales")

    def hint(self) -> str:
        return "[Nomes conhecidos: Site Sales]"


async def test_fixes_aliases_and_sends_the_known_names(bus: EventBus) -> None:
    agent = FakeAgent(Reply("x", "y"))

    await Router(bus, agent, FakeTalker(), vocabulary=FakeVocabulary()).handle(
        "manda pro saite seils"
    )

    assert agent.asked == ["[Nomes conhecidos: Site Sales]\nmanda pro Site Sales"]
