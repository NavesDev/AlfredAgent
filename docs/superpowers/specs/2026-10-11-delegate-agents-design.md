# Delegated agents: polymorphic kinds, lifecycle and on-screen cards (design)

- **Date:** 2026-10-11
- **Status:** Approved
- **Branch:** `feat/delegate-agents`
- **Requirements covered:** RF-26 (partial), RF-30 (partial: create, list, clear, delete), RF-40, RF-60 (partial: sessions on the dashboard); RN-01, RN-04, RN-05 (without `waiting_permission`)

## Goal

1. Replace the single `delegar` tool (tied to the `sistema` session, ADR 0006) with **polymorphic agent kinds**: each kind is a subclass of `AgentKind` that defines its Claude Code tools, its prompt and Alfred's own delegation tool. This branch has one kind, `geral`; the `implementacao` kind (a session tied to a project) is planned, with no code.
2. **Persistent** named sessions that the user creates, keeps, **clears** (resets the context, keeps the session) and **deletes** by voice.
3. A **card per session** on the panel, with kind, model, folder, status, current task, last activity, queue, task count, tokens and last summary, plus Clear and Delete buttons.

## Decisions

| Topic | Decision |
|---|---|
| Session model | Persistent per name (not one instance per task). Tasks for a busy session go into its queue |
| Polymorphism | Abstract base class `AgentKind`; each kind generates its `delegar_<kind>` tool. Management tools are generic |
| Kinds in this branch | Only `geral` (`GeneralAgent`). `ImplementationAgent` only in this document |
| `sistema` session | Kind `geral`, created at boot, always present. It can be cleared, not deleted |
| Several general sessions | `delegar_geral(tarefa, sessao?)`: `sessao` optional, default `sistema` |
| Clear | Cancels the running task, empties the queue and disconnects the client; the next task opens a new context. Task and token counters reset |
| Delete | Clear + remove the session from the screen and the registry |
| Limit | `limits.max_active_sessions` (default 3, RN-04) counts every existing session, including `sistema` |
| Persistence | Memory only. Restarting the server recreates only `sistema` (SQLite and resume come in F4) |
| Create from the screen | No. Create only by voice; the screen lists, clears and deletes |
| Delete by voice | Alfred confirms verbally before calling `apagar_sessao` (prompt rule) |
| Delete from the screen | Inline confirmation on the card (second click) |
| Security | Alfred still has no Bash/Edit/Write (ADR 0003). The new tools only touch the session registry |

## Server

### `infra/claude/agents.py` (new)

```python
class AgentKind(ABC):
    kind: str          # "geral" — registry key and tool suffix
    label: str         # "Geral" — shown on screen and spoken
    tools: list[str]   # the session's Claude Code tools

    @abstractmethod
    def prompt(self, name: str, cwd: Path) -> str: ...

    @abstractmethod
    def delegate_tool(self, delegate: Delegate) -> sdk.SdkMcpTool[Any]: ...


class GeneralAgent(AgentKind):
    kind, label = "geral", "Geral"
    tools = ["Bash", "Read", "Edit", "Write", "Glob", "Grep"]
    # prompt: the current SYSTEM_PROMPT from session.py
    # delegate_tool: "delegar_geral", {"tarefa": str, "sessao": str (optional)}


KINDS: dict[str, AgentKind] = {k.kind: k for k in (GeneralAgent(),)}
```

`Delegate = Callable[[str, str], str]` takes `(session_name, task)` and returns the sentence for Alfred to speak.

Future `ImplementationAgent` (outside this branch): `kind="implementacao"`, a required `cwd` pointing at the project, a `delegar_implementacao(sessao, tarefa)` tool with a required `sessao`, a prompt focused on changing code and running the project's tests.

### `infra/claude/session.py`

- `CodingSession(bus, name, kind: AgentKind, cwd, model, timeout_s, connect)`. `options()` reads `tools` and `prompt()` from the `kind`; the rest (auto mode, `strict_mcp_config`, `setting_sources=[]`) stays the same.
- `run()` now keeps the tokens from `ResultMessage.usage` (`input_tokens + output_tokens` added to the session total) and returns them in the `Reply` (`tokens: int`, default 0).
- `clear()`: disconnects the client; the next `run` reconnects with a new context.
- `close()`: same as `clear()`, used on delete.

### `controllers/sessions.py`

`Sessions` stops wrapping a single session and manages several:

```python
@dataclass
class Slot:
    session: Session
    queue: asyncio.Queue[str]
    worker: asyncio.Task[None]
    status: Literal["idle", "busy", "error"] = "idle"
    task: str | None = None
    activity: str | None = None      # last agent_progress
    tasks_done: int = 0
    tokens: int = 0
    last_summary: str | None = None
```

| Method | Behavior |
|---|---|
| `create(kind, name, cwd=None) -> str` | Validates the kind in the registry, a free name (RN-01, case-insensitive) and the limit. Default `cwd`: home. Creates the `CodingSession`, starts one worker per session and publishes `session_created`. Returns a sentence for Alfred |
| `delegate(name, task) -> str` | Same as today, by name. An unknown name returns "Não existe sessão X" without raising |
| `clear(name) -> str` | Cancels the worker (and the running task), empties the queue, `session.clear()`, resets counters, recreates the worker, publishes `session_cleared` |
| `delete(name) -> str` | Refuses `sistema`. Cancels the worker, `session.close()`, removes the slot, publishes `session_deleted` |
| `list() -> list[SessionView]` | Snapshot for the API and for `listar_sessoes` |
| `run()` | Goes away: each session has its own worker, created in `create` |

