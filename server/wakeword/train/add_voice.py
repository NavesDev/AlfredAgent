"""Copy the user's recordings (record_voice.py) into the training clip folders, before augmentation.

Every 5th take and every 5th free-speech chunk is held out for evaluate_voice.py. Each kept clip
is copied many times: augmentation gives every copy different noise and reverb.

Usage:  python add_voice.py VOICE_DIR OUTPUT_DIR   (OUTPUT_DIR = .work/output/alfred)
"""

import shutil
import sys
import wave
from pathlib import Path

import numpy as np

POSITIVE_COPIES = 75  # ~42 takes -> ~3k of ~40k positives
NEGATIVE_COPIES = 50
CHUNK = 32000  # 2 s, the training window


def held_out(i: int) -> bool:
    return i % 5 == 0


def free_chunks(path: Path) -> list[np.ndarray]:
    with wave.open(str(path)) as w:
        audio = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16)
    return [audio[i : i + CHUNK] for i in range(0, len(audio) - CHUNK + 1, CHUNK)]


def write(path: Path, audio: np.ndarray) -> None:
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(16000)
        w.writeframes(audio.tobytes())


def main(voice: Path, out: Path) -> None:
    for old in [*out.glob("positive_train/user_*"), *out.glob("negative_train/user_*")]:
        old.unlink()
    takes = sorted(voice.glob("alfred_*.wav"))
    kept = [t for i, t in enumerate(takes) if not held_out(i)]
    for take in kept:
        for copy in range(POSITIVE_COPIES):
            shutil.copy(take, out / "positive_train" / f"user_{take.stem}_{copy}.wav")
    free = voice / "negative_free.wav"
    chunks = free_chunks(free) if free.exists() else []
    train_chunks = [c for i, c in enumerate(chunks) if not held_out(i)]
    for i, chunk in enumerate(train_chunks):
        for copy in range(NEGATIVE_COPIES):
            write(out / "negative_train" / f"user_free_{i:02d}_{copy}.wav", chunk)
    print(f"user voice: {len(kept)}/{len(takes)} takes, {len(train_chunks)}/{len(chunks)} chunks")


if __name__ == "__main__":
    main(Path(sys.argv[1]), Path(sys.argv[2]))
