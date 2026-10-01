import asyncio
from collections.abc import Iterator

import numpy as np

from errors import AudioError
from events import EventBus
from infra.audio.talker import Talker
from tests.conftest import drain

RATE = 24000


def make(bus: EventBus, fail: bool = False) -> tuple[Talker, list[np.ndarray]]:
    played: list[np.ndarray] = []

    def synthesize(text: str) -> Iterator[np.ndarray]:
        if fail:
            raise AudioError("kokoro died")
        yield np.full(RATE, 0.5, dtype=np.float32)  # 1 s of audio

    return Talker(bus, synthesize, played.append, sample_rate=RATE), played


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
