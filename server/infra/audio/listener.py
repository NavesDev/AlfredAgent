"""Microphone → wake word → record until silence → Whisper → transcript callback.

Capture and STT share this thread: they are sequential, and the mic is ignored while busy.
"""

import logging
import os
import threading
from collections.abc import Callable
from pathlib import Path
from typing import Protocol

import numpy as np

from config import Listener as ListenerConfig
from config import Whisper as WhisperConfig
from errors import AudioError, DependencyError
from events import EventBus
from infra.audio import level

FRAME = 1280  # 80 ms at 16 kHz, openWakeWord's native frame
FRAME_MS = 80

log = logging.getLogger(__name__)


class WakeWord(Protocol):
    def score(self, frame: np.ndarray) -> float: ...
    def reset(self) -> None: ...


class Listener:
    def __init__(
        self,
        bus: EventBus,
        config: ListenerConfig,
        threshold: float,
        wake: WakeWord,
        is_speech: Callable[[np.ndarray], bool],
        transcribe: Callable[[np.ndarray], str],
        on_transcript: Callable[[str], None],
        muted: Callable[[], bool],
        chime: Callable[[str], None] = lambda _: None,
        acknowledge: Callable[[], None] | None = None,
    ) -> None:
        self._bus, self._config, self._threshold = bus, config, threshold
        self._wake, self._is_speech, self._transcribe = wake, is_speech, transcribe
        self._on_transcript, self._muted, self._chime = on_transcript, muted, chime
        self._acknowledge = acknowledge or (lambda: chime("end"))
        self._max_samples = config.max_record_s * config.sample_rate
        self._recording: list[np.ndarray] | None = None

    def run(self, stop: threading.Event) -> None:
        import sounddevice as sd

        sr = self._config.sample_rate
        with sd.InputStream(samplerate=sr, channels=1, dtype="int16", blocksize=FRAME) as stream:
            while not stop.is_set():
                self.feed(stream.read(FRAME)[0][:, 0])

    def feed(self, frame: np.ndarray) -> None:
        try:
            self._step(frame)
        except AudioError as e:
            self._fail(str(e))
        except Exception as e:
            log.exception("listener failed")
            self._fail(repr(e))

    def _step(self, frame: np.ndarray) -> None:
        if self._recording is None:
            if not self._muted() and self._wake.score(frame) >= self._threshold:
                self._wake.reset()
                self._recording, self._heard, self._silence_ms = [], False, 0
                self._bus.publish("voice_state", state="listening")
                self._chime("start")
            return
        self._recording.append(frame)
        self._bus.publish("audio_level", source="mic", level=level(frame / 32768))
        if self._is_speech(frame):
            self._heard, self._silence_ms = True, 0
        elif self._heard:
            self._silence_ms += FRAME_MS
        if self._silence_ms >= self._config.silence_ms or self._recorded() >= self._max_samples:
            self._finish()

    def _recorded(self) -> int:
        return len(self._recording or []) * FRAME

    def _finish(self) -> None:
        audio = np.concatenate(self._recording or [])[: self._max_samples]
        self._recording = None
        if self._heard:
            self._acknowledge()  # answer right away, before Whisper's seconds
        else:
            self._chime("end")
        self._bus.publish("voice_state", state="transcribing")
        text = self._transcribe(audio).strip()
        if not text:
            self._bus.publish("voice_state", state="idle")
            return
        self._bus.publish("transcript", text=text, source="voice")
        self._on_transcript(text)

    def _fail(self, message: str) -> None:
        self._recording = None
        self._bus.publish("error", where="listener", message=message)
        self._bus.publish("voice_state", state="idle")


class OpenWakeWord:
    def __init__(self, model: str) -> None:
        import openwakeword
        from openwakeword.model import Model

        try:
            if not Path(model).exists():
                openwakeword.utils.download_models([model])
            self._model = Model(wakeword_models=[model], inference_framework="onnx")
        except Exception as e:
            raise DependencyError(f"cannot load wake word model {model!r}: {e}") from e

    def score(self, frame: np.ndarray) -> float:
        return float(max(self._model.predict(frame).values()))

    def reset(self) -> None:
        self._model.reset()


def load_vad(threshold: float = 0.5) -> Callable[[np.ndarray], bool]:
    from openwakeword.vad import VAD

    vad = VAD()
    return lambda frame: bool(vad.predict(frame, frame_size=640) >= threshold)


def load_whisper(
    config: WhisperConfig, hotwords: Callable[[], str] = lambda: ""
) -> Callable[[np.ndarray], str]:
    """`hotwords` is read on every call: the current session and project names."""
    from faster_whisper import WhisperModel

    try:
        model = WhisperModel(
            config.model,
            config.device,
            compute_type=config.compute_type,
            cpu_threads=os.cpu_count() or 0,
        )
    except Exception as e:
        raise DependencyError(f"cannot load Whisper {config.model!r}: {e}") from e

    def transcribe(audio: np.ndarray) -> str:
        try:
            segments, _ = model.transcribe(
                audio.astype(np.float32) / 32768,
                language=config.language,
                initial_prompt=config.initial_prompt or None,
                hotwords=hotwords() or None,
                beam_size=1,
            )
            return " ".join(s.text for s in segments)
        except Exception as e:
            raise AudioError(f"transcription failed: {e}") from e

    return transcribe
