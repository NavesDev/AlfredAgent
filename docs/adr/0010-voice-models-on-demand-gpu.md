# 0010 — Voice models on the GPU on demand, with CPU fallback

- **Status:** Accepted
- **Date:** 2026-11-14

## Context

The machine got an RTX 3060 (12 GB); before, there was no NVIDIA GPU and everything ran on the CPU. The GPU is shared with the `imagens-local` service, whose jobs take up to ~10–11 GB and which fits only one model at a time. Issue #5.

Measurements with the same audio (8 s command, `large-v3-turbo`, `beam_size=1`):

| Piece | CPU | GPU |
|---|---|---|
| Whisper | 6.15 s (`int8`) | 0.34 s (`float16`), 0.31 s (`int8_float16`) |
| Whisper, 3 s of audio | 5.98 s | 0.26 s |
| Kokoro, short sentence (2.5 s of speech) | 0.64 s | 0.07 s |
| Kokoro, 8 s of speech | 2.28 s | 0.14 s |

- Same transcribed text on the CPU and on the GPU. `int8_float16` uses ~1.1 GB of VRAM, `float16` ~2.1 GB.
- Whisper costs almost the same for 3 s or 8 s: the encoder always processes the 30 s window.
- Load: Whisper on the GPU ~2.6 s (disk cache); Kokoro moves CPU↔GPU in ~0.07 s. After releasing, ~470 MB remain (torch and CTranslate2 CUDA contexts).
- Wake word and VAD (openWakeWord, ONNX) stay on the CPU: they are tiny and run per 80 ms frame.
- Concurrency: with Whisper + Kokoro resident (1.86 GB), `z-image-turbo` at 1024 OOMs while loading. With Alfred idle (only the ~470 MB of context) it generates normally (28 s). With the GPU full, loading Whisper fails with OOM.
- Install: torch `cu126` brings cuBLAS/cuDNN 9 as `nvidia-*` wheels, which CTranslate2 also uses. The venv went from 2.1 GB to 7.5 GB. `cu13x` does not work: CTranslate2 4.x needs CUDA 12.

## Decision

- **Device per model** in `config.yaml` (`whisper.device`, `kokoro.device`: `cuda` | `cpu`), default `cuda`. Whisper in `int8_float16` on the GPU, `int8` on the CPU. The model stays `large-v3-turbo`: on the GPU it already takes 0.3 s, and the full `large-v3` would have a ~4x slower decoder for a small gain in Portuguese.
- **GPU on demand** (`infra/audio/device.py`, `OnDemandGpu`):
  - Whisper loads on the GPU when the wake word fires, while the user is talking; Kokoro loads on the first speech;
  - each releases the GPU after `idle_s` unused (Whisper 30 s, Kokoro 10 s);
  - it only goes to the GPU if no other process holds ≥ 1 GB there (an image job) and 2 GB remain beyond what the model needs. `nvidia-smi` answers in ~25 ms and opens no CUDA context.
- **Fallback, not fail-fast:** a busy GPU, no CUDA or an OOM mid-call runs that call on the CPU (the CPU model loads the first time). After a failed load, it stays 60 s on the CPU before trying again (each lost attempt costs ~2.5 s). A missing model still fails at boot.
- **Early transcription, not streaming or 3 s chunks:** on a `listener.guess_ms` (400 ms) pause, Whisper already transcribes the audio so far; if nobody speaks again before `silence_ms`, that text is the command. Speech after the guess discards it. Only while Whisper is on the GPU: on the CPU a discarded guess (~6 s) would delay the real command.
  - 3 s chunks would each cost as much as the whole audio (30 s window), cut words and, on the CPU, take ~6 s each.
  - Streaming with continuous re-transcription spends GPU all the time to deliver the same text the guess already has ready at the end of the pause.

Measured end to end (real `Listener`, real-time audio):

| Scenario | Text ready after the pause ends |
|---|---|
| GPU, with guess | 0.00 s |
| GPU, no guess | 0.32 s |
| GPU busy (CPU) | 6.5 s |
| Before (CPU) | ~6.2 s |

## Consequences

- From end of speech to text: from ~6 s to ~0 s. What remains is `silence_ms` (1.8 s) and Claude's reply. Kokoro starts speaking in ~0.1 s.
- An image job never blocks the voice: Alfred falls back to the CPU and returns to the GPU when it frees up.
- **Accepted risk:** if Alfred just used the GPU (within `idle_s`) and a heavy image job starts loading, the job may OOM, and `imagens-local` is the one that retries. The ~470 MB of CUDA context stay while Alfred runs; `z-image-turbo` at 1536 px, which already worked at the limit, may not fit.
- Lowering `silence_ms` is the next latency gain, but it cuts off people who pause mid-sentence; it stays a user setting.
- Venv ~5 GB larger; the machine needs an NVIDIA driver with CUDA 12+.
