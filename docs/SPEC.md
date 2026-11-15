# Spec — Voice Agent Manager (Claude Code)

Sep 30, 2026 · @Naves

> Original product spec. Traceable requirements in [REQUIREMENTS.md](REQUIREMENTS.md); technical view in [ARCHITECTURE.md](ARCHITECTURE.md). Spoken examples stay in Brazilian Portuguese, the language Alfred listens to.

## Overview

Alfred is a personal voice assistant built for a developer's routine. It answers questions, searches the web, reads mail and calendar, manages tasks and runs several Claude Code sessions in parallel, each with its own name and tied to a project and worktree. You say "Alfred, backend: cria o endpoint de cancelamento" or just "Alfred, tenho e-mail importante hoje?" and it handles it, then answers out loud.

Goals:

- Hands-free: continuous listening with a wake word, no keyboard.
- One entry point: the same "Alfred" serves daily life and code.
- 100% local voice (Whisper + Kokoro); reasoning and integrations run in the cloud.
- Projects, worktrees, named sessions and tasks that are easy to call by voice.
- Light enough to run next to the dev environments (target: ≤ 3 GB of RAM in total).

## Architecture and stack

Speech goes down the local chain to the router. System commands are resolved right there; the rest goes to the main agent or to a named session, which talk to Claude in the cloud and return only the summary line for Kokoro to speak.

## Alfred, the main agent

Besides the code sessions there is a fixed session called `alfred`: the main agent. It gets everything that is neither a system command nor a task addressed to a named session. It is not tied to any repository; its job is to answer, search and coordinate.

| Capability | How it works |
|---|---|
| Answer questions | Direct model answer, short and speakable |
| Search the web | WebSearch and WebFetch tools, native to the Agent SDK |
| Mail and calendar | Gmail and Google Calendar MCP servers: list, summarize, search, draft |
| Tasks | Internal tools: create, list, complete and prioritize tasks per project |
| Projects and sessions | Internal tools: list projects, create a worktree, open a session, see status |
| Delegate code | `delegar(sessao, tarefa)` tool: sends the work to a named session and reports when it is done |

The internal tools are an in-process MCP server (the Agent SDK takes Python tools defined right in the code) that exposes the orchestrator itself to Alfred. That lets it chain flows like "take Recurve's most urgent task and send it to the backend" without you talking to each piece.

Main agent rules:

- Never edits code directly; repository work always goes to a named session through `delegar`.
- Knows the focused session and the current project, so "roda os testes" with no name becomes `delegar(focus, ...)`.
- Model: Sonnet by default to stay fast; very simple questions may go to Haiku.
- Context: keeps the day's history in the same session and starts a new one every day, so it does not grow forever.

## Data model

Three entities in SQLite: Project → Workspace → Session. The project only groups things; the workspace is a folder (with or without git) or a worktree created from another workspace. The UI and the voice call a workspace "ambiente". The session is what you call by voice; its name is the command's "address".

| Entity | Main fields | Example |
|---|---|---|
| Project | id, name, aliases[], description | Recurve · aliases: "recurve", "billing" · "Recurring billing SaaS" |
| Workspace | id, project_id, name, path, kind (folder or worktree), parent_id, branch, description | "back" · ~/dev/recurve-api · folder · "Spring Boot API"; "cancelamento" · ~/dev/recurve-api-wt/cancelamento · worktree of back |
| Session | id, name, aliases, kind (geral or implementacao), workspace_id, model, effort, claude_session_id | "backend" · implementacao · workspace back · opus |
| Task | id, project_id (optional), title, status, priority, session_id (optional), created_at | "Implementar reembolso" · Recurve · high · in_progress on the backend session |

Rules:

- A session name is unique across the whole system, so you never have to say the project.
- Aliases exist because Whisper sometimes transcribes "backend" as "bequi end"; matching uses aliases + fuzzy match (rapidfuzz, ~85% cutoff).
- An English name inside a Portuguese command is the hardest case. Three defenses, in this order: Whisper gets the current names as `hotwords`; a session or project alias found in the transcript becomes the real name; and the command reaches Alfred with a "Known names" line so it picks the closest-sounding name, or asks.
- Projects and workspaces have an optional short description (up to 200 characters), editable on the panel and by voice. Alfred reads the descriptions when listing projects, to know what each one is about and pick the right workspace.
- A project can have several workspaces (e.g. one for the back end and one for the front end). Registering a folder does not require git.
- Creating a worktree runs `git worktree add <parent>-wt/<name> -b <name>` from the parent workspace; removing runs `git worktree remove` and refuses when there are uncommitted changes (unless forced). Removing a plain folder workspace only unregisters it.
- Model and effort come from the settings screen per agent kind; each session can override them.
- The `implementacao` kind uses the full Claude Code harness: CLAUDE.md, skills, plugins, hooks and MCPs ([ADR 0008](adr/0008-implementation-agent-full-harness.md)).
- On the settings screen, the MCPs of those sessions turn on and off one by one or all at once ("Desligar todos" / "Ligar todos").
- Each session gets a 3D portrait generated in the background by the image generator among the user's MCPs; until it exists (or if generation fails), the panel shows the monogram. On the settings screen, "Gerador de imagens" picks the favorite MCP or "Automático" ([ADR 0009](adr/0009-session-portraits-via-mcp.md)).
- `claude_session_id` keeps the Agent SDK id to resume the conversation after the assistant restarts.
- Session status: idle, busy, waiting for permission, error. Task status: open, in progress, done; a task with no project covers personal things ("pagar boleto"), and a delegated task becomes done by itself when the session finishes.

