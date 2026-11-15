# Phase 1 — End-to-end voice (design)

- **Date:** 2026-10-01
- **Status:** Approved
- **Requirements covered:** RF-01, RF-02, RF-03, RF-04, RF-13, RF-20, RF-28; RNF-01, RNF-05, RNF-08, RNF-09 (partial: events + `/ws`)

## Goal

Talk to Alfred and hear the answer: wake word → recording → Whisper → main agent (Claude through the Claude Code harness) → Kokoro reading only the `RESUMO:`. At the same time, publish real-time events on a `/ws` so the front end can animate states from day one.

## Decisions

| Topic | Decision |
|---|---|
| Wake word | `alfred.onnx` trained on the machine itself (`server/wakeword/train/`, results in its README). A voice verifier waits for phase 7 |
| Claude authentication | `claude-agent-sdk` using the already logged-in `claude` CLI (subscription). No `ANTHROPIC_API_KEY` |
| Conversation rhythm | Every utterance starts with the wake word; no follow-up window |
| Pipeline | One asyncio process; capture, STT and TTS in threads; in-memory event bus |
| Front end | No panel; a minimal `GET /ws` dumping the bus as JSON |
| Outside this phase | SQLite, "para" interruption, barge-in, agent tools (web/mail), Haiku fallback, panel |

## Components

All in `server/`.

