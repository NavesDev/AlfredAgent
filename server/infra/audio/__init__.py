from itertools import pairwise

import numpy as np


def level(samples: np.ndarray) -> float:
    """Loudness in 0..1 for UI animation; samples are float in [-1, 1]."""
    return min(1.0, float(np.sqrt(np.mean(np.square(samples)))) * 4)


BANDS = 9
"""Frequency bands sent with each audio level, for the desktop bar visualizer."""
_LOW_HZ, _HIGH_HZ = 100.0, 5000.0
_FLOOR_DB, _CEIL_DB = -70.0, -15.0


def bands(samples: np.ndarray, rate: int) -> list[float]:
    """Loudness per log-spaced voice band (100 Hz to 5 kHz), each in 0..1."""
    spectrum = np.abs(np.fft.rfft(samples * np.hanning(len(samples)))) / (len(samples) / 4)
    freqs = np.fft.rfftfreq(len(samples), 1 / rate)
    edges = np.geomspace(_LOW_HZ, _HIGH_HZ, BANDS + 1)
    out = []
    for lo, hi in pairwise(edges):
        band = spectrum[(freqs >= lo) & (freqs < hi)]
        amp = float(band.max()) if band.size else 0.0
        db = 20 * np.log10(amp) if amp > 0 else _FLOOR_DB
        loudness = np.clip((db - _FLOOR_DB) / (_CEIL_DB - _FLOOR_DB), 0, 1)
        out.append(round(float(np.sqrt(loudness)), 3))
    return out


def check_audio(input_rate: int, output_rate: int = 24000) -> None:
    """Fail fast if PortAudio or the default mic/speaker is unavailable."""
    from errors import DependencyError

    try:
        import sounddevice as sd

        sd.check_input_settings(samplerate=input_rate, channels=1, dtype="int16")
        sd.check_output_settings(samplerate=output_rate, channels=1, dtype="float32")
    except Exception as e:
        raise DependencyError(f"audio device unavailable: {e}") from e
