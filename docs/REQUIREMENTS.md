# Requirements

Derived from [SPEC.md](SPEC.md). On conflict, the spec wins until this document is updated.

Conventions: **RF** = functional requirement, **RNF** = non-functional, **RN** = business rule. Each item names the roadmap phase (F1–F7) it lands in.

## Glossary

| Term | Meaning |
|---|---|
| Wake word | Word that turns listening on ("Alfred", alias "Alfredo") |
| Main agent | Fixed `alfred` session: answers, searches, coordinates. Never edits code |
| Named session | Claude Code session tied to a workspace; its name is the command's "address" |
| Project | Groups workspaces and sessions (name + aliases) |
| Workspace | A project folder (with or without git) or a `git worktree` created from another one. Called "ambiente" in the UI and by voice |
| Focused session | Session that gets code commands with no explicit name |
| `RESUMO:` line | Line that opens each reply, up to 2 sentences, the only one read aloud |
| Tainted turn | Turn in which the agent read external content (mail, web) |
| System command | Command the router resolves by regex, without calling a model |

## Functional requirements

### Voice

| ID | Requirement | Phase |
|---|---|---|
| RF-01 | Listen continuously and wake on the configurable wake word (`alfred.onnx`, trained with `server/wakeword/train/`) | F1 |
| RF-02 | Detect end of speech with VAD and transcribe locally with Whisper (pt, `initial_prompt` with jargon, `hotwords` with the current session and project names and aliases) | F1 |
| RF-03 | Speak replies with Kokoro (configurable voice and speed) | F1 |
| RF-04 | Read aloud only the `RESUMO:` line, which opens the reply and is spoken as soon as it arrives (streaming); never raw output, code or long paths | F1 |
| RF-05 | If the reply has no `RESUMO:`, write a summary with Haiku | F7 |
| RF-06 | Barge-in: the wake word during speech cuts the audio immediately | F5 |
| RF-07 | Speech queue: notifications never talk over the user or other audio; a session notice that arrives during an Alfred turn waits for the turn to end, and each notice opens with the session name ("Recurve terminou: …") | F5 |
| RF-08 | Short chime when the wake word fires and another when recording stops | F1 |

### Routing

| ID | Requirement | Phase |
|---|---|---|
| RF-10 | Regex interruptions, even while Alfred is busy: "para" (silences and cancels Alfred), "<session>, para", "para tudo" | F3 |
| RF-11 | Explicit shortcut: a sentence starting with `<name>:` or `<name>,` of a known session goes straight to that session | F3 |
| RF-12 | Name resolution by aliases + fuzzy match (rapidfuzz, ~85% cutoff). Sessions and projects have spoken aliases; an alias in the transcript becomes the real name before reaching Alfred, and each command carries the list of known names so Alfred can fix a mistranscribed name | F3 |
| RF-13 | Everything else goes to the main agent | F1 |
| RF-14 | A command for a busy session goes into the session's queue and Alfred says so ("backend tá ocupado, coloquei na fila") | F3 |
| RF-15 | Commands typed on the panel (`POST /api/commands`) go through the same router as the voice | F6 |

### Main agent

| ID | Requirement | Phase |
|---|---|---|
| RF-20 | Answer questions briefly and in a speakable way | F1 |
| RF-21 | Search the web with the Agent SDK's WebSearch/WebFetch | F2 |
| RF-22 | Read, summarize, search and draft mail (Gmail MCP) | F2 |
| RF-23 | Read and query events (Google Calendar MCP) | F2 |
| RF-24 | Send/reply to mail and change events only after confirmation, reading the recipient and a summary first | F5 |
| RF-25 | Expose the orchestrator through internal tools (in-process MCP): projects, sessions, worktrees, tasks, `delegar` | F3–F4 |
| RF-26 | `delegar(sessao, tarefa)`: sends work to a named session and reports when it is done | F3 |
| RF-27 | A code command with no session name becomes `delegar(focus, ...)` | F3 |
| RF-28 | One conversation per day: the day's history in the same session, a new session every day | F1 |
| RF-29 | Read, list and search home files (except secret files) and a workspace's git state, to answer questions and checks without delegating, plus the GitHub issues of a workspace's repo ([ADR 0011](adr/0011-main-agent-local-read.md)) | F4 |

### Sessions, projects and tasks

