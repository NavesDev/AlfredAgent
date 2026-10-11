import asyncio
from collections.abc import Callable

import numpy as np
import pytest

from config import Listener as ListenerConfig
from errors import AudioError
from events import Event, EventBus
from infra.audio.listener import FRAME, Listener, load_vad
from tests.conftest import drain

WAKE, SPEECH, SILENCE = (np.full(FRAME, v, dtype=np.int16) for v in (2, 1, 0))
SILENCE_FRAMES = 15  # 1200 ms / 80 ms
chimes: list[str] = []


class FakeWake:
    def __init__(self) -> None:
        self.resets = 0

    def score(self, frame: np.ndarray) -> float:
        return 1.0 if frame[0] == 2 else 0.0

    def reset(self) -> None:
        self.resets += 1


def make(  # type: ignore[no-untyped-def]
    bus: EventBus,
    text: str | Exception = "oi alfred",
    muted: bool = False,
    acknowledge: Callable[[], None] | None = None,
):
    heard: list[str] = []
    chimes.clear()
    recorded: list[np.ndarray] = []

    def transcribe(audio: np.ndarray) -> str:
        recorded.append(audio)
        if isinstance(text, Exception):
            raise text
        return text

    listener = Listener(
        bus,
        ListenerConfig(),
        threshold=0.5,
        wake=FakeWake(),
        is_speech=lambda f: bool(f[0]),
        transcribe=transcribe,
        on_transcript=heard.append,
        muted=lambda: muted,
        chime=chimes.append,
        acknowledge=acknowledge,
    )
    return listener, heard, recorded


def feed(listener: Listener, *frames: np.ndarray) -> None:
    for frame in frames:
        listener.feed(frame)


async def events(queue: asyncio.Queue[Event], type: str) -> list[Event]:
    await asyncio.sleep(0)
    return [e for e in drain(queue) if e["type"] == type]


async def test_wake_word_then_speech_then_silence_hands_off_transcript(bus: EventBus) -> None:
    queue = bus.subscribe()
    listener, heard, recorded = make(bus)

    feed(listener, SILENCE, WAKE, SPEECH, SPEECH, *[SILENCE] * SILENCE_FRAMES)

    assert heard == ["oi alfred"]
    assert len(recorded[0]) == FRAME * (2 + SILENCE_FRAMES)
    states = [e["state"] for e in await events(queue, "voice_state")]
    assert states == ["listening", "transcribing"]


async def test_chimes_on_wake_word_and_when_recording_stops(bus: EventBus) -> None:
    listener, _, _ = make(bus)

    feed(listener, WAKE)
    assert chimes == ["start"]
    feed(listener, SPEECH, *[SILENCE] * SILENCE_FRAMES)
    assert chimes == ["start", "end"]


async def test_acknowledges_instead_of_end_chime_when_speech_was_heard(bus: EventBus) -> None:
    acks: list[str] = []
    listener, heard, _ = make(bus, acknowledge=lambda: acks.append("ack"))

    feed(listener, WAKE, SPEECH, *[SILENCE] * SILENCE_FRAMES)

    assert acks == ["ack"] and chimes == ["start"] and heard == ["oi alfred"]


async def test_only_chimes_when_recording_ends_without_speech(bus: EventBus) -> None:
    acks: list[str] = []
    listener, _, _ = make(bus, acknowledge=lambda: acks.append("ack"))

    feed(listener, WAKE, *[SILENCE] * 200)  # hits max duration

    assert acks == [] and chimes == ["start", "end"]


async def test_publishes_transcript_event(bus: EventBus) -> None:
    queue = bus.subscribe()
    listener, _, _ = make(bus)

    feed(listener, WAKE, SPEECH, *[SILENCE] * SILENCE_FRAMES)

    assert [e["text"] for e in await events(queue, "transcript")] == ["oi alfred"]


async def test_ignores_audio_without_wake_word(bus: EventBus) -> None:
    queue = bus.subscribe()
    listener, heard, _ = make(bus)

    feed(listener, SPEECH, SILENCE, SPEECH)

    assert heard == [] and await events(queue, "voice_state") == []


async def test_ignores_wake_word_while_muted(bus: EventBus) -> None:
    listener, heard, _ = make(bus, muted=True)

    feed(listener, WAKE, SPEECH, *[SILENCE] * SILENCE_FRAMES)

    assert heard == []


async def test_waits_for_speech_before_counting_silence(bus: EventBus) -> None:
    listener, heard, _ = make(bus)

    feed(listener, WAKE, *[SILENCE] * SILENCE_FRAMES)

    assert heard == []


async def test_stops_recording_at_max_duration(bus: EventBus) -> None:
    listener, heard, recorded = make(bus)

    feed(listener, WAKE, *[SPEECH] * 200)

    assert heard == ["oi alfred"]
    assert len(recorded[0]) == 16000 * 15


async def test_publishes_mic_level_while_listening(bus: EventBus) -> None:
    queue = bus.subscribe()
    listener, _, _ = make(bus)

    feed(listener, WAKE, SPEECH)

    levels = await events(queue, "audio_level")
    assert levels and levels[0]["source"] == "mic" and 0 < levels[0]["level"] <= 1


async def test_empty_transcript_returns_to_idle(bus: EventBus) -> None:
    queue = bus.subscribe()
    listener, heard, _ = make(bus, text="  ")

    feed(listener, WAKE, SPEECH, *[SILENCE] * SILENCE_FRAMES)

    assert heard == []
    assert (await events(queue, "voice_state"))[-1]["state"] == "idle"


@pytest.mark.parametrize("failure", [AudioError("mic died"), RuntimeError("bug")])
async def test_failure_is_published_and_listener_recovers(
    bus: EventBus, failure: Exception
) -> None:
    queue = bus.subscribe()
    listener, _, _ = make(bus, text=failure)

    feed(listener, WAKE, SPEECH, *[SILENCE] * SILENCE_FRAMES, WAKE)

    await asyncio.sleep(0)
    published = drain(queue)
    assert [e["type"] for e in published].count("error") == 1
    states = [e["state"] for e in published if e["type"] == "voice_state"]
    assert states == ["listening", "transcribing", "idle", "listening"]


def test_real_vad_returns_false_on_silence() -> None:
    assert load_vad()(np.zeros(FRAME, dtype=np.int16)) is False
