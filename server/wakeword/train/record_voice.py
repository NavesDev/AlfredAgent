"""Record the user's own "Alfred" takes (positives) and free speech without it (negatives).

Run from server/:  PYTHONPATH=. uv run python wakeword/train/record_voice.py
Clips go to wakeword/train/voice/ (git-ignored: it is the user's voice). Re-running resumes.
"""

import sys
import time
import wave
from pathlib import Path

import numpy as np
import sounddevice as sd

SR = 16000
OUT = Path(__file__).parent / "voice"
TAKE_S = 2.5
FREE_S = 60
# (style, count, what the user should do)
STYLES = [
    ("rapido", 15, 'Diga só "Alfred", RÁPIDO, como você fala no dia a dia'),
    ("normal", 15, 'Diga só "Alfred", NORMAL'),
    ("lento", 8, 'Diga só "Alfred", LENTO'),
    ("longe", 8, 'Diga só "Alfred", NORMAL, mais longe do microfone ou mais baixo'),
    ("ei", 6, 'Diga "Ei, Alfred" (as duas palavras juntas)'),
]


def record(seconds: float) -> np.ndarray:
    audio = sd.rec(int(seconds * SR), samplerate=SR, channels=1, dtype="int16")
    sd.wait()
    return audio[:, 0]


def rms_windows(audio: np.ndarray, win: int = 320) -> np.ndarray:
    n = len(audio) // win
    x = audio[: n * win].astype(np.float32).reshape(n, win) / 32768
    return np.sqrt((x**2).mean(axis=1))


def speech_span(audio: np.ndarray, floor: float) -> tuple[int, int] | None:
    loud = np.flatnonzero(rms_windows(audio) > max(floor * 4, 0.004))
    if len(loud) < 5:  # under 100 ms of sound
        return None
    return loud[0] * 320, (loud[-1] + 1) * 320


def save(path: Path, audio: np.ndarray) -> None:
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(audio.astype(np.int16).tobytes())


def take(floor: float) -> np.ndarray:
    while True:
        print("   ● fale agora", end="", flush=True)
        audio = record(TAKE_S)
        span = speech_span(audio, floor)
        if span is None:
            print("  ✗ não ouvi, de novo")
        elif np.abs(audio).max() >= 32000:
            print("  ✗ estourou (alto demais), de novo")
        elif span[0] < 0.05 * SR or span[1] > len(audio) - 0.1 * SR:
            print("  ✗ cortou no começo ou no fim, de novo")
        else:
            print("  ✓")
            start, end = max(0, span[0] - int(0.2 * SR)), min(len(audio), span[1] + int(0.3 * SR))
            time.sleep(0.6)
            return audio[start:end]


def main() -> None:
    OUT.mkdir(exist_ok=True)
    print("Fique em silêncio 2 s para medir o ruído…")
    floor = float(np.median(rms_windows(record(2))))
    print(f"ruído de fundo: {floor:.4f}\n")
    total = sum(n for _, n, _ in STYLES)
    done = len(list(OUT.glob("alfred_*.wav")))
    for style, count, hint in STYLES:
        have = len(list(OUT.glob(f"alfred_{style}_*.wav")))
        if have >= count:
            continue
        print(f"== {hint} ==")
        input("   Enter para começar…")
        for i in range(have, count):
            done += 1
            print(f"[{done}/{total}] {style}", end="")
            save(OUT / f"alfred_{style}_{i:02d}.wav", take(floor))
        print()
    free = OUT / "negative_free.wav"
    if not free.exists():
        print(f"== Agora fale à vontade por {FREE_S} s SEM dizer Alfred ==")
        print("   (leia algo em voz alta, comente o dia, dê comandos como se fosse pro Alfred)")
        input("   Enter para começar…")
        save(free, record(FREE_S))
    print(f"\nPronto: {len(list(OUT.glob('alfred_*.wav')))} takes + fala livre em {OUT}")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        sys.exit("\ninterrompido; rode de novo para continuar de onde parou")
