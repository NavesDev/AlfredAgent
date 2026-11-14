import asyncio
from collections.abc import Iterator
from itertools import pairwise

import numpy as np

from errors import AudioError
from events import EventBus
from infra.audio.talker import PAUSE_S, Talker
from tests.conftest import drain

RATE = 24000


def make(
    bus: EventBus, fail: bool = False, acks: tuple[str, ...] = ()
) -> tuple[Talker, list[np.ndarray]]:
    played: list[np.ndarray] = []

    def synthesize(text: str) -> Iterator[np.ndarray]:
        if fail:
            raise AudioError("kokoro died")
        yield np.full(RATE, 0.5, dtype=np.float32)  # 1 s of audio

    talker = Talker(bus, synthesize, played.append, sample_rate=RATE, acknowledgements=acks)
    return talker, played


async def test_say_marks_speaking_until_played(bus: EventBus) -> None:
    talker, played = make(bus)

    talker.say("oi")
    assert talker.is_speaking

    talker.process_one()
    assert not talker.is_speaking
    assert sum(len(block) for block in played) == RATE


async def test_publishes_speaking_levels_then_idle(bus: EventBus) -> None:
    queue = bus.subscribe()
    talker, _ = make(bus)

    talker.say("oi")
    talker.process_one()
    await asyncio.sleep(0)

    events = drain(queue)
    assert (events[0]["type"], events[0]["state"]) == ("voice_state", "speaking")
    levels = [e for e in events if e["type"] == "audio_level"]
    assert len(levels) == 15 and levels[0]["source"] == "tts"
    assert (events[-1]["type"], events[-1]["state"]) == ("voice_state", "idle")


async def test_synthesis_failure_is_published_and_returns_to_idle(bus: EventBus) -> None:
    queue = bus.subscribe()
    talker, _ = make(bus, fail=True)

    talker.say("oi")
    talker.process_one()
    await asyncio.sleep(0)

    events = drain(queue)
    assert any(e["type"] == "error" and e["where"] == "talker" for e in events)
    assert events[-1]["state"] == "idle"
    assert not talker.is_speaking


async def test_chime_plays_short_tone_without_entering_speaking_state(bus: EventBus) -> None:
    queue = bus.subscribe()
    talker, played = make(bus)

    talker.chime("start")
    await asyncio.sleep(0)

    assert len(played) == 1 and 0 < len(played[0]) <= RATE // 5  # under 200 ms
    assert not talker.is_speaking and drain(queue) == []


async def test_start_and_end_chimes_differ(bus: EventBus) -> None:
    talker, played = make(bus)

    talker.chime("start")
    talker.chime("end")

    assert not np.array_equal(played[0], played[1])


async def test_acknowledge_plays_ready_clip_without_voice_states(bus: EventBus) -> None:
    queue = bus.subscribe()
    talker, played = make(bus, acks=("Certo.",))

    talker.acknowledge()
    assert talker.is_speaking  # keeps the wake word muted while it plays
    talker.process_one()
    await asyncio.sleep(0)

    assert len(played) == 1 and len(played[0]) == RATE
    assert not talker.is_speaking and drain(queue) == []


async def test_acknowledge_does_not_repeat_the_same_clip_twice_in_a_row(bus: EventBus) -> None:
    calls: list[str] = []

    def synthesize(text: str) -> Iterator[np.ndarray]:
        calls.append(text)
        yield np.full(10, len(calls), dtype=np.float32)

    played: list[np.ndarray] = []
    talker = Talker(bus, synthesize, played.append, acknowledgements=("a", "b"))
    for _ in range(6):
        talker.acknowledge()
        talker.process_one()

    assert calls == ["a", "b"]  # synthesized once, at startup
    assert all(x[0] != y[0] for x, y in pairwise(played))


async def test_acknowledge_without_clips_falls_back_to_end_chime(bus: EventBus) -> None:
    talker, played = make(bus)

    talker.acknowledge()

    assert len(played) == 1 and not talker.is_speaking


async def test_rests_in_the_given_state_after_speaking(bus: EventBus) -> None:
    queue = bus.subscribe()
    talker, _ = make(bus)

    talker.set_resting("thinking")
    talker.say("Analisando seus e-mails.")
    talker.process_one()
    await asyncio.sleep(0)

    states = [e["state"] for e in drain(queue) if e["type"] == "voice_state"]
    assert states == ["speaking", "thinking"]


async def test_notify_during_a_turn_waits_for_the_turn_to_end(bus: EventBus) -> None:
    talker, _ = make(bus)
    talker.set_resting("thinking")

    talker.notify("Recurve terminou: testes passaram.")
    assert not talker.is_speaking

    talker.set_resting("idle")
    assert talker.is_speaking


async def test_notify_outside_a_turn_speaks_right_away(bus: EventBus) -> None:
    talker, _ = make(bus)

    talker.notify("Recurve terminou.")

    assert talker.is_speaking


async def test_back_to_back_lines_get_a_short_pause_between_them(bus: EventBus) -> None:
    talker, played = make(bus)
    talker.say("primeira")
    talker.say("segunda")

    talker.process_one()

    gap = played[-1]
    assert not gap.any() and len(gap) == int(RATE * PAUSE_S)
