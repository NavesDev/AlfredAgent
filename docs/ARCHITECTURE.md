# Arquitetura

Visão técnica do Alfred. Requisitos em [REQUIREMENTS.md](REQUIREMENTS.md), tecnologias em [STACK.md](STACK.md).

## Visão geral

Um processo Python (asyncio) roda o loop de voz, os agentes e a API. A fala desce pela cadeia local até o roteador. Comandos de sistema são resolvidos ali mesmo; o resto vai para o agente principal ou para uma sessão nomeada, que conversam com o Claude na nuvem e devolvem só a linha de resumo para o Kokoro falar.

```mermaid
flowchart LR
    mic([Microfone]) --> ww[openWakeWord]
    ww --> vad[Silero VAD]
    vad --> stt[faster-whisper]
    stt --> router{Router}
    web([Painel web<br/>CommandBar]) -->|POST /api/commands| router

    router -->|interrupção / sistema| ctrl[Controllers]
    router -->|"&lt;nome&gt;: ..."| sess[Sessões nomeadas]
    router -->|resto| alfred[Agente principal<br/>alfred]

    alfred -->|tools internas| ctrl
    alfred -->|delegar| sess
    alfred --> cloud[(Claude API<br/>MCP Gmail / Calendar<br/>WebSearch)]
    sess --> cloud
    sess --> repo[(Worktrees git)]

    ctrl --> db[(SQLite)]
    ctrl --> bus[[Event bus]]
    alfred --> bus
    sess --> bus

    bus --> talker[Kokoro + fila de fala]
    bus --> ws[WebSocket]
    talker --> spk([Alto-falante])
    ws --> web
```

Local: tudo à esquerda da nuvem. Nuvem: raciocínio (Claude) e integrações (Gmail, Calendar, web).

## Camadas do server

| Camada | Responsabilidade | Pode importar |
|---|---|---|
| `models/` | Dados e SQLite. Não sabe nada de voz nem de Claude | — |
| `infra/` | Mundo externo: microfone, alto-falante, Claude, git | `models` (só tipos) |
| `controllers/` | Lógica de decisão. Único lugar que junta `models` com `infra` | `models`, `infra`, `events` |
| `api/` | Expõe controllers e eventos ao painel | `controllers`, `events` |
| `events.py` | Bus em memória (pub/sub) | — |
| `main.py` | Composição: sobe threads de áudio, loop dos agentes e API | tudo |

Sem interfaces nem camadas extras. Trocar Whisper ou Kokoro é mexer só em `listener.py` ou `talker.py`.

## Estrutura de pastas

```text
alfred/
├── server/
│   ├── main.py                # starts voice loop + API
│   ├── config.yaml            # local, not versioned (see config.example.yaml)
│   ├── pyproject.toml
│   ├── events.py              # in-memory event bus
│   ├── models/
│   │   ├── db.py
│   │   ├── project.py         # Project + Workspace
│   │   ├── session.py
│   │   └── task.py
│   ├── controllers/
│   │   ├── router.py          # interrupts + session-name shortcut
│   │   ├── sessions.py
│   │   ├── projects.py
│   │   └── tasks.py
│   ├── infra/
│   │   ├── audio/
│   │   │   ├── listener.py    # wake word + VAD + Whisper
│   │   │   └── talker.py      # Kokoro + speech queue
│   │   ├── claude/
│   │   │   ├── alfred.py      # main agent
│   │   │   ├── session.py     # coding sessions
│   │   │   ├── permissions.py # permission gates
│   │   │   └── tools.py       # internal tools for Alfred
│   │   └── git.py             # git worktree add/remove
│   └── api/
│       ├── app.py             # FastAPI + serves the web build
│       ├── routes/            # projects, sessions, tasks, confirmations, commands
│       └── ws.py              # pushes events to the web app
├── apps/
│   ├── web/                   # React + TypeScript + Vite
│   └── desktop/               # Tauri (future)
├── docs/
└── Makefile
```

## Threads e concorrência

```mermaid
flowchart TB
    subgraph T1[Thread: listener]
        cap[sounddevice stream] --> wwd[wake word + VAD] --> whisper[faster-whisper]
    end
    subgraph Loop[Loop asyncio principal]
        router2[router] --> agents[agentes / sessões]
        agents --> bus2[event bus]
        api2[FastAPI + WS]
    end
    subgraph T3[Thread: TTS]
        kokoro[Kokoro + playback]
    end
    whisper -->|call_soon_threadsafe| router2
    bus2 -->|fila de fala| kokoro
```

