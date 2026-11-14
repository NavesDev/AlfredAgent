"""Speech queue → Kokoro → speaker, publishing levels for UI animation."""

import logging
import queue
import random
import threading
from collections.abc import Callable, Iterator, Sequence

import numpy as np

from config import Kokoro as KokoroConfig
from errors import AudioError, DependencyError
from events import EventBus
from infra.audio import level

KOKORO_RATE = 24000
LEVELS_PER_S = 15
CHIMES = {"start": (660.0, 990.0), "end": (990.0, 660.0)}  # rising = listening, falling = done
PAUSE_S = 0.5  # silence between two lines played back to back, so they don't run together

log = logging.getLogger(__name__)


class Talker:
    def __init__(
        self,
        bus: EventBus,
        synthesize: Callable[[str], Iterator[np.ndarray]],
        play: Callable[[np.ndarray], None],
        sample_rate: int = KOKORO_RATE,
        acknowledgements: Sequence[str] = (),
    ) -> None:
        self._bus, self._synthesize, self._play = bus, synthesize, play
        self._block = sample_rate // LEVELS_PER_S
        self._pause = np.zeros(int(sample_rate * PAUSE_S), dtype=np.float32)
        self._chimes = {kind: _sweep(*hz, sample_rate) for kind, hz in CHIMES.items()}
        # Synthesized once at startup so they play with no delay.
        self._acks = [np.concatenate(list(synthesize(text))) for text in acknowledgements]
        self._last_ack = -1
        self._queue: queue.Queue[str | np.ndarray] = queue.Queue()
        self._resting = "idle"
        self._held: list[str] = []  # notifications waiting for Alfred's turn to end
        self._lock = threading.Lock()

    @property
    def is_speaking(self) -> bool:
        return self._queue.unfinished_tasks > 0

    def say(self, text: str) -> None:
        self._queue.put(text)

    def notify(self, text: str) -> None:
        """A line nobody asked for (a session finished): during Alfred's turn it waits for the
        turn to end, so it never lands in the middle of his answer."""
        with self._lock:
            if self._resting == "thinking":
                self._held.append(text)
                return
        self.say(text)

    def set_resting(self, state: str) -> None:
        """voice_state published when the queue empties: "thinking" while a turn is still on.
        Leaving the turn releases the notifications held during it."""
        with self._lock:
            self._resting = state
            held, self._held = (self._held, []) if state != "thinking" else ([], self._held)
        for text in held:
            self.say(text)

    def acknowledge(self) -> None:
        """Queue a short ready-made reply ("Certo.") so the user hears something while STT and
        Claude work. Falls back to the end chime when none are configured."""
        if not self._acks:
            self.chime("end")
            return
        choices = [i for i in range(len(self._acks)) if i != self._last_ack] or [0]
        self._last_ack = random.choice(choices)
        self._queue.put(self._acks[self._last_ack])

    def chime(self, kind: str) -> None:
        """Short cue played right away, outside the speech queue and voice states."""
        self._play(self._chimes[kind])

    def run(self, stop: threading.Event) -> None:
        while not stop.is_set():
            self.process_one(timeout=0.1)

    def process_one(self, timeout: float | None = None) -> None:
        try:
            item = self._queue.get(timeout=timeout)
        except queue.Empty:
            return
        if not isinstance(item, str):  # acknowledgement: plays outside voice states
            try:
                self._play(item)
            finally:
                self._queue.task_done()
            return
        try:
            self._speak(item)
            if not self._queue.empty():
                self._play(self._pause)
        except AudioError as e:
            self._bus.publish("error", where="talker", message=str(e))
        except Exception as e:
            log.exception("talker failed")
            self._bus.publish("error", where="talker", message=repr(e))
        finally:
            self._queue.task_done()
            if not self.is_speaking:
                self._bus.publish("voice_state", state=self._resting)

    def _speak(self, text: str) -> None:
        self._bus.publish("voice_state", state="speaking")
        for chunk in self._synthesize(text):
            for start in range(0, len(chunk), self._block):
                block = chunk[start : start + self._block]
                self._bus.publish("audio_level", source="tts", level=level(block))
                self._play(block)


def _sweep(start_hz: float, end_hz: float, rate: int, seconds: float = 0.12) -> np.ndarray:
    t = np.linspace(0, seconds, int(rate * seconds), endpoint=False)
    phase = 2 * np.pi * np.cumsum(np.linspace(start_hz, end_hz, len(t))) / rate
    return (0.3 * np.sin(phase) * np.hanning(len(t))).astype(np.float32)


def load_kokoro(config: KokoroConfig) -> Callable[[str], Iterator[np.ndarray]]:
    from kokoro import KPipeline

    try:
        pipeline = KPipeline(lang_code="p", repo_id="hexgrad/Kokoro-82M")
        pipeline.load_voice(config.voice)
    except Exception as e:
        raise DependencyError(f"cannot load Kokoro voice {config.voice!r}: {e}") from e

    def synthesize(text: str) -> Iterator[np.ndarray]:
        try:
            for result in pipeline(text, voice=config.voice, speed=config.speed):
                if result.audio is not None:
                    yield result.audio.numpy()
        except Exception as e:
            raise AudioError(f"speech synthesis failed: {e}") from e

    return synthesize


def open_speaker() -> Callable[[np.ndarray], None]:
    import sounddevice as sd

    stream = sd.OutputStream(samplerate=KOKORO_RATE, channels=1, dtype="float32")
    stream.start()
    return lambda block: stream.write(block)
