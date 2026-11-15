# 0001 — Local voice, cloud reasoning

- **Status:** Accepted
- **Date:** 2026-10-01

## Context

Alfred listens continuously. Sending audio to the cloud exposes everything said near the microphone and adds latency and cost. On the other hand, running a capable LLM locally next to the dev environments blows the ≤ 3 GB RAM budget.

## Decision

Wake word (openWakeWord), VAD (Silero), STT (faster-whisper) and TTS (Kokoro) run 100% locally. Only transcribed text leaves the machine, to Claude and to the integrations (Gmail, Calendar, web).

## Consequences

- Audio never leaves the machine.
- Transcription quality depends on the local Whisper: mitigated with `initial_prompt`, aliases and fuzzy match.
- A ~2 GB RAM (or VRAM) peak during STT; `medium` as plan B.