## Voice commands and routing

Every command starts with the wake word. The router first tries the system commands (regex/fixed grammar, no tokens spent); whatever does not match goes to a named session or to the main agent.

| Speech | What happens |
|---|---|
| "Alfred, backend: roda os testes do billing" | Sent straight to the "backend" session |
| "Alfred, roda os testes" | The main agent delegates to the focused session |
| "Alfred, tenho e-mail importante hoje?" | Lists and summarizes unread mail |
| "Alfred, o que tenho na agenda amanhã?" | Reads the Google Calendar events |
| "Alfred, pesquisa como configurar virtual threads no Spring Boot" | Searches the web and answers in 2 sentences |
| "Alfred, qual a diferença entre JWT e sessão?" | Answers directly |
| "Alfred, anota tarefa no Recurve: implementar reembolso" | Creates the task in the project |
| "Alfred, quais tarefas tenho abertas?" | Lists by project and priority |
| "Alfred, manda o backend fazer a tarefa de reembolso" | Delegates and marks the task in progress |
| "Alfred, foca no frontend" | Switches the focused session |
| "Alfred, status" | Reads the status of every session in one sentence |
| "Alfred, backend, o que você fez?" | Reads the session's last summary |
| "Alfred, nova sessão testes no Recurve, worktree cancelamento" | Creates the worktree (if missing) + the "testes" session |
| "Alfred, cria worktree cancelamento no Recurve" | `git worktree add` + registers the workspace |
| "Alfred, lista projetos" / "lista sessões" | Reads the registered names |
| "Alfred, backend, para" | Interrupts the session's run |
| "Alfred, fecha a sessão testes" | Closes the session (keeps the history) |

How routing works:

1. Interruptions match by regex and act in milliseconds, even while Alfred is busy: "para" silences the speech and cancels Alfred, "<session>, para" interrupts that session, "para tudo" interrupts all of them.
2. Explicit shortcut: a sentence starting with `<name>:` or `<name>,` of a known session (aliases + fuzzy match) goes straight to it, skipping Alfred.
3. Everything else goes to the main agent `alfred`, which decides: answers, searches, handles mail, calendar and tasks, or delegates to a code session. Natural sentences such as "pede pro backend rodar os testes" also land here.
4. A task for a busy session goes into its queue and Alfred says "backend tá ocupado, coloquei na fila".

## Permissions, notifications and spoken replies

**Permissions.** Code sessions run in Claude Code's auto mode, which blocks most dangerous actions on its own; no sandbox for now. On top of that, `permissions.py` does three things through `canUseTool`:

- Minimal denylist, always denied: `sudo`, `rm -rf` outside the worktree, writes outside the workspace.
- Sensitive actions (push, deleting a file, installing a dependency, sending mail, changing the calendar) ask for confirmation on the configured channel.
- Tainted turn: if Alfred read mail or the web during the turn, any action with side effects needs confirmation, against prompt injection.

The main agent has no Bash or Edit: whoever reads external content never runs commands. A session waiting for an answer has the waiting-for-permission status, and every tool call goes to an audit log.

The confirmation channel is configurable per action, because a spoken "yes" does not prove it was you:

