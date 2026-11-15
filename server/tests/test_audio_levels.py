import numpy as np

from infra.audio import BANDS, bands


def tone(hz: float, rate: int = 16000, amp: float = 0.3, n: int = 1280) -> np.ndarray:
    return (amp * np.sin(2 * np.pi * hz * np.arange(n) / rate)).astype(np.float32)


def test_silence_has_every_band_at_zero() -> None:
    assert bands(np.zeros(1280, dtype=np.float32), 16000) == [0.0] * BANDS


def test_values_stay_in_unit_range() -> None:
    values = bands(np.ones(1280, dtype=np.float32), 16000)
    assert len(values) == BANDS and all(0 <= v <= 1 for v in values)


def test_low_tone_peaks_in_a_low_band_and_high_tone_in_a_high_band() -> None:
    low = bands(tone(200), 16000)
    high = bands(tone(3500), 16000)
    assert int(np.argmax(low)) < BANDS // 3
    assert int(np.argmax(high)) >= 2 * BANDS // 3


def test_louder_voice_raises_its_band() -> None:
    quiet = bands(tone(500, amp=0.02), 16000)
    loud = bands(tone(500, amp=0.5), 16000)
    peak = int(np.argmax(loud))
    assert loud[peak] > quiet[peak]


def test_works_at_the_tts_rate() -> None:
    assert int(np.argmax(bands(tone(3500, rate=24000, n=1600), 24000))) >= 2 * BANDS // 3
