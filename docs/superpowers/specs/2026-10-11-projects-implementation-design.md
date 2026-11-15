# Projects, workspaces and the implementation agent (design)

- **Date:** 2026-10-11
- **Status:** Implemented
- **Branch:** `feat/projects-implementation`
- **Requirements covered:** RF-30 (create from the screen), RF-34, RF-35, RF-36, RF-37, RF-61 (partial: `/projects`, `/projects/:id`), RNF-07; RN-01, RN-04, RN-11
- **Animation mockup:** [assets/2026-10-11-butler-mockup.html](assets/2026-10-11-butler-mockup.html) (open in the browser; the chosen options are listed under [Butler animation](#butler-animation))

## Goal

1. **Projects and workspaces.** A project only groups things, with a name and aliases. A workspace is any folder, with optional git. A project can have one workspace for the back end and another for the front end. Worktrees are workspaces created from a git workspace.
2. **Sessions tied to a project and a place.** Every session may belong to a workspace (and so to a project). Session CRUD stays the same as today and gains `workspace`.
3. **Implementation agent.** New `implementacao` kind with the full Claude Code harness: CLAUDE.md, skills, plugins, hooks, MCPs, every tool.
4. **Configurable models.** Model and effort per agent kind (`alfred`, `geral`, `implementacao`), editable at runtime on the settings screen, with a per-session override.
5. **Visible subagents.** Claude Code's native subagents show as ephemeral satellites of the session node.
6. **Persistence.** SQLite for everything; sessions resume the conversation after a restart (resume).
7. **UI.** Constellation grouped by project, the animated butler on the implementation kind, `/projects`, `/projects/:id` and `/settings` screens.

## Decisions

| Topic | Decision |
|---|---|
| Slicing | One spec and one branch covering everything |
| Project | Grouping: `name` + `aliases`. No `repo_path` or `base_branch` (changes the SPEC) |
| Workspace | Any folder, `kind` `folder` or `worktree`. No git validation on registration |
| Worktree | `git worktree add <parent>-wt/<name> -b <name>` from the parent workspace's HEAD |
| Delete a workspace | `folder`: only unregistered, the folder stays. `worktree`: `git worktree remove`; refuses with uncommitted changes unless forced |
| Sessions per workspace | Several, freely. Same CRUD as today |
| `geral` session | Optional workspace (becomes the `cwd`); without one, `cwd` is the home |
| `implementacao` session | Workspace required |
| Persistence | The stdlib's `sqlite3` in `models/db.py`. Resume through `claude_session_id` |
| Models | Default per kind in the `agent_settings` table, editable in `/settings`; per-session override. `config.yaml` only seeds the first time |
| Effort | Same scheme as the model; empty = Claude Code's default |
| Implementation harness | `setting_sources=["user","project","local"]`, `claude_code` preset prompt, every tool, `skills="all"`, `permission_mode="auto"` |
| Implementation MCPs | All loaded by default; the settings screen has a list of disabled servers. The prompt says to use an external MCP only when the task asks for it |
| Subagents | Ephemeral, visual only, no CRUD or voice |
| Limit | `max_active_sessions` counts live `claude` processes, not registrations. Editable in `/settings` |
| Idleness | A session idle for `idle_minutes` (default 10) disconnects on its own and resumes on the next task |
| Identity on screen | Clusters: the project's diamond between Alfred and its sessions |
| Creating from the screen | `/projects`, `/projects/:id`, `/settings` routes + a "new session here" menu when clicking the diamond |
| Security | Alfred still has no Bash/Edit/Write (ADR 0003). The full harness's risk goes to ADR 0008 |

## Data (`server/models/`)

### Tables

| Table | Fields |
|---|---|
| `project` | `id`, `name` (unique, case-insensitive), `aliases` (json), `created_at` |
| `workspace` | `id`, `project_id`, `name` (unique within the project), `path`, `kind` (`folder` \| `worktree`), `parent_id` (optional, worktree only), `branch` (optional), `created_at` |
| `session` | `id`, `name` (globally unique, RN-01), `kind`, `workspace_id` (optional), `model` (optional), `effort` (optional), `claude_session_id` (optional), `protected`, `created_at` |
| `agent_settings` | `kind` (PK: `alfred`, `geral`, `implementacao`), `model`, `effort` (optional) |
| `app_settings` | `key` (PK), `value` (json): `max_active_sessions`, `idle_minutes`, `mcp_disabled` |

### Files

- `models/db.py`: opens the connection (`storage.db_path`), creates the tables with `CREATE TABLE IF NOT EXISTS` and tracks migrations through `PRAGMA user_version`. `foreign_keys=ON`. Operations are short and local and run straight on the loop.
- `models/project.py`: `Project`, `Workspace` (pydantic) and `create/get/list/update/delete` functions per entity.
- `models/session.py`: `SessionRecord` (the table row) and `SessionView` (what the screen and Alfred see), with the CRUD functions.
- `models/settings.py`: `AgentSettings`, `AppSettings`, `load/save` and `seed(config)`.

### Rules

- Model and effort precedence: session → the kind's `agent_settings` → `config.yaml` (`agents.default_model`).
- A workspace with a session cannot be deleted. Neither can a project with a workspace. Both return an error in pt-BR.
- `claude_session_id` is saved at the end of each task (`ResultMessage.session_id`). Clearing resets the field; deleting removes the row.
- At boot, `sistema` is seeded if missing (kind `geral`, protected, no workspace). Every session loads disconnected.
- `seed(config)` writes `agent_settings` and `app_settings` only when the tables are empty.

## Server

### `infra/git.py` (new)

Async functions with `asyncio.create_subprocess_exec("git", ...)`, without blocking the loop:

- `add_worktree(parent: Path, name: str) -> tuple[Path, str]`: path `<parent>-wt/<name>`. If the `name` branch already exists, uses `git worktree add <path> <name>`; otherwise `-b <name>`. Returns path and branch.
- `remove_worktree(path: Path, force: bool)`: `git worktree remove [--force] <path>`.
- `is_dirty(path: Path) -> bool`: `git status --porcelain`.
- A git failure becomes `GitError(AlfredError)` with the stderr message truncated.

### `infra/claude/agents.py`

`AgentKind` gets what each kind needs to build the SDK options:

```python
class AgentKind(ABC):
    kind: ClassVar[str]
    label: ClassVar[str]
    needs_workspace: ClassVar[bool] = False

    @abstractmethod
    def options(self, ctx: SessionContext) -> sdk.ClaudeAgentOptions: ...

    @abstractmethod
    def delegate_tool(self, delegate: Delegate) -> sdk.SdkMcpTool[Any]: ...
```

`SessionContext` (dataclass): `name`, `cwd`, `model`, `effort`, `resume`, `mcp_disabled`.

- **`GeneralAgent`** keeps today's behavior: fixed tools, `strict_mcp_config=True`, `setting_sources=[]`, its own prompt, `permission_mode="auto"`.
- **`ImplementationAgent`** (new, `kind="implementacao"`, `label="Implementação"`, `needs_workspace=True`):

```python
sdk.ClaudeAgentOptions(
    model=ctx.model,
    effort=ctx.effort,
    cwd=ctx.cwd,
    resume=ctx.resume,
    system_prompt={"type": "preset", "preset": "claude_code", "append": IMPLEMENTATION_APPEND},
    setting_sources=["user", "project", "local"],  # CLAUDE.md, skills, plugins, hooks, MCPs
    skills="all",
    permission_mode="auto",
    disallowed_tools=[f"mcp__{name}" for name in ctx.mcp_disabled],
)
```

`IMPLEMENTATION_APPEND`: session name, project and workspace; `SUMMARY_RULE`; "use external MCPs (mail, calendar, browser) only when the task explicitly asks for it".

Alfred's tool: `delegar_implementacao(sessao, tarefa)`, both required.

### `infra/claude/session.py`

- `CodingSession` takes a `SessionContext` and the `AgentKind`; `options()` delegates to the kind.
- Besides `AssistantMessage` and `ResultMessage`, `run()` now handles:
  - `TaskStartedMessage` → `subagent_started` (`session`, `id=task_id`, `type=task_type`, `description`).
  - `TaskProgressMessage` → `subagent_progress` (`session`, `id`, `last_tool`).
  - `TaskNotificationMessage` → `subagent_finished` (`session`, `id`, `status`).
  - `SystemMessage` `init` → keeps the names in `data["mcp_servers"]` as `known_mcp_servers` (suggestions on screen).
  - Messages with `parent_tool_use_id` (from subagents) do not feed the session's phase or `agent_progress`.
- `Reply` gets `session_id` (from `ResultMessage.session_id`) for the controller to persist.
- `connected` (property): there is an open client.

### Session phase

`infra/claude/activity.py` gets `phase_of(tool_name) -> Phase | None`:

| Phase | Tools |
|---|---|
| `exploring` | `Read`, `Grep`, `Glob`, `LS`, `WebSearch`, `WebFetch`, `NotebookRead` |
| `editing` | `Edit`, `Write`, `MultiEdit`, `NotebookEdit` |
| `running` | `Bash`, `BashOutput` |

Tools outside the table (MCP, `Skill`, `TodoWrite`) do not change the phase. `agent_progress` now includes `phase`. The controller keeps the task's last phase; it goes back to `null` when the task ends.

### `controllers/projects.py` (new)

`Projects(db, bus, sessions)`:

| Method | Behavior |
|---|---|
| `create(name, aliases)` | Free, unique name. Publishes `project_created` |
| `update(id, name?, aliases?)` | Publishes `project_updated` |
| `delete(id)` | Refuses if it has a workspace. Publishes `project_deleted` |
| `add_workspace(project, name, path)` | `kind=folder`. The folder must exist. Publishes `project_updated` |
| `add_worktree(project, parent, name)` | `git.add_worktree` from the parent's path; registers `kind=worktree`, `parent_id`, `branch`. Publishes `project_updated` |
| `delete_workspace(id, force=False)` | Refuses if it has a session. Worktree: `is_dirty` and no `force` → "o worktree tem mudanças não commitadas" error; otherwise `remove_worktree`. Publishes `project_updated` |
| `find(name)` | Resolves a project by name or alias (case-insensitive; fuzzy waits for F3) |

Errors: `ProjectError(AlfredError)` with `ProjectNotFound` and `ProjectInUse`, messages in pt-BR.

### `controllers/settings.py` (new)

`Settings(db, bus)`: `get() -> SettingsView`, `update(...)`. Publishes `settings_updated`. Model/effort changes apply on each session's next connection; Alfred reopens its client on the next question if its model changed. `max_active_sessions` and `idle_minutes` apply at once.

### `controllers/sessions.py`

Changes over what exists:

- **Persistence.** `create` writes the row; `add` goes away (boot loads from the database). `clear` resets `claude_session_id`; `delete` deletes the row.
- **`create(kind, name, workspace_id=None, model=None, effort=None)`.** Validates `needs_workspace`. The `cwd` comes from the workspace (or home). It does not count toward the limit: creating opens no process.
- **`update(name, model?, effort?)`.** Per-session override; applies on the next connection.
- **Slots.** A pool with `max_active_sessions` slots. Before running a task, the worker asks for a slot:
  1. the session is already connected → go on;
  2. there is a free slot → take it;
  3. there is a connected, idle session → disconnect the one idle the longest and take its slot;
  4. otherwise wait in a global FIFO queue.
- **Idleness.** A watcher every 30 s disconnects sessions idle for more than `idle_minutes` and frees the slot.
- **`delegate`** reports the global queue: "Todas as vagas estão ocupadas; a tarefa da sessão X entrou na fila."
- **Subagents.** Subscribes to the bus's `subagent_*` and keeps `slot.subagents` (id, type, description, last tool, status). Finished ones stay until the next task starts.
- **Phase.** Subscribes to `agent_progress` and keeps `slot.phase`.

`SessionView` now has: `project` (name, optional), `workspace` (name, optional), `branch`, `effort`, `phase` (`exploring` \| `editing` \| `running` \| `null`), `connected`, `subagents: list[SubagentView]`, besides the current fields. `SubagentView`: `id`, `type`, `description`, `last_tool`, `status` (`running` \| `completed` \| `failed` \| `stopped`).

### Alfred's tools (`infra/claude/tools.py`)

All of them go into `permissions.ALLOWED`. None runs a free command on the computer. The only ones that touch the disk are `criar_worktree` and `apagar_workspace`, through `infra/git.py`, always from an already registered folder.

| Tool | Arguments |
|---|---|
| `criar_projeto` | `nome`, `apelidos?` |
| `listar_projetos` | — (projects, workspaces and sessions in one sentence) |
| `criar_workspace` | `projeto`, `nome`, `pasta` |
| `criar_worktree` | `projeto`, `workspace_pai`, `nome` |
| `apagar_workspace` | `projeto`, `nome`, `forcar?` (confirm first; confirm again before forcing) |
| `criar_sessao` | `tipo`, `nome`, `projeto?`, `workspace?`, `modelo?`, `effort?` (replaces `pasta` with project + workspace) |
| `delegar_implementacao` | `sessao`, `tarefa` |
| `delegar_geral`, `limpar_sessao`, `apagar_sessao`, `listar_sessoes` | As today |

Alfred's prompt: code and repositories go to `delegar_implementacao` on a session of the right project; with no implementation session in the project, ask whether to create one ("crio a sessão back no Recurve?"). "Nova sessão testes no Recurve, worktree cancelamento" = `criar_worktree` (if missing) + `criar_sessao`.

`activity.py`: labels for the new tools; `delegar_implementacao` goes into `SILENT_ACTIVITIES`.

### API

| Route | Use |
|---|---|
| `GET /api/projects`, `POST /api/projects` | List (with workspaces) and create |
| `GET/PATCH/DELETE /api/projects/{id}` | Detail, rename/aliases, delete (409 if in use) |
| `POST /api/projects/{id}/workspaces` | `{name, path}` |
| `POST /api/projects/{id}/worktrees` | `{parent_id, name}` |
| `DELETE /api/workspaces/{id}?force=` | 409 if it has a session or uncommitted changes without `force` |
| `GET /api/sessions`, `POST /api/sessions` | List and create (`{kind, name, workspace_id?, model?, effort?}`) |
| `PATCH /api/sessions/{name}` | `{model?, effort?}` |
| `POST /api/sessions/{name}/clear`, `DELETE /api/sessions/{name}` | As today |
| `GET /api/settings`, `PUT /api/settings` | Model and effort per kind, `max_active_sessions`, `idle_minutes`, `mcp_disabled`, `known_mcp_servers` (read-only) |

`Projects` and `Settings` go in `app.state`, like `Sessions`. Typed errors become 404/409/422 in the routes and sentences in the tools.

### New events

| Event | Payload |
|---|---|
| `project_created`, `project_updated` | `project: ProjectView` (with workspaces) |
| `project_deleted` | `id` |
| `settings_updated` | `settings: SettingsView` |
| `subagent_started` | `session`, `id`, `type`, `description` |
| `subagent_progress` | `session`, `id`, `last_tool` |
| `subagent_finished` | `session`, `id`, `status` |
| `agent_progress` | gains `phase` (optional) |

`session_*` events keep the whole `SessionView`, now with the new fields.

### Config

```yaml
agents:
  default_model: sonnet        # seed of agent_settings on first boot
  models:                      # optional seeds per kind
    alfred: sonnet
    geral: sonnet
    implementacao: opus
limits:
  max_active_sessions: 3       # seed; edited in /settings afterwards
  idle_minutes: 10
storage:
  db_path: data/alfred.sqlite3
```

`Storage.db_path` and `Agents.models` go into `config.py`, with defaults.

## Web (`apps/web`)

### Routes and features

`react-router` comes in (already in the STACK). Routes: `/` (dashboard), `/projects`, `/projects/:id`, `/settings`. Discreet navigation at the top.

| Feature | Contents |
|---|---|
| `projects/` | `ProjectsPage` (list, create project), `ProjectPage` (workspaces with path/branch, create workspace and worktree, the project's sessions, create session), hooks `useProjects`, `useProject`, mutations |
| `settings/` | `SettingsPage`: model + effort per kind, session limit, idle minutes, disabled MCPs (with suggestions from `known_mcp_servers`); `useSettings` hook |
| `sessions/` | Grouped constellation, butler node, satellites, diamond menu, details panel with editable model/effort |

The new-session form (kind, name, workspace, model, effort) is used by `projects` and `sessions`, so it moves up to `components/NewSessionForm.tsx`. It only takes data and callbacks; each feature passes its own hooks. `schema.ts` is regenerated (`make gen-api`).

### Grouped constellation

- Sessions with a project sit in a sector of the ellipse. A filament runs from the orb to the **project's diamond** (uppercase label above), and short branches run from the diamond to each session. Sessions with no project (e.g. `sistema`) link straight to the orb, as today.
- Session label: name, and below it the workspace chip (`back · ⎇ cancelamento`), then the activity.
- Clicking the diamond opens a menu with "new session here" (opens `NewSessionForm` with the project filled in) and "open project" (goes to `/projects/:id`).
- Pure geometry in `features/sessions/lib/constellation.ts`, with tests: sectors per project, diamond position, branches.
- Light pulses keep going, now along the orb → diamond → session path.

### Subagents

Each active subagent is a small square linked to the session node by a thin stroke, with its type in mono next to it. It blinks on each `subagent_progress`. When it ends, it fades out. The details panel lists the current task's subagents (type, description, last tool, status). The data comes from `SessionView.subagents` and the `subagent_*` events.

### Butler animation

Only `implementacao` sessions use the butler; `geral` ones stay as a dot. It is SVG pixel art (36×32 grid) with CSS animations, in `features/sessions/components/butler/`. The suit is neutral, and the only touch of color is the tie in the orb's purple. The references are in the mockup, on the cards with these IDs.

| State | Trigger | Animation (mockup ID) |
|---|---|---|
| Idle | `idle` (connected or not) | Dozing: head down, eyes closed, zzz, slow breathing |
| Exploring | `busy` + `phase=exploring` | **E3** Thought bubble: types slowly, the bubble cycles folder, file and magnifier |
| Editing | `busy` + `phase=editing` (or null phase) | Typing on the laptop, head bobbing |
| Running | `busy` + `phase=running` | **T1** Dramatic Enter: finger goes up, hits Enter, crosses arms with "..." |
| Calling a subagent | `subagent_started` (plays ~1.5 s and returns to the phase) | **C3** A sealed letter with a purple seal flies toward the subagent's square |
| Done | `busy` → `idle` without error (plays once, ~3 s) | **AB3** Top-hat trick: takes off the hat, turns it over and the ✓ comes out |
| Error | `error` | X eyes, shaking |
| Waiting for permission | reserved for F5, no trigger now | **A1** Swinging "?" sign, no pulsing wave |

- **Hover** on the butler: a small terminal with the session's last 6 tool calls (`› Edit billing.py`). It is built in the web cache from `agent_progress`, with no new route.
- **Sizes.** In the constellation the node is ~36 px; the details panel shows a bigger butler.
- **Logic.** The state machine is pure (`lib/butler.ts`: `(view, lastEvent) → ButlerState`) and tested. The components only render the state.
- **Accessibility.** With `prefers-reduced-motion`, each state becomes a still frame. The node's `aria-label` states the state in text.

## Errors

- Git failed (`GitError`): the voice speaks the short message and the API returns 422 with the truncated stderr. Nothing is registered if `git worktree add` fails.
- Resume failed (the conversation vanished from disk): the session opens a new conversation, publishes `error` with "a sessão X perdeu o histórico e começou do zero" and carries on with the task.
- The workspace vanished from disk: the task fails before connecting and the session goes `error` with "a pasta do workspace X não existe mais".
- Disconnecting for idleness never becomes an error.
- The global queue has no limit. Alfred only reports the position.

## Security — ADR 0008

New ADR "Implementation agent with the full harness":

- **Decision:** the `implementacao` session loads the user's settings (CLAUDE.md, skills, plugins, hooks and every MCP) and runs in auto mode, with no fixed tool list.
- **Accepted risk:** this session can read external content (mail or web, through MCP) and run commands in the same turn. That is the scenario ADRs 0003 and 0006 avoid for Alfred and for `sistema`.
- **Mitigations:**
  - the auto mode classifier;
  - the prompt rule to use an external MCP only when the task asks for it;
  - the disabled-MCP list on the settings screen;
  - Alfred still has no Bash/Edit/Write and describes tasks in its own words (ADR 0006).

## Documentation to update

- `SPEC.md` and `ARCHITECTURE.md`:
  - new data model (project without `repo_path`/`base_branch`, workspace with `kind` `folder|worktree` and `parent_id`);
  - agent kinds;
  - new events;
  - routes.
- `REQUIREMENTS.md`:
  - RN-04 now counts live processes;
  - RN-11 now covers `folder|worktree`;
  - Open question 4 resolved (the per-session queue stays in memory; history comes from resume).
- ADR 0008.

## Tests

Server (pytest, fake SDK and git as today):

- `test_db.py`:
  - table creation and `user_version`;
  - `seed` writes only once.
- `test_projects.py`:
  - unique names;
  - deletion refused with dependents;
  - worktree with fake git: path, existing vs new branch, a failure registers nothing;
  - dirty without `force` → error.
- `test_git.py`: in a real temporary repo (`git init`), `add_worktree` and `remove_worktree` work and `is_dirty` detects a change.
- `test_settings.py`:
  - session → kind → yaml precedence;
  - `settings_updated`.
- `test_agents.py`: `ImplementationAgent.options()` has:
  - the `claude_code` preset;
  - full `setting_sources`;
  - `skills="all"`;
  - `disallowed_tools` from `mcp_disabled`;
  - a required workspace.
- `test_session.py`:
  - `subagent_*` events from the `Task*Message`s;
  - messages with `parent_tool_use_id` do not change the phase;
  - `session_id` comes back in the `Reply`;
  - `resume` in the options.
- `test_sessions.py`:
  - slots (take, evict the oldest idle one, queue and release in order);
  - idleness watcher;
  - persistence and boot loading disconnected;
  - `clear` resets `claude_session_id`;
  - phase and subagents in the snapshot.
- `test_activity.py`: `phase_of`.
- `test_tools.py`:
  - new tools forward and are in `ALLOWED`;
  - Alfred still has no Bash/Edit/Write.
- `test_api_projects.py`, `test_api_settings.py`, `test_api_sessions.py` (create and `PATCH`).

Web (Vitest):

- `constellation.test.ts`: sectors, diamond, branches.
- `butler.test.ts`: state machine, including "done" only after `busy` without error and "calling" with a bounded duration.
- Hooks: project and subagent events update the cache.
- `make lint`, build and a visual check in the browser with the demo mode (since removed).

## Outside this branch

- Permissions and `waiting_permission`, F5. The animation is drawn but has no trigger.
- `<name>:` shortcut and focus (RF-11, RF-27).
- Fuzzy name matching.
- Interrupting without clearing (RF-33).
- Tasks (RF-38/39).
- Cloning a repository or creating a project from scratch: it can be delegated to `sistema`.
- Persisted subagent history.
- Changing the kind of an existing session.
