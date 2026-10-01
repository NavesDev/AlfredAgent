"""Speech queue → Kokoro → speaker, publishing levels for UI animation."""

import logging
import queue
import threading
from collections.abc import Callable, Iterator

import numpy as np

from config import Kokoro as KokoroConfig
from errors import AudioError, DependencyError
from events import EventBus
from infra.audio import level

KOKORO_RATE = 24000
LEVELS_PER_S = 15

log = logging.getLogger(__name__)


class Talker:
    def __init__(
        self,
        bus: EventBus,
        synthesize: Callable[[str], Iterator[np.ndarray]],
        play: Callable[[np.ndarray], None],
        sample_rate: int = KOKORO_RATE,
    ) -> None:
        self._bus, self._synthesize, self._play = bus, synthesize, play
        self._block = sample_rate // LEVELS_PER_S
        self._queue: queue.Queue[str] = queue.Queue()

    @property
    def is_speaking(self) -> bool:
        return self._queue.unfinished_tasks > 0

    def say(self, text: str) -> None:
        self._queue.put(text)

    def run(self, stop: threading.Event) -> None:
        while not stop.is_set():
            self.process_one(timeout=0.1)

    def process_one(self, timeout: float | None = None) -> None:
        try:
            text = self._queue.get(timeout=timeout)
        except queue.Empty:
            return
        try:
            self._speak(text)
        except AudioError as e:
            self._bus.publish("error", where="talker", message=str(e))
        except Exception as e:
            log.exception("talker failed")
            self._bus.publish("error", where="talker", message=repr(e))
        finally:
            self._queue.task_done()
            if not self.is_speaking:
                self._bus.publish("voice_state", state="idle")

    def _speak(self, text: str) -> None:
        self._bus.publish("voice_state", state="speaking")
        for chunk in self._synthesize(text):
            for start in range(0, len(chunk), self._block):
                block = chunk[start : start + self._block]
                self._bus.publish("audio_level", source="tts", level=level(block))
                self._play(block)


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
    return stream.write