- Captura e wake word ficam sempre ligados, com custo quase zero de CPU.
- O Whisper roda na thread do listener, só por segmento de fala; o modelo fica carregado. O microfone é ignorado enquanto o comando é processado.
- O Kokoro consome uma fila de fala com prioridade; barge-in limpa a fila e para o playback.
- Interrupções ("para") são casadas no próprio listener/router antes de qualquer `await` longo, para agir em milissegundos.

## Fluxo de um comando

```mermaid
sequenceDiagram
    participant U as Usuário
    participant L as listener
    participant R as router
    participant A as alfred
    participant S as sessão "backend"
    participant B as event bus
    participant T as talker

    U->>L: "Alfred, manda o backend fazer a tarefa de reembolso"
    L->>R: transcript
    R->>B: transcript
    R->>R: não é interrupção nem atalho
    R->>A: prompt
    A->>A: tool tasks.find("reembolso")
    A->>S: delegar("backend", tarefa)
    A->>B: task_updated (in_progress)
    A-->>B: alfred_reply "RESUMO: mandei pro backend."
    B->>T: fala
    S-->>B: session_status busy … idle
    S-->>B: alfred_reply "backend terminou: <resumo>"
    B->>T: fala (entra na fila se usuário estiver falando)
    B->>B: task_updated (done)
```

## Roteamento

Ordem de avaliação no `controllers/router.py`:

1. **Interrupções** (regex): `para`, `<sessão>, para`, `para tudo`. Agem mesmo com tudo ocupado.
2. **Comandos de sistema** (gramática fixa, sem token): foco, status, listar, fechar sessão etc. Os que não casarem com segurança caem no agente principal, que tem as mesmas tools.
3. **Atalho explícito**: `<nome>:` ou `<nome>,` no início, onde `<nome>` casa com nome/apelido de sessão (rapidfuzz ≥ ~85). Vai direto para a sessão.
4. **Agente principal**: todo o resto.

Sessão ocupada não recebe dois prompts ao mesmo tempo: cada sessão tem uma fila FIFO. O router publica o aviso "tá ocupado, coloquei na fila".

## Agentes

### Agente principal (`alfred`)

- Sessão fixa, não presa a repositório.
- Tools: WebSearch, WebFetch, MCP Gmail, MCP Calendar e o MCP in-process de `infra/claude/tools.py` (projetos, sessões, worktrees, tarefas, `delegar`).
- **Sem Bash e sem Edit.** Quem lê conteúdo externo nunca executa comando.
- Até a fase 5: leitura de Gmail/Agenda, web e navegador liberados; escrita escondida e negada ([ADR 0004](adr/0004-main-agent-read-only-plus-browser.md)).
- Modelo Sonnet por padrão; perguntas simples podem cair no Haiku.
- Conhece a sessão em foco e o projeto atual (injetados no contexto).
- Uma conversa por dia: o `claude_session_id` da sessão `alfred` rotaciona diariamente.
- Cliente persistente (`ClaudeSDKClient`): o CLI fica aberto entre perguntas e é reaberto quando o dia vira ou após erro.

### Sessões nomeadas

- Uma instância do Agent SDK por sessão, com `cwd` = path do workspace.
- Auto mode do Claude Code + gate `canUseTool` do `permissions.py`.
- `system_prompt` exige começar com `RESUMO:` (até 2 frases, sem código nem caminhos longos), falado assim que chega.
- `claude_session_id` persistido para resume após reinício.
- Limite de sessões ativas simultâneas (`limits.max_active_sessions`, padrão 3).

## Modelo de dados

```mermaid
erDiagram
    PROJECT ||--o{ WORKSPACE : has
    WORKSPACE ||--o{ SESSION : hosts
    PROJECT ||--o{ TASK : groups
    SESSION ||--o{ TASK : executes

    PROJECT {
        int id PK
        text name
        json aliases
        text repo_path
        text base_branch
    }
    WORKSPACE {
        int id PK
        int project_id FK
        text name
        text path
        text branch
        text kind "main | worktree"
    }
    SESSION {
        int id PK
        int workspace_id FK "null para alfred"
        text name UK
        json aliases
        text claude_session_id
        text status "idle | busy | waiting_permission | error"
        json allowed_tools
        text system_prompt
    }
    TASK {
        int id PK
        int project_id FK "opcional"
        text title
        text status "open | in_progress | done"
        text priority "low | medium | high"
        int session_id FK "opcional"
        datetime created_at
    }
```

Tabelas auxiliares previstas: `audit_log` (toda tool call), `confirmation` (pedidos pendentes/respondidos), `session_summary` (último `RESUMO:` por sessão).

## Event bus

`events.py` é um pub/sub em memória. Controllers e agentes publicam; `talker` e `ws.py` consomem. Voz e tela ficam em paridade sem duplicar lógica.

