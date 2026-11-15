"""Microphone → wake word → record until silence → Whisper → transcript callback.

Whisper runs on its own worker thread. It starts early, on the audio so far, once a pause
reaches `guess_ms`: if no speech follows before `silence_ms`, that guess is the transcript,
so the command is ready when the pause ends. Speech after the guess discards it. Only while
Whisper is fast (GPU): on the CPU a discarded guess (~6 s) would delay the real one. The mic
is ignored while the final transcript is awaited.
"""

import logging
import os
import threading
from collections.abc import Callable
from concurrent.futures import Future, ThreadPoolExecutor
from pathlib import Path
from typing import Protocol

import numpy as np

from config import Listener as ListenerConfig
from config import Whisper as WhisperConfig
from errors import AudioError, DependencyError
from events import EventBus
from infra.audio import level
from infra.audio.device import OnDemandGpu

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
        warm: Callable[[], None] = lambda: None,
        can_guess: Callable[[], bool] = lambda: True,
    ) -> None:
        self._bus, self._config, self._threshold = bus, config, threshold
        self._wake, self._is_speech, self._transcribe = wake, is_speech, transcribe
        self._on_transcript, self._muted, self._chime = on_transcript, muted, chime
        self._acknowledge = acknowledge or (lambda: chime("end"))
        self._warm = warm  # the wake word loads Whisper on the GPU while the user speaks
        self._can_guess = can_guess
        self._max_samples = config.max_record_s * config.sample_rate
        self._recording: list[np.ndarray] | None = None
        self._guess: Future[str] | None = None  # transcript of the audio before this pause
        self._stt = ThreadPoolExecutor(max_workers=1, thread_name_prefix="stt")

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
                self._warm()
                self._recording, self._heard, self._silence_ms = [], False, 0
                self._guess = None
                self._bus.publish("voice_state", state="listening")
                self._chime("start")
            return
        self._recording.append(frame)
        self._bus.publish("audio_level", source="mic", level=level(frame / 32768))
        if self._is_speech(frame):
            self._heard, self._silence_ms, self._guess = True, 0, None
        elif self._heard:
            self._silence_ms += FRAME_MS
            if (
                self._guess is None
                and self._silence_ms >= self._config.guess_ms
                and self._can_guess()
            ):
                self._guess = self._stt.submit(self._transcribe, self._audio())
        if self._silence_ms >= self._config.silence_ms or self._recorded() >= self._max_samples:
            self._finish()

    def _recorded(self) -> int:
        return len(self._recording or []) * FRAME

    def _audio(self) -> np.ndarray:
        return np.concatenate(self._recording or [])[: self._max_samples]

    def _finish(self) -> None:
        guess, self._guess = self._guess, None
        transcript = guess or self._stt.submit(self._transcribe, self._audio())
        self._recording = None
        if self._heard:
            self._acknowledge()  # answer right away, before Whisper's seconds
        else:
            self._chime("end")
        self._bus.publish("voice_state", state="transcribing")
        text = transcript.result().strip()
        if not text:
            self._bus.publish("voice_state", state="idle")
            return
        self._bus.publish("transcript", text=text, source="voice")
        self._on_transcript(text)

    def _fail(self, message: str) -> None:
        self._recording, self._guess = None, None
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


class Whisper:
    """Transcriber that loads on the GPU on demand (see `OnDemandGpu`).

    `hotwords` is read on every call: the current session and project names.
    """

    def __init__(self, config: WhisperConfig, hotwords: Callable[[], str] = lambda: "") -> None:
        # torch loads its CUDA 12 cuBLAS/cuDNN wheels into the process; CTranslate2 finds
        # them by soname and fails with "libcublas.so.12 is not found" otherwise.
        import torch  # noqa: F401
        from faster_whisper import WhisperModel

        downloaded = False

        def load(device: str, compute_type: str) -> Callable[[], WhisperModel]:
            def model() -> WhisperModel:
                nonlocal downloaded
                loaded = WhisperModel(
                    config.model,
                    device,
                    compute_type=compute_type,
                    cpu_threads=0 if device == "cuda" else os.cpu_count() or 0,
                    local_files_only=downloaded,  # skips the Hub check (~0.4 s) on reloads
                )
                downloaded = True
                return loaded

            return model

        cpu_type = config.compute_type if config.device == "cpu" else "int8"
        self._config, self._hotwords = config, hotwords
        self._models = OnDemandGpu(
            "Whisper",
            config.device,
            config.idle_s,
            load_gpu=load("cuda", config.compute_type),
            load_cpu=load("cpu", cpu_type),
            need_mb=1500,  # large-v3-turbo int8_float16 measured ~1.2 GB with its context
        )

    def check(self) -> None:
        """Load once at startup, so a missing model fails fast."""
        try:
            self._models.run(lambda _: None)
        except Exception as e:
            raise DependencyError(f"cannot load Whisper {self._config.model!r}: {e}") from e

    def warm(self) -> None:
        self._models.warm()

    def fast(self) -> bool:
        return self._models.wants_gpu

    def __call__(self, audio: np.ndarray) -> str:
        samples = audio.astype(np.float32) / 32768
        hotwords = self._hotwords() or None
        try:
            return self._models.run(
                lambda model: " ".join(
                    s.text
                    for s in model.transcribe(
                        samples,
                        language=self._config.language,
                        initial_prompt=self._config.initial_prompt or None,
                        hotwords=hotwords,
                        beam_size=1,
                    )[0]
                )
            )
        except Exception as e:
            raise AudioError(f"transcription failed: {e}") from e


def load_whisper(config: WhisperConfig, hotwords: Callable[[], str] = lambda: "") -> Whisper:
    whisper = Whisper(config, hotwords)
    whisper.check()
    return whisper
