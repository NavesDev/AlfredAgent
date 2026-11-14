"""Score models on the user's held-out recordings (the ones add_voice.py leaves out).

Run from server/:  PYTHONPATH=. uv run python wakeword/train/evaluate_voice.py MODEL [MODEL...]
"""

import sys
import wave
from pathlib import Path

import numpy as np

from infra.audio.listener import FRAME, OpenWakeWord

VOICE = Path(__file__).parent / "voice"
THRESHOLDS = [0.3, 0.5]


def load(path: Path) -> np.ndarray:
    with wave.open(str(path)) as w:
        return np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16)


def scores(wake: OpenWakeWord, pcm: np.ndarray) -> list[float]:
    wake.reset()
    pcm = np.concatenate([np.zeros(8000, np.int16), pcm, np.zeros(16000, np.int16)])
    return [wake.score(pcm[i : i + FRAME]) for i in range(0, len(pcm) - FRAME, FRAME)]


def main(models: list[str]) -> None:
    takes = [t for i, t in enumerate(sorted(VOICE.glob("alfred_*.wav"))) if i % 5 == 0]
    free = load(VOICE / "negative_free.wav")
    chunks = [free[i : i + 32000] for i in range(0, len(free) - 32000 + 1, 32000)][::5]
    for model in models:
        wake = OpenWakeWord(model)
        peaks = {t.stem.removeprefix("alfred_"): max(scores(wake, load(t))) for t in takes}
        neg = max((max(scores(wake, c)) for c in chunks), default=0.0)
        print(f"\n{model}")
        print("  " + "  ".join(f"{k}={v:.2f}" for k, v in peaks.items()))
        for cut in THRESHOLDS:
            hits = sum(v >= cut for v in peaks.values())
            print(f"  threshold {cut}: acordou {hits}/{len(peaks)}; fala livre pico {neg:.2f}")


if __name__ == "__main__":
    main(sys.argv[1:])
