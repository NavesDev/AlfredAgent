# Stack

Alfred's technologies and the reason for each choice. Relevant changes become an [ADR](adr/).

## Overview

| Layer | Technology |
|---|---|
| Server runtime | Python 3.11+, asyncio, a single process |
| Package manager (Python) | uv + `pyproject.toml` |
| Agents | Claude Agent SDK (Python), using the logged-in `claude` CLI (Claude Code harness) |
| Models | Sonnet (default), Haiku (simple questions and fallback summaries) |
| Integrations | Gmail MCP, Google Calendar MCP, the SDK's native WebSearch/WebFetch |
| Internal tools | In-process MCP server (Python tools defined in the code itself) |
| Wake word | openWakeWord (trained `alfred.onnx` model) |
| VAD | Silero VAD |
| STT | faster-whisper `large-v3-turbo`, `int8_float16` on the GPU on demand, `int8` on the CPU ([ADR 0010](adr/0010-voice-models-on-demand-gpu.md)) |
| TTS | Kokoro (`pf_dora` or `pm_alex`), GPU on demand or CPU |
| Audio I/O | sounddevice (PortAudio) |
| Fuzzy match | rapidfuzz |
| Persistence | SQLite |
| API | FastAPI + Uvicorn, native WebSocket |
| Front end | React + TypeScript + Vite |
| UI | Tailwind CSS; Alfred's orb: Strands (React Bits, WebGL2) with a CSS version |
| Server state on the front end | TanStack Query |
| Typed client | openapi-typescript + openapi-fetch (types generated from FastAPI's OpenAPI) |
| Routing | React Router |
| Tests | pytest + pytest-asyncio (server), Vitest + Testing Library (web) |
| Lint/format | ruff + mypy (server), oxlint + tsc + Prettier (web), clippy + rustfmt (desktop) |
| Package manager (Node) | pnpm |
| Desktop | Tauri v2 (WebKitGTK on Linux), loading `apps/web` ([ADR 0012](adr/0012-desktop-shell-tauri.md)) |

## Server

**Python 3.11+ with asyncio.** The local voice ecosystem (faster-whisper, Kokoro, openWakeWord, Silero) is Python, and the Agent SDK has a first-class Python SDK. A single process keeps the MVP simple: the event bus lives in memory and there is no IPC.

**Threads for audio.** Capture, STT and TTS are CPU/GPU-bound or blocking. They run in their own threads and talk to the loop through `asyncio.Queue` / `loop.call_soon_threadsafe`, so they never block the agents.

**Claude Agent SDK.** Provides sessions with resume, `canUseTool` for the permission gate, auto mode, WebSearch/WebFetch and MCP servers (external and in-process). Each named session is an SDK instance with `cwd` in its workspace.

**SQLite.** One user, one machine, few writes. No database server to maintain.

**FastAPI.** Native async (the same loop as everything else), built-in WebSocket and automatic OpenAPI, which feeds the front-end types.

**rapidfuzz.** Whisper gets proper names wrong ("backend" → "bequi end"). Aliases + fuzzy match with a ~85% cutoff solve it without calling a model.

## Voice

| Component | Approx. RAM | When it weighs |
|---|---|---|
| openWakeWord + Silero | ~150 MB | Always on, near-zero CPU |
| faster-whisper large-v3-turbo | ~1.1 GB of VRAM (`int8_float16`), ~2 GB of RAM on the CPU fallback | From the wake word until 30 s after the last command |
| Kokoro | ~350 MB of VRAM or ~400 MB of RAM | Until 10 s after the last speech |
| CUDA contexts | ~470 MB of VRAM | While Alfred runs |
| Claude Code sessions (3) | ~0.5–1 GB | While running tasks |

- **faster-whisper `large-v3-turbo` int8:** best quality/speed trade-off in Portuguese. An `initial_prompt` with the jargon (Spring, Liferay, endpoint, worktree, commit, session names) improves technical terms. If the machine gets tight, switching to `medium` is one config line.
- **Kokoro:** light local TTS with Portuguese voices. 8 s of speech in 0.14 s on the GPU, 2.3 s on the CPU.
- **GPU on demand:** the GPU is shared with the image service. Whisper and Kokoro load when used, release the VRAM when idle and fall back to the CPU if it is busy ([ADR 0010](adr/0010-voice-models-on-demand-gpu.md)). torch comes from the `cu126` index, whose `nvidia-*` wheels (cuBLAS, cuDNN 9) also serve CTranslate2.
- **openWakeWord:** lets us train our own wake word ("Alfred") and runs on the CPU at near-zero cost.

## Web

- **Vite + React + TS:** fast dev server, static build served by FastAPI in production (single port).
- **TanStack Query:** all server state; the WebSocket only updates the cache. No Redux/Zustand.
- **openapi-typescript + openapi-fetch:** `api/schema.ts` generated from FastAPI; one contract between server and front end, no hand-duplicated types.
- **Tailwind:** components live in the repo, with no closed UI library dependency.
- **Strands (React Bits):** Alfred's orb, copied into the repo (MIT + Commons Clause). Plain WebGL2, no three.js; where WebGL2 is missing, the CSS version takes over. Visual direction in [DESIGN.md](DESIGN.md).

## Minimum versions

| Tool | Version |
|---|---|
| Python | 3.11 |
| Node.js | 20 LTS |
| pnpm | 9 |
| Git | 2.40 |
| NVIDIA driver (optional) | CUDA 12+ |

## Configuration

A single `server/config.yaml` file (versioned only as `config.example.yaml`). Main points:

```yaml
whisper:
  model: large-v3-turbo
  device: cuda          # cuda | cpu; CPU fallback while the GPU is busy
  compute_type: int8_float16
  language: pt
  initial_prompt: "Spring, Liferay, endpoint, worktree, commit, backend, frontend"
  idle_s: 30            # releases the GPU after this long unused

kokoro:
  voice: pf_dora        # or pm_alex
  speed: 1.1
  device: cuda
  idle_s: 10

wakeword:
  name: Alfred
  model: wakeword/alfred.onnx  # trained in wakeword/train
  threshold: 0.5
  aliases: [alfred, alfredo]

limits:
  max_active_sessions: 3

permissions:
  default_confirmation: voice      # voice | key | web | voice+key
  per_action:
    git_push: key
    send_email: voice+key
    delete_file: voice
    install_dependency: voice
  tainted_turn: key
  timeout_s: 60                    # no answer = denied
```

Claude authentication comes from the Claude Code login. Secrets (Google credentials, an API key if that ever changes) live in environment variables / `.env`, never in the YAML.