| ID | Requirement | Phase |
|---|---|---|
| RF-30 | Create, list, focus, check status of and close named sessions by voice | F3 |
| RF-31 | Read the status of every session in one sentence ("Alfred, status") | F3 |
| RF-32 | Read a session's last summary ("backend, o que você fez?") | F3 |
| RF-33 | Interrupt one session's run or all of them | F3 |
| RF-34 | Register and list projects with aliases | F4 |
| RF-34a | Projects, workspaces and sessions have a short description, editable on the panel and by voice; it is Alfred's context to decide where to delegate | F4 |
| RF-35 | Create a worktree (`git worktree add <path> -b <branch>`) and register the workspace; remove it with `git worktree remove` | F4 |
| RF-36 | "Nova sessão X no projeto Y, worktree Z" creates the worktree if missing and the session | F4 |
| RF-36a | A project has a default workspace; a workspace has an implementation mode (`worktree` or `ambiente`), with a global default. The mode guides Alfred, which decides whether to create a worktree and the branch name (repo conventions, issue) and creates the worktree, workspace and session without asking | F4 |
| RF-36b | Workspaces mirror git worktrees: one created outside becomes a workspace; one removed outside deletes the workspace and its sessions | F4 |
| RF-37 | Resume sessions after the assistant restarts through `claude_session_id` (resume) | F4 |
| RF-38 | Create, list, complete and prioritize tasks, with or without a project | F4 |
| RF-39 | Delegating a task marks it `in_progress`; when the session finishes, it becomes `done` automatically | F4 |
| RF-40 | When it finishes, the session notifies by voice: "backend terminou: <summary>" | F3 |

### Permissions and audit

| ID | Requirement | Phase |
|---|---|---|
| RF-50 | Always-denied denylist: `sudo`, `rm -rf` outside the worktree, writes outside the workspace | F5 |
| RF-51 | Sensitive actions (push, deleting a file, installing a dependency, sending mail, changing the calendar) ask for confirmation | F5 |
| RF-52 | Confirmation channel configurable per action: `voice`, `key`, `web`, `voice+key` | F5 |
| RF-53 | Tainted turn: any action with side effects needs confirmation | F5 |
| RF-54 | No answer within the timeout (60 s) = denied | F5 |
| RF-55 | A session waiting for confirmation has the `waiting_permission` status | F5 |
| RF-56 | Every tool call goes to an audit log | F5 |
| RF-57 | Confirmation answerable by voice or by clicking on the panel (`POST /api/confirmations/{id}`) | F6 |

### Web panel

| ID | Requirement | Phase |
|---|---|---|
| RF-60 | Dashboard (`/`): sessions, pending confirmations, live conversation, open tasks | F6 |
| RF-61 | Screens `/projects`, `/projects/:id`, `/tasks`, `/activity` | F6 |
| RF-62 | Real-time updates over WebSocket (bus events, including `voice_state` and `audio_level` with level and frequency bands for animations) | F1 (`/ws`), F6 (panel) |
| RF-63 | CommandBar (Ctrl+K) to talk to Alfred by typing | F6 |
| RF-64 | Reachable on localhost and from the phone on the local network | F6 |
| RF-65 | Desktop app (Tauri) with the panel's UI, its own title bar and a tray; closing hides it in the tray ([ADR 0012](adr/0012-desktop-shell-tauri.md)) | Desktop |
| RF-66 | Floating voice visualizer (mini orb + bars) while the voice is not idle and the app is minimized or in the tray; its position is a preset chosen in Settings (RF-74), it cannot be dragged, and clicks outside it pass through | Desktop |
| RF-67 | Check for a newer release tag at boot, every 6 hours and on request; show the version and its CHANGELOG notes on the panel ([ADR 0013](adr/0013-self-update-from-git-tags.md)) | Updates |
| RF-68 | "Atualizar" updates to that tag and restarts Alfred; refused when the checkout is not on a clean `main`; a failed install or build rolls back to the previous version | Updates |

### Results

| ID | Requirement | Phase |
|---|---|---|
| RF-69 | The "Alfred" name on the title bar uses Newsreader Display italic, bundled with the app; the app and tray icon is the real orb, round with a transparent background | Desktop |
| RF-70 | A session that finishes may record a result (files to show and/or a change report) with `APRESENTAR:` (show it) or `GUARDAR:` (keep it only) lines in its final reply; no lines, no result ([ADR 0014](adr/0014-results-presentation.md)) | Results |
| RF-71 | A change report is the reply text plus `git diff --numstat` between the task's starting `HEAD` and the tree at the end | Results |
| RF-72 | "Me mostra o que o X fez" shows the session's last result; Alfred also shows a file it found, as a card or straight in the expanded view when asked ("me apresenta"); "pode fechar" closes it | Results |
| RF-73 | With the panel out of sight the pill grows into a 300 px result card in its corner; with the panel in sight the card shows on the panel. The card shows image/GIF, muted looping video, report or document; "Ampliar" opens a centered expanded view with arrows between files; "Abrir no app" and "Pasta" open the file or its folder. Each session lists its last 30 results | Results |
| RF-74 | Everything that floats (pill, card, future notices) anchors to one position preset chosen in Settings: top or bottom, left, center or right; default top right | Desktop |

## Non-functional requirements