Usage errors (duplicate name, limit, protected session, unknown kind) become sentences returned for Alfred to speak, not exceptions. Changes to metrics (`task`, `activity`, `tokens`, `status`) publish `session_status` with the whole session snapshot.

`activity` comes from the bus: the controller subscribes to `agent_progress` and keeps the `label` (or the text, truncated) of the matching session.

`SessionView` (pydantic, in `models/session.py`): `name, kind, label, model, cwd, status, task, activity, queue, tasks_done, tokens, last_summary, protected`.

### Alfred's tools (`infra/claude/tools.py`)

`alfred_tools(sessions)` builds the in-process MCP with:

- one delegation tool per registry kind (`kind.delegate_tool(sessions.delegate)`), today only `delegar_geral`;
- `criar_sessao(tipo, nome, pasta?)`, `limpar_sessao(nome)`, `apagar_sessao(nome)`, `listar_sessoes()`.

All of them go into `permissions.ALLOWED`. Alfred's prompt (`alfred.py`) explains: use `delegar_geral` for computer tasks, without `sessao` when the user does not name one; confirm with the user before `apagar_sessao`; `limpar` when they ask to "limpar", "zerar" or "esquecer" a session.

`activity.py`: labels "Criando sessão", "Limpando sessão", "Apagando sessão", "Listando sessões". `delegar_geral` keeps "Mandando para a sessão" and stays in the router's `SILENT_ACTIVITIES`.

### Config

```yaml
limits:
  max_active_sessions: 3
```

New optional `Limits` model in `config.py`, with the default above.

### API (`api/routes/sessions.py`)

| Route | Response |
|---|---|
| `GET /api/sessions` | `list[SessionView]` |
| `POST /api/sessions/{name}/clear` | `SessionView`; 404 if it does not exist |
| `DELETE /api/sessions/{name}` | 204; 404 if it does not exist; 409 if protected |

`Sessions` goes in `app.state.sessions`, like the bus. The routes use `Sessions` methods that raise typed errors (`SessionNotFound`, `SessionProtected`); the tool methods catch those errors and return a sentence.

### Events

| Event | Payload |
|---|---|
| `session_created` | `session: SessionView` |
| `session_status` | `session: SessionView` (before, only name and status) |
| `session_cleared` | `session: SessionView` |
| `session_deleted` | `name` |

## Web

The first version used a row of cards; it looked generic and did not show the link to Alfred. Replaced by the **constellation**:

- Each session is a neutral dot around the orb (SVG/CSS, no WebGL): gray when free, white with a breathing halo when busy, red on error. Alfred's orb is the only color on screen. Colored mini orbs were tried and dropped: visually heavy and one WebGL context per agent.
- A floating label under the node: name and, below it, the current activity (busy) or `livre · model`.
- A neutral gray filament links the orb's center to each node, drawn behind both orbs. Free: faint line. Busy: animated dashes, lighter.
- A light pulse runs along the filament: Alfred → node when a task starts, node → Alfred when it ends (derived from `session_status` events).
- Clicking the node opens the details panel (kind, model, folder, task, activity, queue, tasks, tokens, last summary, Clear, Delete with a second click). Esc or a click outside closes it.
- Positions on an ellipse around the orb, sides first, then above and below; kept inside the visible area. Pure geometry in `features/sessions/lib/constellation.ts`, with tests.
- The dashboard passes the `Assistant` orb's ref to the `Constellation`; the features do not import each other.
- Data: TanStack Query `GET /api/sessions` + `/ws` `session_*` events into the cache. `schema.ts` generated from OpenAPI.

## Errors

- Session failure: `error` status on the card, the voice says "A sessão X não conseguiu terminar a tarefa", the next task reconnects (already exists). Status goes back to `idle` when the next task starts.
- Clearing during a task: `CancelledError` in the worker does not become a spoken error; the voice says "Sessão X limpa".
- Route with an unknown name: 404; the card already disappeared through the event.

## Tests

- `test_agents.py`: registry, `GeneralAgent.prompt`, `delegate_tool` forwards `(sessao or "sistema", tarefa)`.
- `test_session.py`: `options()` comes from the kind; `clear()` disconnects and the next `run` reconnects; tokens added up.
- `test_sessions.py`: create (duplicate name, limit, unknown kind); delegate by name and unknown name; clear cancels the running task and empties the queue; delete removes and protects `sistema`; events published.
- `test_alfred.py`/`test_tools.py`: management tools forward and are in `ALLOWED`; Alfred still has no Bash/Edit/Write.
- `test_api_sessions.py`: the three routes with `TestClient`.
- Web: `make lint` and build; visual check in the browser with the demo mode (since removed).

## Outside this branch

`ImplementationAgent`, worktrees, focus and the `<name>:` shortcut (RF-11, RF-27), interrupting without clearing (RF-33), persistence and resume (RNF-07), `waiting_permission`, creating a session from the screen.