| Evento | Payload principal | Consumidores |
|---|---|---|
| `transcript` | texto, origem (voz/painel) | ws |
| `alfred_reply` | sessão, resumo, texto completo | talker (só resumo), ws |
| `session_status` | sessão, status | ws, talker (quando termina) |
| `task_updated` | tarefa | ws |
| `permission_request` | id, sessão, ação, descrição, canal | talker, ws |
| `permission_resolved` | id, aprovado, canal | ws |

## Erros

Exceções em camadas, todas em `server/errors.py`:

```text
AlfredError
├── ConfigError        # config.yaml inválido            → fatal na inicialização
├── DependencyError    # CLI claude, microfone, modelos   → fatal na inicialização
├── AudioError         # falha em captura/STT/TTS         → recuperável
└── AgentError         # falha/timeout no Agent SDK       → recuperável
```

Regras:

- **`infra` traduz:** exceção de biblioteca externa vira a exceção da camada com `raise XError(...) from e`. Nada de `except Exception` engolindo erro.
- **`controllers` decide:** captura `AudioError`/`AgentError` no limite do turno, publica `error` no bus, fala a mensagem curta e volta a `idle`.
- **`main` encerra:** `ConfigError`/`DependencyError` imprimem a mensagem e saem com código 1.
- **Fail-fast:** tudo que pode falhar é verificado na inicialização, antes de abrir o microfone: config válido, `claude` no `PATH`, dispositivo de áudio, modelos (Whisper, Kokoro, wake word) carregados de forma eager. Nada é carregado sob demanda no primeiro comando.
- Exceção inesperada dentro de thread de áudio: loga com traceback, publica `error`, a thread segue. No loop principal, derruba o processo.

## Permissões

```mermaid
flowchart TD
    call[tool call] --> deny{denylist?}
    deny -->|sim| no[negado]
    deny -->|não| taint{turno contaminado<br/>e efeito colateral?}
    taint -->|sim| ask
    taint -->|não| sens{ação sensível?}
    sens -->|sim| ask[permission_request<br/>canal configurado]
    sens -->|não| ok[permitido]
    ask -->|aprovado| ok
    ask -->|negado / timeout 60s| no
    ok --> audit[(audit_log)]
    no --> audit
```

- **Denylist:** `sudo`, `rm -rf` fora do worktree, escrita fora do workspace.
- **Sensíveis:** push, apagar arquivo, instalar dependência, enviar e-mail, mexer na agenda.
- **Turno contaminado:** se o turno leu e-mail ou web, qualquer efeito colateral exige confirmação (defesa contra prompt injection).
- **Canais:** `voice`, `key`, `web`, `voice+key`, configuráveis por ação. Um "pode" falado não prova que foi você, por isso ações críticas usam `key`.
- Sessão aguardando fica `waiting_permission`. Confirmação pode vir por voz ou por `POST /api/confirmations/{id}`.

## API

| Rota | Uso |
|---|---|
| `GET/POST /api/projects`, `GET /api/projects/{id}` | Projetos e workspaces |
| `POST /api/projects/{id}/worktrees`, `DELETE …/{ws_id}` | Criar/remover worktree |
| `GET/POST /api/sessions`, `POST /api/sessions/{id}/stop` | Sessões |
| `GET/POST/PATCH /api/tasks` | Tarefas |
| `GET /api/confirmations`, `POST /api/confirmations/{id}` | Confirmações pendentes |
| `POST /api/commands` | Texto para o mesmo router da voz |
| `WS /ws` | Stream de eventos do bus |

Em dev, o Vite faz proxy de `/api` e `/ws` para o server. Em produção, o FastAPI serve o `dist/` na mesma porta.

## Web (`apps/web`)

Organizado por feature; cada feature repete o esqueleto `pages/`, `components/`, `hooks/` (só o que precisa).

```text
apps/web/src/
├── main.tsx
├── App.tsx                      # layout + routes + global ConfirmDialog
├── api/                         # client.ts, schema.ts (generated), events.ts
├── features/
│   ├── sessions/  projects/  tasks/  confirmations/
│   ├── activity/  command/  dashboard/
├── components/                  # ui/ (shadcn), layout/
├── hooks/useEvents.ts           # WebSocket → updates the cache
├── lib/
└── styles/globals.css
```

Regras:

- Todo acesso à API fica nos hooks da feature (TanStack Query). Componentes só chamam o hook e renderizam.
- Feature importa de `api/`, `components/`, `hooks/`, `lib/`, nunca de outra feature. Exceção: `dashboard`.
- Componente usado por duas features sobe para `components/`. Tipo específico de feature vai em `types.ts` na raiz dela.
- Sem gerenciador de estado global: servidor no TanStack Query, o resto em `useState`.

## Decisões

Ver [adr/](adr/).