| File | Responsibility | Depends on |
|---|---|---|
| `errors.py` | `AlfredError` hierarchy → `ConfigError`, `DependencyError`, `AudioError`, `AgentError` (see [ARCHITECTURE.md](../../ARCHITECTURE.md#errors)) | — |
| `main.py` | Loads the config, creates the bus, starts the audio threads, the agent and Uvicorn on the same loop | everything |
| `config.py` | Pydantic model of `config.yaml`; `load_config(path) -> Config` | pydantic, pyyaml |
| `events.py` | `EventBus`: `publish(type, **data)` (safe from any thread), `subscribe() -> asyncio.Queue`, `unsubscribe(q)` | asyncio |
| `controllers/router.py` | `Router.handle(text, source)`: in phase 1 hands everything to the agent and sends the summary to the talker | events, infra |
| `infra/audio/listener.py` | Thread: 16 kHz mono microphone, 80 ms frames → openWakeWord → records with Silero VAD until 800 ms of silence (max 15 s) → faster-whisper → `on_transcript(text)` callback | openwakeword, faster-whisper, sounddevice |
| `infra/audio/talker.py` | Thread: consumes a sentence queue → Kokoro (`lang_code='p'`, voice/speed from the config) → plays. Exposes `say(text)` and `is_speaking` | kokoro, sounddevice |
| `infra/claude/alfred.py` | `AlfredAgent.ask(text) -> Reply`: `ClaudeSDKClient`, Sonnet, no tools, pt-BR system prompt requiring `RESUMO:`; the stream becomes `agent_progress` | claude-agent-sdk, events, state |
| `infra/claude/summary.py` | `extract_summary(text) -> str`: the `RESUMO:` line; otherwise the first sentence; strips markdown/code | — |
| `infra/claude/state.py` | Reads/writes `data/alfred_state.json` `{date, claude_session_id}`; a new day = a new session | — |
| `api/app.py` | FastAPI: `GET /health`, mounts `ws.py` | fastapi |
| `api/ws.py` | `GET /ws`: subscribes to the bus and sends each event as JSON | events |
| `wakeword/train/` | Script that builds `wakeword/alfred.onnx` (Piper pt-BR and en samples, "Alfred"/"Alfredo" phrases) with the openWakeWord training pipeline | openwakeword, piper |

The layers follow [ARCHITECTURE.md](../../ARCHITECTURE.md): `infra` never imports `controllers`; `router` wires listener → agent → talker.

## Events

Wire format: `{"type": str, "ts": float, ...data}`.

| `type` | Data | When |
|---|---|---|
| `voice_state` | `state`: `idle`, `listening`, `transcribing`, `thinking`, `speaking` | Each transition |
| `audio_level` | `source`: `mic` or `tts`; `level`: 0–1 (normalized RMS); `bands`: 9 bands from 100 Hz to 5 kHz, 0–1 | ~15×/s in `listening` and `speaking` |
| `transcript` | `text`, `source`: `voice` | Whisper finished with non-empty text |
| `agent_progress` | `session`: `alfred`; `kind`: `text` or `tool`; `content` | Each SDK stream block |
| `alfred_reply` | `session`, `text`, `summary` | Final reply |
| `error` | `where`, `message` | Handled failure |

## Flow

1. `idle`: the listener feeds openWakeWord; score ≥ threshold → `listening`.
2. Records until 800 ms of VAD silence or 15 s; publishes the mic's `audio_level`.
3. `transcribing`: faster-whisper (`language=pt`, `initial_prompt` from the config). Empty text → `idle`.
4. `transcript` → `Router.handle`.
5. `thinking`: `AlfredAgent.ask` streams (`agent_progress`) until the result.
6. `alfred_reply` → `talker.say(summary)` → `speaking` → `idle`.

Capture and STT share the listener thread: they are sequential, and the microphone is ignored while the command is processed. While `talker.is_speaking`, the listener drops wake word detections (avoids self-triggering). Barge-in is phase 5.

## Latency (2nd iteration)

Measured on the first real use: ~16 s between the end of speech and the start of the answer (VAD 0.8 s + Whisper ~6 s + Claude ~9 s + TTS ~0.5 s).

| Change | How |
|---|---|
| Speak while the reply arrives | The prompt asks for `RESUMO:` on the **first** line; `include_partial_messages` streams; `on_summary` hands the line to the talker as soon as it closes. If it never comes, `extract_summary` runs at the end |
| Measured result | Sentence spoken in 4.0 s on the first question and 1.5 s on the next (before ~9 s), not counting Whisper |
| Claude always open | `ClaudeSDKClient` connected at startup (also validates the login: fail-fast); reopened when the day turns, after an error or a timeout |
| Chimes | The listener calls `chime("start")` when the wake word fires and `chime("end")` when recording stops; tones generated with numpy, played straight to the speaker, outside the speech queue |
| Transcribe while speaking | **Dropped for now.** Measured: `chunk_length` 30, 10 and 6 all take the same 6.2 s for 5 s of speech, because CTranslate2 pads the window to 30 s before the encoder. Chunks would multiply the cost. Real ways out: a smaller model (`small` ~1.5 s, gets jargon wrong), another STT engine, or a GPU |

## Agent's daily session

- On connect, if `state.date == today`, it resumes with `resume=claude_session_id`. The client stays open; when the day turns, it reconnects without `resume`.
- Otherwise it opens a new session and stores the new `claude_session_id` with today's date.
- "Day" uses the machine's local time zone, turning at midnight. A conversation in progress at the turn stays in the session where it started.

## Error handling

Layered exceptions and fail-fast as in [ARCHITECTURE.md](../../ARCHITECTURE.md#errors). Models load at startup.

| Situation | Behavior |
|---|---|
| Empty transcript/noise | Back to `idle` without speaking |
| SDK/CLI fails or takes over 60 s | Publishes `error`, says "Não consegui falar com o Claude agora", back to `idle` |
| `claude` CLI missing or logged out | Clear error at startup, the process exits |
| Microphone unavailable | Clear error at startup, the process exits |
| Exception inside an audio thread | Logs, publishes `error`, state `idle`, the thread keeps going |
| Resume with an invalid `claude_session_id` | Discards it, opens a new session, stores the new id |

## Configuration (additions)

```yaml
wakeword:
  model: hey_jarvis          # pretrained name or path to an .onnx
  threshold: 0.5

listener:
  sample_rate: 16000
  silence_ms: 800
  max_record_s: 15

agents:
  default_model: sonnet
  timeout_s: 60

storage:
  state_path: data/alfred_state.json
```

## Tests

Unit tests (pytest + pytest-asyncio), no hardware or network:

- `events`: a publish from another thread reaches the subscriber; unsubscribe stops delivery.
- `summary`: with `RESUMO:`, without `RESUMO:`, with a code block, empty reply.
- `config`: loads `config.example.yaml`; clear error on an invalid field.
- `state`: same day resumes the id; a new day makes a new session; missing file.
- `listener`: state machine with injected fake wake word, VAD and Whisper (frame sequence → transitions and `transcript`).
- `alfred`: a fake SDK client emitting a stream → `agent_progress` + `Reply` with the summary; timeout → error.
- `router`: transcript → fake agent → fake talker gets the summary.
- `ws`: TestClient connects and receives a published event.

Manual smoke test: "Hey Jarvis, qual a diferença entre JWT e sessão?" → spoken answer in 1–2 sentences; `websocat ws://localhost:8000/ws` shows the event sequence.

## Setup

- `uv` (Python manager).
- System: `libportaudio2`, `espeak-ng`.
- Python: `claude-agent-sdk`, `faster-whisper`, `kokoro`, `openwakeword`, `sounddevice`, `numpy`, `pydantic`, `pyyaml`, `fastapi`, `uvicorn`; dev: `pytest`, `pytest-asyncio`, `httpx`, `ruff`, `mypy`.
- Whisper on the CPU (machine without an NVIDIA GPU): `device: cpu`, `compute_type: int8`.

## Risks

- **Terms of use:** using the Claude subscription through the Agent SDK in a personal project is a gray area; if it becomes a problem, switching to `ANTHROPIC_API_KEY` is only an environment setting.
- **CPU latency:** large-v3-turbo int8 on 12 cores should take ~1–3 s per short command; beyond that, `medium` or `small`.
- **Wake word:** trained only with synthetic voices; it gets ~50% of synthetic pt-BR phrases right. Validate with a real voice and, if needed, retrain with the user's recordings.
- **Pronunciation:** Kokoro in pt-BR depends on `espeak-ng`; check it in the smoke test.