| ID | Requirement |
|---|---|
| RNF-01 | **Audio privacy:** capture, wake word, STT and TTS 100% local; audio never leaves the machine |
| RNF-02 | **Memory:** ≤ 3 GB of total RAM with 3 active sessions (Whisper on the GPU saves ~2 GB) |
| RNF-03 | **Interruption latency:** "para" commands act in milliseconds, without calling a model |
| RNF-04 | **Cost:** system commands spend no tokens; Sonnet by default, Haiku for simple questions and summaries |
| RNF-05 | **Concurrency:** one asyncio process; audio, STT and TTS in their own threads, never blocking the agents' loop |
| RNF-06 | **Security:** main agent without Bash/Edit — whoever reads external content never runs commands |
| RNF-07 | **Resilience:** a process restart loses no projects, sessions, tasks or conversations (SQLite + resume) |
| RNF-08 | **Replaceability:** swapping Whisper or Kokoro only touches `listener.py` or `talker.py`; changing the wake word means changing the model |
| RNF-09 | **Voice/screen parity:** every action and event available by voice shows on the panel and vice versa, through the event bus |
| RNF-10 | **Language:** interaction in pt-BR; everything in the repo in English |
| RNF-11 | **Network:** panel on the local network only; no internet access in the MVP |

## Business rules

| ID | Rule |
|---|---|
| RN-01 | A session name is unique across the whole system |
| RN-02 | There is always a fixed `alfred` session (main agent), not tied to a repository |
| RN-03 | The main agent never edits code; repository work always goes through `delegar` |
| RN-04 | A maximum number of `claude` processes open at once (default 3, editable on the settings screen). A session idle for `idle_minutes` closes its process and resumes the conversation on the next task; with no free slot, the task waits in a queue |
| RN-05 | Session status: `idle`, `busy`, `waiting_permission`, `error` |
| RN-06 | Task status: `open`, `in_progress`, `done`; priority `low`, `medium`, `high` |
| RN-07 | A task with no project is personal ("pagar boleto") |
| RN-08 | Closing a session ends its run but keeps the history |
| RN-09 | Mail is always read as a summary, never in full |
| RN-10 | Reading mail/calendar runs right away; writing needs confirmation |
| RN-11 | A workspace has `kind` `folder` (any folder) or `worktree` (with `parent_id` and `branch`) |
| RN-11a | Project and workspace descriptions are optional, 200 characters at most |
| RN-12 | Result files are served only to this computer (loopback). From another device the panel shows a result's title, summary and report text, never its media or files |
| RN-13 | A result file is shown only if Alfred could read it: inside the home, not a secret (ADR 0011), checked when recorded and again when served |

## Out of scope for the MVP

- Sandboxing code sessions
- Access over the internet
- Multiple users
- Voice-cloning TTS

## MVP roadmap

Each phase delivers something usable on its own.

| Phase | Delivery | Done when |
|---|---|---|
| F1 | End-to-end voice + trained `alfred.onnx` wake word + `/ws` events | "Alfred, qual a diferença entre JWT e sessão?" is answered out loud, only the `RESUMO:`; state events on `/ws` |
| F2 | General assistant | Web, Gmail and Calendar working by voice |
| F3 | Named sessions | 2+ sessions in parallel, `<name>:` shortcut, focus, status, queue, interruption |
| F4 | Projects, worktrees and tasks | Create a worktree + session by voice, delegate a task, resume after a restart |
| F5 | Permissions | Per-channel confirmation, denylist, tainted turn, barge-in, notification queue, audit |
| F6 | Web panel | Screens listed in RF-60/61, confirmation by click, CommandBar |
| F7 | Polish | Wake word refined with the user's recordings, optional verifier with the user's voice, tuned `initial_prompt`, Haiku fallback |

## Open questions

1. **Permission timeout duplicated in the spec:** `permissions.timeout_s` and `limits.timeout_permissao_s`. Proposal: keep only `permissions.timeout_s`.
2. **Config keys in Portuguese** (`limites`, `max_sessoes_ativas`) contradict "config in English". Proposal: `limits.max_active_sessions`.
3. **`key` channel:** which key/device? A global desktop shortcut may come with the Tauri app (ADR 0012). Proposal: a key in the server terminal or a button on the panel until then.
4. ~~**Per-session queue:** persisted in SQLite or in memory only?~~ Resolved: the queue lives in memory; projects, sessions and settings go to SQLite and the conversation comes back through resume.
5. **Daily rotation of the `alfred` conversation:** at what time does the day turn, and what happens to a conversation in progress?
6. **Panel authentication on the local network:** none in the MVP? Anyone on the LAN could approve confirmations through `web`.
7. The project's **license**.
8. **Subscription use through the Agent SDK:** phase 1 authenticates with the Claude Code login; confirm personal use is allowed by the terms, otherwise move to `ANTHROPIC_API_KEY`.
