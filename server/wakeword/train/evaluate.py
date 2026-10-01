"""Score a wake word model on pt-BR Kokoro voices the training never heard.

Run from server/:  PYTHONPATH=. uv run python wakeword/train/evaluate.py MODEL [WAKE]
WAKE replaces "Alfred" in the positive phrases (e.g. "hey jarvis" to sanity-check a stock model).
"""

import sys

import numpy as np

from config import Kokoro
from infra.audio.listener import FRAME, OpenWakeWord
from infra.audio.talker import load_kokoro

VOICES = ["pf_dora", "pm_alex", "pm_santa"]
SPEEDS = [0.9, 1.1, 1.3]
POSITIVES = [
    "{w}.",
    "{w}, qual a diferença entre JWT e sessão?",
    "Ei {w}, tenho e-mail importante hoje?",
    "{w}, backend: roda os testes do billing.",
]
NEGATIVES = [
    "Qual a diferença entre JWT e sessão?",
    "Comprei alface e alfafa na feira.",
    "Eu ofereci ajuda pro Fred ontem.",
    "O alfabeto grego começa com alfa.",
    "Tenho e-mail importante hoje? Roda os testes.",
    "Ele ficou com medo e saiu correndo.",
    "Alfaiate, alfinete e alforria.",
    "Vou pagar o frete amanhã de manhã.",
]


def to_16k_pcm(audio: np.ndarray) -> np.ndarray:
    resampled = np.interp(np.arange(0, len(audio), 1.5), np.arange(len(audio)), audio)
    padded = np.concatenate([np.zeros(8000), resampled, np.zeros(16000)])
    return (np.clip(padded, -1, 1) * 32767).astype(np.int16)


def peak_score(wake: OpenWakeWord, pcm: np.ndarray) -> float:
    wake.reset()
    return max(wake.score(pcm[i : i + FRAME]) for i in range(0, len(pcm) - FRAME, FRAME))


def main(model: str, word: str = "Alfred", threshold: str = "0.5") -> None:
    cut = float(threshold)
    wake = OpenWakeWord(model)
    results: dict[bool, list[tuple[float, str]]] = {True: [], False: []}
    for voice in VOICES:
        for speed in SPEEDS:
            synth = load_kokoro(Kokoro(voice=voice, speed=speed))
            for positive, phrases in ((True, POSITIVES), (False, NEGATIVES)):
                for phrase in phrases:
                    text = phrase.format(w=word)
                    pcm = to_16k_pcm(np.concatenate(list(synth(text))))
                    results[positive].append((peak_score(wake, pcm), f"{voice} x{speed}: {text}"))

    hits = [s for s, _ in results[True] if s >= cut]
    false_accepts = [(s, t) for s, t in results[False] if s >= cut]
    print(f"model {model}, threshold {cut}")
    print(f"recall: {len(hits)}/{len(results[True])}")
    for voice in VOICES:  # kokoro_positives.py trains on all but pm_alex
        scores = [s for s, t in results[True] if t.startswith(voice)]
        print(f"  {voice}: {sum(s >= cut for s in scores)}/{len(scores)}")
    print(f"false accepts: {len(false_accepts)}/{len(results[False])}")
    for score, text in sorted(results[True])[:5]:
        print(f"  weakest positive {score:.2f}  {text}")
    for score, text in sorted(results[False], reverse=True)[:5]:
        print(f"  strongest negative {score:.2f}  {text}")


if __name__ == "__main__":
    main(*sys.argv[1:])
