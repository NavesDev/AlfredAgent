# Projetos, workspaces e agente de implementação (design)

- **Data:** 2026-10-11
- **Status:** Implementado
- **Branch:** `feat/projects-implementation`
- **Requisitos cobertos:** RF-30 (criar pela tela), RF-34, RF-35, RF-36, RF-37, RF-61 (parcial: `/projects`, `/projects/:id`), RNF-07; RN-01, RN-04, RN-11
- **Mockup das animações:** [assets/2026-10-11-butler-mockup.html](assets/2026-10-11-butler-mockup.html) (abrir no navegador; as opções escolhidas estão listadas em [Animação do mordomo](#animação-do-mordomo))

## Objetivo

1. **Projetos e workspaces.** Projeto é só um agrupador com nome e apelidos. Workspace é uma pasta qualquer, com git opcional. Um projeto pode ter um workspace pro back e outro pro front. Worktrees são workspaces criados a partir de um workspace git.
2. **Sessões presas a projeto e local.** Toda sessão pode pertencer a um workspace (e portanto a um projeto). O CRUD de sessões é o mesmo de hoje e ganha `workspace`.
3. **Agente de implementação.** Novo tipo `implementacao` com o harness completo do Claude Code: CLAUDE.md, skills, plugins, hooks, MCPs, todas as tools.
4. **Modelos configuráveis.** Modelo e effort por tipo de agente (`alfred`, `geral`, `implementacao`), editáveis em runtime na tela de configurações, com override por sessão.
5. **Subagentes visíveis.** Subagentes nativos do Claude Code aparecem como satélites efêmeros do nó da sessão.
6. **Persistência.** SQLite para tudo; sessões retomam a conversa depois de reiniciar (resume).
7. **UI.** Constelação agrupada por projeto, o mordomo animado no tipo implementação, telas `/projects`, `/projects/:id` e `/settings`.

## Decisões

| Tema | Decisão |
|---|---|
| Fatiamento | Uma spec e um branch só cobrindo tudo |
| Projeto | Agrupador: `name` + `aliases`. Sem `repo_path` nem `base_branch` (muda a SPEC) |
| Workspace | Pasta qualquer, `kind` `folder` ou `worktree`. Sem validação de git ao cadastrar |
| Worktree | `git worktree add <pai>-wt/<nome> -b <nome>` a partir do HEAD do workspace pai |
| Apagar workspace | `folder`: só sai do cadastro, a pasta fica. `worktree`: `git worktree remove`; recusa se houver mudança não commitada, a menos que force |
| Sessões por workspace | Várias, livre. Mesmo CRUD de hoje |
| Sessão `geral` | Workspace opcional (vira o `cwd`); sem workspace, `cwd` é a home |
| Sessão `implementacao` | Workspace obrigatório |
| Persistência | `sqlite3` da stdlib em `models/db.py`. Resume via `claude_session_id` |
| Modelos | Padrão por tipo na tabela `agent_settings`, editável em `/settings`; override por sessão. O `config.yaml` só semeia na primeira vez |
| Effort | Mesmo esquema do modelo; vazio = padrão do Claude Code |
| Harness da implementação | `setting_sources=["user","project","local"]`, preset `claude_code` no prompt, todas as tools, `skills="all"`, `permission_mode="auto"` |
| MCPs da implementação | Todos carregados por padrão; a tela de configurações tem uma lista de servidores desligados. O prompt manda usar MCP externo só quando a tarefa pedir |
| Subagentes | Efêmeros, só visuais, sem CRUD nem voz |
| Limite | `max_active_sessions` conta processos `claude` vivos, não o cadastro. Editável em `/settings` |
| Ociosidade | Sessão ociosa por `idle_minutes` (padrão 10) desconecta sozinha e retoma por resume na próxima tarefa |
| Identidade na tela | Aglomerados: losango do projeto entre o Alfred e as sessões dele |
| Criação pela tela | Rotas `/projects`, `/projects/:id`, `/settings` + menu "nova sessão aqui" ao clicar no losango |
| Segurança | O Alfred continua sem Bash/Edit/Write (ADR 0003). O risco do harness completo vai para a ADR 0008 |

## Dados (`server/models/`)

### Tabelas

| Tabela | Campos |
|---|---|
| `project` | `id`, `name` (único, sem diferenciar maiúsculas), `aliases` (json), `created_at` |
| `workspace` | `id`, `project_id`, `name` (único dentro do projeto), `path`, `kind` (`folder` \| `worktree`), `parent_id` (opcional, só worktree), `branch` (opcional), `created_at` |
| `session` | `id`, `name` (único global, RN-01), `kind`, `workspace_id` (opcional), `model` (opcional), `effort` (opcional), `claude_session_id` (opcional), `protected`, `created_at` |
| `agent_settings` | `kind` (PK: `alfred`, `geral`, `implementacao`), `model`, `effort` (opcional) |
| `app_settings` | `key` (PK), `value` (json): `max_active_sessions`, `idle_minutes`, `mcp_disabled` |

### Arquivos

- `models/db.py`: abre a conexão (`storage.db_path`), cria as tabelas com `CREATE TABLE IF NOT EXISTS` e controla migrações por `PRAGMA user_version`. `foreign_keys=ON`. As operações são curtas e locais e rodam direto no loop.
- `models/project.py`: `Project`, `Workspace` (pydantic) e funções `create/get/list/update/delete` por entidade.
- `models/session.py`: `SessionRecord` (linha da tabela) e `SessionView` (o que a tela e o Alfred veem), com as funções de CRUD.
- `models/settings.py`: `AgentSettings`, `AppSettings`, `load/save` e `seed(config)`.

### Regras

- Precedência de modelo e effort: sessão → `agent_settings` do tipo → `config.yaml` (`agents.default_model`).
- Um workspace com sessão não pode ser apagado. Um projeto com workspace também não. Os dois devolvem erro em pt-BR.
- `claude_session_id` é salvo ao fim de cada tarefa (`ResultMessage.session_id`). Limpar zera o campo; apagar remove a linha.
- No boot, `sistema` é semeada se não existir (tipo `geral`, protegida, sem workspace). Todas as sessões carregam desconectadas.
- `seed(config)` grava `agent_settings` e `app_settings` só quando as tabelas estão vazias.

## Server

### `infra/git.py` (novo)

Funções async com `asyncio.create_subprocess_exec("git", ...)`, sem bloquear o loop:

- `add_worktree(parent: Path, name: str) -> tuple[Path, str]`: path `<parent>-wt/<name>`. Se a branch `name` já existe, usa `git worktree add <path> <name>`; senão `-b <name>`. Devolve path e branch.
- `remove_worktree(path: Path, force: bool)`: `git worktree remove [--force] <path>`.
- `is_dirty(path: Path) -> bool`: `git status --porcelain`.
- Falha do git vira `GitError(AlfredError)` com a mensagem do stderr cortada.

### `infra/claude/agents.py`

`AgentKind` ganha o que cada tipo precisa para montar as opções do SDK:

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

- **`GeneralAgent`** mantém o comportamento atual: tools fixas, `strict_mcp_config=True`, `setting_sources=[]`, prompt próprio, `permission_mode="auto"`.
- **`ImplementationAgent`** (novo, `kind="implementacao"`, `label="Implementação"`, `needs_workspace=True`):

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

`IMPLEMENTATION_APPEND`: nome da sessão, projeto e workspace; `SUMMARY_RULE`; "use MCPs externos (e-mail, agenda, navegador) só quando a tarefa pedir explicitamente".

Tool do Alfred: `delegar_implementacao(sessao, tarefa)`, ambos obrigatórios.

### `infra/claude/session.py`

- `CodingSession` recebe um `SessionContext` e o `AgentKind`; `options()` delega ao kind.
- `run()` passa a tratar, além de `AssistantMessage` e `ResultMessage`:
  - `TaskStartedMessage` → `subagent_started` (`session`, `id=task_id`, `type=task_type`, `description`).
  - `TaskProgressMessage` → `subagent_progress` (`session`, `id`, `last_tool`).
  - `TaskNotificationMessage` → `subagent_finished` (`session`, `id`, `status`).
  - `SystemMessage` `init` → guarda os nomes em `data["mcp_servers"]` como `known_mcp_servers` (sugestões na tela).
  - Mensagens com `parent_tool_use_id` (de subagentes) não alimentam a fase nem o `agent_progress` da sessão.
- `Reply` ganha `session_id` (de `ResultMessage.session_id`) para o controller persistir.
- `connected` (propriedade): há cliente aberto.

### Fase da sessão

`infra/claude/activity.py` ganha `phase_of(tool_name) -> Phase | None`:

| Fase | Tools |
|---|---|
| `exploring` | `Read`, `Grep`, `Glob`, `LS`, `WebSearch`, `WebFetch`, `NotebookRead` |
| `editing` | `Edit`, `Write`, `MultiEdit`, `NotebookEdit` |
| `running` | `Bash`, `BashOutput` |

Tools fora da tabela (MCP, `Skill`, `TodoWrite`) não mudam a fase. `agent_progress` passa a incluir `phase`. O controller guarda a última fase da tarefa; ela volta a `null` quando a tarefa acaba.

### `controllers/projects.py` (novo)

`Projects(db, bus, sessions)`:

| Método | Comportamento |
|---|---|
| `create(name, aliases)` | Nome livre e único. Publica `project_created` |
| `update(id, name?, aliases?)` | Publica `project_updated` |
| `delete(id)` | Recusa se tiver workspace. Publica `project_deleted` |
| `add_workspace(project, name, path)` | `kind=folder`. A pasta precisa existir. Publica `project_updated` |
| `add_worktree(project, parent, name)` | `git.add_worktree` a partir do path do pai; cadastra `kind=worktree`, `parent_id`, `branch`. Publica `project_updated` |
| `delete_workspace(id, force=False)` | Recusa se tiver sessão. Worktree: `is_dirty` e sem `force` → erro "o worktree tem mudanças não commitadas"; senão `remove_worktree`. Publica `project_updated` |
| `find(name)` | Resolve projeto por nome ou apelido (sem diferenciar maiúsculas; fuzzy fica pra F3) |

Erros: `ProjectError(AlfredError)` com `ProjectNotFound` e `ProjectInUse`, mensagens em pt-BR.

### `controllers/settings.py` (novo)

`Settings(db, bus)`: `get() -> SettingsView`, `update(...)`. Publica `settings_updated`. Mudanças de modelo/effort valem na próxima conexão de cada sessão; o Alfred reabre o cliente na próxima pergunta se o modelo dele mudou. `max_active_sessions` e `idle_minutes` valem na hora.

### `controllers/sessions.py`

Mudanças sobre o que existe:

- **Persistência.** `create` grava a linha; `add` some (o boot carrega do banco). `clear` zera `claude_session_id`; `delete` apaga a linha.
- **`create(kind, name, workspace_id=None, model=None, effort=None)`.** Valida `needs_workspace`. O `cwd` vem do workspace (ou home). Não conta no limite: criar não abre processo.
- **`update(name, model?, effort?)`.** Override por sessão; vale na próxima conexão.
- **Vagas.** Um pool com `max_active_sessions` vagas. Antes de rodar uma tarefa, o worker pede vaga:
  1. a sessão já está conectada → segue;
  2. há vaga livre → ocupa;
  3. há sessão conectada e ociosa → desconecta a ociosa há mais tempo e ocupa;
  4. senão espera numa fila FIFO global.
- **Ociosidade.** Um vigia a cada 30 s desconecta sessões ociosas há mais de `idle_minutes` e libera a vaga.
- **`delegate`** avisa a fila global: "Todas as vagas estão ocupadas; a tarefa da sessão X entrou na fila."
- **Subagentes.** Assina `subagent_*` do bus e mantém `slot.subagents` (id, tipo, descrição, última tool, status). Os concluídos ficam até a próxima tarefa começar.
- **Fase.** Assina `agent_progress` e guarda `slot.phase`.

`SessionView` passa a ter: `project` (nome, opcional), `workspace` (nome, opcional), `branch`, `effort`, `phase` (`exploring` \| `editing` \| `running` \| `null`), `connected`, `subagents: list[SubagentView]`, além dos campos atuais. `SubagentView`: `id`, `type`, `description`, `last_tool`, `status` (`running` \| `completed` \| `failed` \| `stopped`).

### Tools do Alfred (`infra/claude/tools.py`)

Todas entram em `permissions.ALLOWED`. Nenhuma executa comando livre no computador. As únicas que mexem no disco são `criar_worktree` e `apagar_workspace`, via `infra/git.py`, sempre a partir de uma pasta já cadastrada.

| Tool | Argumentos |
|---|---|
| `criar_projeto` | `nome`, `apelidos?` |
| `listar_projetos` | — (projetos, workspaces e sessões numa frase) |
| `criar_workspace` | `projeto`, `nome`, `pasta` |
| `criar_worktree` | `projeto`, `workspace_pai`, `nome` |
| `apagar_workspace` | `projeto`, `nome`, `forcar?` (confirmar antes; confirmar de novo antes de forçar) |
| `criar_sessao` | `tipo`, `nome`, `projeto?`, `workspace?`, `modelo?`, `effort?` (troca `pasta` por projeto + workspace) |
| `delegar_implementacao` | `sessao`, `tarefa` |
| `delegar_geral`, `limpar_sessao`, `apagar_sessao`, `listar_sessoes` | Como hoje |

Prompt do Alfred: código e repositórios vão para `delegar_implementacao` numa sessão do projeto certo; sem sessão de implementação no projeto, perguntar se cria uma ("crio a sessão back no Recurve?"). "Nova sessão testes no Recurve, worktree cancelamento" = `criar_worktree` (se não existir) + `criar_sessao`.

`activity.py`: rótulos para as tools novas; `delegar_implementacao` entra em `SILENT_ACTIVITIES`.

### API

| Rota | Uso |
|---|---|
| `GET /api/projects`, `POST /api/projects` | Lista (com workspaces) e cria |
| `GET/PATCH/DELETE /api/projects/{id}` | Detalhe, renomear/apelidos, apagar (409 se em uso) |
| `POST /api/projects/{id}/workspaces` | `{name, path}` |
| `POST /api/projects/{id}/worktrees` | `{parent_id, name}` |
| `DELETE /api/workspaces/{id}?force=` | 409 se tiver sessão ou mudanças não commitadas sem `force` |
| `GET /api/sessions`, `POST /api/sessions` | Lista e cria (`{kind, name, workspace_id?, model?, effort?}`) |
| `PATCH /api/sessions/{name}` | `{model?, effort?}` |
| `POST /api/sessions/{name}/clear`, `DELETE /api/sessions/{name}` | Como hoje |
| `GET /api/settings`, `PUT /api/settings` | Modelos e effort por tipo, `max_active_sessions`, `idle_minutes`, `mcp_disabled`, `known_mcp_servers` (só leitura) |

`Projects` e `Settings` vão em `app.state`, como `Sessions`. Erros tipados viram 404/409/422 nas rotas e frases nas tools.

### Eventos novos

| Evento | Payload |
|---|---|
| `project_created`, `project_updated` | `project: ProjectView` (com workspaces) |
| `project_deleted` | `id` |
| `settings_updated` | `settings: SettingsView` |
| `subagent_started` | `session`, `id`, `type`, `description` |
| `subagent_progress` | `session`, `id`, `last_tool` |
| `subagent_finished` | `session`, `id`, `status` |
| `agent_progress` | ganha `phase` (opcional) |

Os `session_*` continuam com o `SessionView` inteiro, agora com os campos novos.

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

`Storage.db_path` e `Agents.models` entram no `config.py`, com padrões.

## Web (`apps/web`)

### Rotas e features

Entra `react-router` (já previsto na STACK). Rotas: `/` (dashboard), `/projects`, `/projects/:id`, `/settings`. Navegação discreta no topo.

| Feature | Conteúdo |
|---|---|
| `projects/` | `ProjectsPage` (lista, criar projeto), `ProjectPage` (workspaces com path/branch, criar workspace e worktree, sessões do projeto, criar sessão), hooks `useProjects`, `useProject`, mutations |
| `settings/` | `SettingsPage`: modelo + effort por tipo, limite de sessões, minutos ociosos, MCPs desligados (com sugestões de `known_mcp_servers`); hook `useSettings` |
| `sessions/` | Constelação agrupada, nó do mordomo, satélites, menu do losango, painel de detalhes com modelo/effort editáveis |

O formulário de nova sessão (tipo, nome, workspace, modelo, effort) é usado por `projects` e `sessions`, então sobe para `components/NewSessionForm.tsx`. Ele só recebe dados e callbacks; cada feature passa os seus hooks. `schema.ts` é regenerado (`make gen-api`).

### Constelação agrupada

- Sessões com projeto ficam num setor da elipse. Do orb sai um filamento até o **losango do projeto** (rótulo em caixa alta acima), e do losango saem ramos curtos até cada sessão. Sessões sem projeto (ex: `sistema`) ligam direto no orb, como hoje.
- Rótulo da sessão: nome, e embaixo o chip do workspace (`back · ⎇ cancelamento`), depois a atividade.
- Clique no losango abre um menu com "nova sessão aqui" (abre o `NewSessionForm` com o projeto preenchido) e "abrir projeto" (vai pra `/projects/:id`).
- Geometria pura em `features/sessions/lib/constellation.ts`, com testes: setores por projeto, posição do losango, ramos.
- Os pulsos de luz continuam, agora pelo caminho orb → losango → sessão.

### Subagentes

Cada subagente ativo é um quadradinho ligado ao nó da sessão por um traço fino, com o tipo em mono ao lado. Ele pisca a cada `subagent_progress`. Ao terminar, some com fade. O painel de detalhes lista os subagentes da tarefa atual (tipo, descrição, última tool, status). Os dados vêm do `SessionView.subagents` e dos eventos `subagent_*`.

### Animação do mordomo

Só as sessões `implementacao` usam o mordomo; as `geral` continuam como ponto. Ele é pixel art em SVG (grade 36×32) com animações em CSS, em `features/sessions/components/butler/`. O terno é neutro, e o único toque de cor é a gravata no roxo do orb. As referências estão no mockup, nos cards com estes IDs.

| Estado | Gatilho | Animação (ID no mockup) |
|---|---|---|
| Ocioso | `idle` (conectado ou não) | Cochilando: cabeça baixa, olhos fechados, zzz, respiração lenta |
| Explorando | `busy` + `phase=exploring` | **E3** Balão de pensamento: digita devagar, balão alterna pasta, arquivo e lupa |
| Editando | `busy` + `phase=editing` (ou fase nula) | Digitando no laptop, cabeça balançando |
| Rodando | `busy` + `phase=running` | **T1** Enter dramático: dedo sobe, bate no Enter, cruza os braços com "..." |
| Chamando subagente | `subagent_started` (toca ~1,5 s e volta à fase) | **C3** Carta selada com selo roxo voa em direção ao quadradinho do subagente |
| Terminou | `busy` → `idle` sem erro (toca uma vez, ~3 s) | **AB3** Truque da cartola: tira a cartola, vira e o ✓ sai de dentro |
| Erro | `error` | Olhos em X, tremida |
| Aguardando permissão | reservado para a F5, sem gatilho agora | **A1** Placa "?" balançando, sem onda pulsando |

- **Hover** no mordomo: um terminal pequeno com as últimas 6 tool calls da sessão (`› Edit billing.py`). Ele é montado no cache da web a partir de `agent_progress`, sem rota nova.
- **Tamanhos.** Na constelação o nó tem ~36 px; o painel de detalhes mostra o mordomo maior.
- **Lógica.** A máquina de estados é pura (`lib/butler.ts`: `(view, lastEvent) → ButlerState`) e tem testes. Os componentes só renderizam o estado.
- **Acessibilidade.** Com `prefers-reduced-motion`, cada estado vira um quadro parado. O `aria-label` do nó diz o estado em texto.

## Erros

- Git falhou (`GitError`): a voz fala a mensagem curta e a API devolve 422 com o stderr cortado. Nada é cadastrado se o `git worktree add` falhar.
- O resume falhou (conversa sumiu do disco): a sessão abre conversa nova, publica `error` com "a sessão X perdeu o histórico e começou do zero" e segue a tarefa.
- O workspace sumiu do disco: a tarefa falha antes de conectar e a sessão fica `error` com "a pasta do workspace X não existe mais".
- A desconexão por ociosidade nunca vira erro.
- Fila global cheia não tem limite. O Alfred só avisa a posição.

## Segurança — ADR 0008

Nova ADR "Agente de implementação com harness completo":

- **Decisão:** a sessão `implementacao` carrega as configurações do usuário (CLAUDE.md, skills, plugins, hooks e todos os MCPs) e roda em auto mode, sem lista fixa de tools.
- **Risco aceito:** essa sessão pode ler conteúdo externo (e-mail ou web, via MCP) e executar comandos no mesmo turno. É o cenário que as ADRs 0003 e 0006 evitam para o Alfred e para a `sistema`.
- **Mitigações:**
  - o classificador do auto mode;
  - a regra no prompt de usar MCP externo só quando a tarefa pedir;
  - a lista de MCPs desligados na tela de configurações;
  - o Alfred continua sem Bash/Edit/Write e descreve as tarefas com as próprias palavras (ADR 0006).

## Documentação a atualizar

- `SPEC.md` e `ARCHITECTURE.md`:
  - novo modelo de dados (projeto sem `repo_path`/`base_branch`, workspace com `kind` `folder|worktree` e `parent_id`);
  - tipos de agente;
  - eventos novos;
  - rotas.
- `REQUIREMENTS.md`:
  - RN-04 passa a contar processos vivos;
  - RN-11 passa a valer para `folder|worktree`;
  - Questão em aberto 4 resolvida (a fila por sessão continua em memória; o histórico vem do resume).
- ADR 0008.

## Testes

Server (pytest, SDK e git falsos como hoje):

- `test_db.py`:
  - criação das tabelas e `user_version`;
  - `seed` grava só uma vez.
- `test_projects.py`:
  - nomes únicos;
  - apagar recusado com dependentes;
  - worktree com git falso: path, branch existente vs nova, falha não cadastra;
  - sujo sem `force` → erro.
- `test_git.py`: num repo temporário real (`git init`), `add_worktree` e `remove_worktree` funcionam e `is_dirty` detecta mudança.
- `test_settings.py`:
  - precedência sessão → tipo → yaml;
  - `settings_updated`.
- `test_agents.py`: `ImplementationAgent.options()` tem:
  - preset `claude_code`;
  - `setting_sources` completo;
  - `skills="all"`;
  - `disallowed_tools` a partir de `mcp_disabled`;
  - workspace obrigatório.
- `test_session.py`:
  - eventos `subagent_*` a partir das `Task*Message`;
  - mensagens com `parent_tool_use_id` não mudam a fase;
  - `session_id` volta no `Reply`;
  - `resume` nas opções.
- `test_sessions.py`:
  - vagas (ocupa, despeja a ociosa mais antiga, enfileira e libera em ordem);
  - vigia de ociosidade;
  - persistência e boot carregando desconectado;
  - `clear` zera o `claude_session_id`;
  - fase e subagentes no snapshot.
- `test_activity.py`: `phase_of`.
- `test_tools.py`:
  - tools novas repassam e estão em `ALLOWED`;
  - o Alfred continua sem Bash/Edit/Write.
- `test_api_projects.py`, `test_api_settings.py`, `test_api_sessions.py` (criar e `PATCH`).

Web (Vitest):

- `constellation.test.ts`: setores, losango, ramos.
- `butler.test.ts`: máquina de estados, incluindo "terminou" só depois de `busy` sem erro e "chamando" com duração limitada.
- Hooks: os eventos de projeto e subagente atualizam o cache.
- `make lint`, build e conferência visual no navegador com o modo demo (`lib/demo.ts` ganha projetos, uma sessão de implementação e subagentes).

## Fora desta branch

- Permissões e `waiting_permission`, F5. A animação fica desenhada mas sem gatilho.
- Atalho `<nome>:` e foco (RF-11, RF-27).
- Fuzzy match de nomes.
- Interromper sem limpar (RF-33).
- Tarefas (RF-38/39).
- Clonar repositório ou criar projeto do zero: dá pra delegar à `sistema`.
- Histórico persistido dos subagentes.
- Mudar o tipo de uma sessão existente.
