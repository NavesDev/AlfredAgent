"""Download background audio and room impulse responses as 16 kHz wavs (openWakeWord recipe)."""

import sys
from pathlib import Path

import datasets
import numpy as np
import scipy.io.wavfile
from tqdm import tqdm


def dump(name: str, split: str, out: Path, limit: int | None = None, **kwargs: str) -> None:
    out.mkdir(exist_ok=True)
    if any(out.iterdir()):
        return
    ds = datasets.load_dataset(name, split=split, streaming=True, **kwargs)
    ds = ds.cast_column("audio", datasets.Audio(sampling_rate=16000))
    for i, row in enumerate(tqdm(ds.take(limit) if limit else ds, desc=name)):
        audio = (np.clip(row["audio"]["array"], -1, 1) * 32767).astype(np.int16)
        scipy.io.wavfile.write(out / f"{i}.wav", 16000, audio)


if __name__ == "__main__":
    work = Path(sys.argv[1])
    dump("davidscripka/MIT_environmental_impulse_responses", "train", work / "mit_rirs")
    dump("agkphysics/AudioSet", "train", work / "audioset_16k", limit=10000, name="balanced")
    dump("rudraml/fma", "train", work / "fma", limit=1000, name="small")