```yaml
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

**Notifications.** Sessions run in the background. When one finishes, the orchestrator says "backend terminou: <summary>". If you are talking or other audio is playing, the notification waits in a speech queue instead of talking over it.

**Spoken replies.** Raw output is never read aloud. Each session's `system_prompt` asks it to **start** with a `RESUMO:` line of up to 2 sentences, with no code or long paths; the TTS reads only that line, as soon as it arrives in the stream, without waiting for the rest of the reply. If the line is missing, Haiku writes the summary as a fallback.

**Mail and calendar.** Reading runs right away. Sending, replying or changing an event follows the configured confirmation, with Alfred reading the recipient and a summary first ("vou responder o João dizendo que topa sexta, posso?"). Mail is always read as a summary, never in full.

**Barge-in.** Saying the wake word while Kokoro is speaking cuts the audio at once.

## Layout, config and resources

Monorepo with `server/` at the root and the interfaces in `apps/`; everything in the repo is in English. The server is Python 3.11+, a single asyncio process running the voice loop and the API; audio, STT and TTS live in their own threads so they never block the agents' loop.

The full folder tree is in [ARCHITECTURE.md](ARCHITECTURE.md#folder-structure).

**Server.** `models` holds data and SQLite and knows nothing about voice or Claude; `controllers` holds the decision logic and is the only place that joins models with infra; `infra` talks to the outside world (microphone, speaker, Claude, git); `api` exposes everything to the panel. No interfaces or extra layers: swapping Whisper or Kokoro only touches `listener.py` or `talker.py`.

**Event bus.** Controllers publish events (`transcript`, `session_status`, `task_updated`, `permission_request`, `alfred_reply`) on `events.py`, and the talker and `ws.py` consume them. Voice and screen stay in parity without duplicated logic, and a `permission_request` can be answered by speaking or by clicking on the panel (`POST /api/confirmations/{id}`).

**Web (`apps/web`).** React + TypeScript + Vite, Tailwind, TanStack Query (the WebSocket updates the cache), openapi-typescript + openapi-fetch for types generated from FastAPI, React Router and Vitest. In dev, Vite runs separately with a proxy; in production FastAPI serves `dist/` on a single port. It opens on localhost or on the phone over the local network.

`src/` is organized by feature, and every feature repeats the same skeleton (`pages/`, `components/`, `hooks/`, only what it needs).

Front-end rules:

- All API access lives in the feature hooks (TanStack Query queries and mutations); components only call the hook and render.
- A feature imports from the global `api/`, `components/`, `hooks/` and `lib/`, never from another feature. The exception is the dashboard, which exists to bring the others together.
- A component used by two features moves up to `components/`; a type specific to one feature becomes `types.ts` at its root.
- No global state manager: server state in TanStack Query, the rest in `useState`.
- Screens: `/` (dashboard: sessions, pending confirmations, live conversation and open tasks), `/projects`, `/projects/:id`, `/tasks` and `/activity`.
- The CommandBar sends text to the same router as the voice (`POST /api/commands`), to use Alfred by typing when speaking is not an option.

**Desktop (`apps/desktop`).** Tauri v2 wraps the same `apps/web` ([ADR 0012](adr/0012-desktop-shell-tauri.md)): undecorated window with its own title bar, closing hides it in the tray, and a floating voice visualizer (mini orb + bars) shows at the bottom center of the screen when Alfred listens, thinks or speaks while the app is minimized or in the tray. A global shortcut and native notifications come later.

Key points of `config.yaml`:

- whisper: `model: large-v3-turbo`, `device: cuda|cpu`, `compute_type: int8_float16`, `language: pt`, `initial_prompt` with your jargon (Spring, Liferay, endpoint, worktree, commit, session names).
- kokoro: `voice: pf_dora` (or `pm_alex`), `speed: 1.1`.
- wakeword: name Alfred, model `alfred.onnx` trained with openWakeWord, threshold 0.65, aliases alfred and alfredo. It is configurable: changing the name means pointing to another trained model.
- limites: `max_sessoes_ativas: 3`, `timeout_permissao_s: 60` (original keys; see open questions 1 and 2 in [REQUIREMENTS.md](REQUIREMENTS.md#open-questions)).

| Component | Approx. RAM | When it weighs |
|---|---|---|
| openWakeWord + Silero | ~150 MB | Always on, near-zero CPU |
| faster-whisper large-v3-turbo | ~1.1 GB of VRAM (or ~2 GB of RAM on the CPU) | From the wake word until 30 s after the command |
| Kokoro | ~400 MB | Only while speaking |
| Claude Code sessions (3) | ~0.5–1 GB | While running tasks |

Whisper and Kokoro use the GPU on demand and fall back to the CPU when it is busy ([ADR 0010](adr/0010-voice-models-on-demand-gpu.md)). If the machine gets tight, switching to medium is a one-line change.

## MVP roadmap

Each phase delivers something usable on its own:

1. End-to-end voice: wake word → Whisper → main agent → Kokoro reading the `RESUMO:`.
2. General assistant: questions, web, Gmail and Google Calendar in the main agent.
3. Named sessions: SQLite, several code sessions, routing, focus, status, per-session queue.
4. Projects, worktrees and tasks: registration by voice, `git worktree add/remove`, tasks per project, delegation and resume after a restart.
5. Permissions: configurable confirmation, denylist, tainted turn, barge-in, notification queue.
6. Web panel: `apps/web` with sessions, tasks, log and confirmation by click.
7. Polish: trained Alfred wake word, `initial_prompt` tuning, Haiku fallback.

Out of scope for the MVP: session sandboxing, access over the internet, multiple users and voice-cloning TTS.
