"""Add Romance-accent positives (Kokoro pt/es/it/fr) to the Piper ones before augmentation.

Piper only speaks English, and a model trained on it alone scored ~0 on Brazilian "Alfred".
pm_alex is left out so evaluate.py has an unseen pt-BR voice.

Run from server/:  PYTHONPATH=. uv run python wakeword/train/kokoro_positives.py OUT_DIR
"""

import sys
from pathlib import Path

import numpy as np
import scipy.io.wavfile
import scipy.signal
from kokoro import KPipeline

VOICES = {
    "p": ["pf_dora", "pm_santa"],
    "e": ["ef_dora", "em_alex", "em_santa"],
    "i": ["if_sara", "im_nicola"],
    "f": ["ff_siwis"],
}
TEXTS = ["Alfred.", "Alfred,", "Alfred!", "Alfred?", "Ei, Alfred.", "Alfredo."]
SPEEDS = np.arange(0.7, 1.45, 0.05)
COPIES = 10  # each copy gets different random augmentation later


def main(out: Path) -> None:
    n = 0
    for lang, voices in VOICES.items():
        pipeline = KPipeline(lang_code=lang, repo_id="hexgrad/Kokoro-82M")
        for voice in voices:
            for speed in SPEEDS:
                for text in TEXTS:
                    audio = np.concatenate([r.audio.numpy() for r in pipeline(text, voice, speed)])
                    pcm = np.clip(scipy.signal.resample_poly(audio, 2, 3), -1, 1) * 32767
                    for copy in range(COPIES):
                        name = f"kokoro_{voice}_{speed:.2f}_{TEXTS.index(text)}_{copy}.wav"
                        scipy.io.wavfile.write(out / name, 16000, pcm.astype(np.int16))
                        n += 1
    print(f"wrote {n} clips to {out}")


if __name__ == "__main__":
    main(Path(sys.argv[1]))
