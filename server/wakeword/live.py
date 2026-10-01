"""Live wake word meter: prints the score while you talk. Ctrl+C to stop.

Run from server/:  PYTHONPATH=. uv run python wakeword/live.py [MODEL] [THRESHOLD]
"""

import sys

import sounddevice as sd

from infra.audio.listener import FRAME, OpenWakeWord


def main(model: str = "wakeword/alfred.onnx", threshold: str = "0.5") -> None:
    wake, cut = OpenWakeWord(model), float(threshold)
    print(f"ouvindo com {model}, threshold {cut}. Fale 'Alfred'… (Ctrl+C sai)")
    with sd.InputStream(samplerate=16000, channels=1, dtype="int16", blocksize=FRAME) as mic:
        while True:
            score = wake.score(mic.read(FRAME)[0][:, 0])
            if score >= 0.05:
                bar = "#" * int(score * 40)
                print(f"{score:4.2f} {bar:<40} {'<<< ACORDOU' if score >= cut else ''}")


if __name__ == "__main__":
    try:
        main(*sys.argv[1:])
    except KeyboardInterrupt:
        pass
