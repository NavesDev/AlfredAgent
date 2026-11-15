# 0002 — Server in one asyncio process with an in-memory event bus

- **Status:** Accepted
- **Date:** 2026-10-01

## Context

Voice, agents, API and WebSocket need to share state (sessions, focus, speech queue, pending confirmations). It is a one-user, one-machine system.

## Decision

One Python process with asyncio runs the agents' loop and FastAPI. Audio, STT and TTS run in their own threads. Events flow through an in-memory pub/sub (`events.py`) consumed by `talker` and `ws.py`.

## Consequences

- No IPC, broker or serialization between services.
- Voice and panel stay in parity naturally.
- A process crash takes everything down; SQLite persistence and the Agent SDK's resume cover the restart.
- Scaling to multiple users would require revisiting this decision (out of the MVP's scope).
