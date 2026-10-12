# Agentes delegados: tipos polimórficos, ciclo de vida e cartões na tela (design)

- **Data:** 2026-10-11
- **Status:** Aprovado
- **Branch:** `feat/delegate-agents`
- **Requisitos cobertos:** RF-26 (parcial), RF-30 (parcial: criar, listar, limpar, apagar), RF-40, RF-60 (parcial: sessões no dashboard); RN-01, RN-04, RN-05 (sem `waiting_permission`)

## Objetivo

1. Trocar a tool única `delegar` (presa à sessão `sistema`, ADR 0006) por **tipos de agente polimórficos**: cada tipo é uma subclasse de `AgentKind` que define suas tools do Claude Code, prompt e a própria tool de delegar do Alfred. Nesta branch existe um tipo, `geral`; o tipo `implementacao` (sessão presa a um projeto) fica previsto, sem código.
2. Sessões nomeadas **persistentes** que o usuário cria, mantém, **limpa** (zera o contexto, mantém a sessão) e **apaga** por voz.
3. Um **cartão por sessão** no painel, com tipo, modelo, pasta, status, tarefa atual, última atividade, fila, contagem de tarefas, tokens e último resumo, mais botões Limpar e Apagar.

## Decisões

| Tema | Decisão |
|---|---|
| Modelo de sessão | Persistente por nome (não uma instância por tarefa). Tarefas para sessão ocupada entram na fila dela |
| Polimorfismo | Classe base abstrata `AgentKind`; cada tipo gera sua tool `delegar_<kind>`. Tools de gestão são genéricas |
| Tipos nesta branch | Só `geral` (`GeneralAgent`). `ImplementationAgent` só neste documento |
| Sessão `sistema` | Tipo `geral`, criada no boot, sempre presente. Pode ser limpa, não pode ser apagada |
| Várias sessões gerais | `delegar_geral(tarefa, sessao?)`: `sessao` opcional, padrão `sistema` |
| Limpar | Cancela a tarefa em andamento, esvazia a fila e desconecta o cliente; a próxima tarefa abre contexto novo. Contadores de tarefas e tokens zeram |
| Apagar | Limpar + remover a sessão da tela e do registro |
| Limite | `limits.max_active_sessions` (padrão 3, RN-04) conta todas as sessões existentes, incluindo `sistema` |
| Persistência | Só em memória. Reiniciar o server recria apenas `sistema` (SQLite e resume ficam na F4) |
| Criar pela tela | Não. Criar só por voz; a tela lista, limpa e apaga |
| Apagar por voz | O Alfred confirma verbalmente antes de chamar `apagar_sessao` (regra no prompt) |
| Apagar pela tela | Confirmação inline no cartão (segundo clique) |
| Segurança | O Alfred continua sem Bash/Edit/Write (ADR 0003). As tools novas só mexem no registro de sessões |

## Server

### `infra/claude/agents.py` (novo)

```python
class AgentKind(ABC):
    kind: str          # "geral" — chave do registro e sufixo da tool
    label: str         # "Geral" — mostrado na tela e falado
    tools: list[str]   # tools do Claude Code da sessão

    @abstractmethod
    def prompt(self, name: str, cwd: Path) -> str: ...

    @abstractmethod
    def delegate_tool(self, delegate: Delegate) -> sdk.SdkMcpTool[Any]: ...


class GeneralAgent(AgentKind):
    kind, label = "geral", "Geral"
    tools = ["Bash", "Read", "Edit", "Write", "Glob", "Grep"]
    # prompt: o SYSTEM_PROMPT atual de session.py
    # delegate_tool: "delegar_geral", {"tarefa": str, "sessao": str (opcional)}


KINDS: dict[str, AgentKind] = {k.kind: k for k in (GeneralAgent(),)}
```

`Delegate = Callable[[str, str], str]` recebe `(nome_da_sessao, tarefa)` e devolve a frase para o Alfred falar.

Futuro `ImplementationAgent` (fora desta branch): `kind="implementacao"`, `cwd` obrigatório apontando para o projeto, tool `delegar_implementacao(sessao, tarefa)` com `sessao` obrigatória, prompt focado em mudar código e rodar testes do projeto.

### `infra/claude/session.py`

- `CodingSession(bus, name, kind: AgentKind, cwd, model, timeout_s, connect)`. `options()` lê `tools` e `prompt()` do `kind`; o resto (auto mode, `strict_mcp_config`, `setting_sources=[]`) não muda.
- `run()` passa a guardar os tokens do `ResultMessage.usage` (`input_tokens + output_tokens` somados ao total da sessão) e devolve no `Reply` (`tokens: int`, padrão 0).
- `clear()`: desconecta o cliente; o próximo `run` reconecta com contexto novo.
- `close()`: igual a `clear()`, usado ao apagar.

### `controllers/sessions.py`

`Sessions` deixa de embrulhar uma sessão e passa a gerenciar várias:

```python
@dataclass
class Slot:
    session: Session
    queue: asyncio.Queue[str]
    worker: asyncio.Task[None]
    status: Literal["idle", "busy", "error"] = "idle"
    task: str | None = None
    activity: str | None = None      # último agent_progress
    tasks_done: int = 0
    tokens: int = 0
    last_summary: str | None = None
```

| Método | Comportamento |
|---|---|
| `create(kind, name, cwd=None) -> str` | Valida kind no registro, nome livre (RN-01, sem diferenciar maiúsculas) e limite. `cwd` padrão: home. Cria a `CodingSession`, sobe um worker por sessão e publica `session_created`. Devolve frase para o Alfred |
| `delegate(name, task) -> str` | Igual ao atual, por nome. Nome desconhecido devolve "Não existe sessão X" sem levantar |
| `clear(name) -> str` | Cancela o worker (e a tarefa em andamento), esvazia a fila, `session.clear()`, zera contadores, recria o worker, publica `session_cleared` |
| `delete(name) -> str` | Recusa `sistema`. Cancela o worker, `session.close()`, remove o slot, publica `session_deleted` |
| `list() -> list[SessionView]` | Snapshot para a API e para `listar_sessoes` |
| `run()` | Some: cada sessão tem seu worker, criado em `create` |

Os erros de uso (nome duplicado, limite, sessão protegida, tipo desconhecido) viram frases devolvidas para o Alfred falar, não exceções. As alterações em métricas (`task`, `activity`, `tokens`, `status`) publicam `session_status` com o snapshot inteiro da sessão.

`activity` vem do bus: o controller assina `agent_progress` e guarda o `label` (ou o texto, cortado) da sessão correspondente.

`SessionView` (pydantic, em `models/session.py`): `name, kind, label, model, cwd, status, task, activity, queue, tasks_done, tokens, last_summary, protected`.

### Tools do Alfred (`infra/claude/tools.py`)

`alfred_tools(sessions)` monta o MCP in-process com:

- uma tool de delegar por tipo do registro (`kind.delegate_tool(sessions.delegate)`), hoje só `delegar_geral`;
- `criar_sessao(tipo, nome, pasta?)`, `limpar_sessao(nome)`, `apagar_sessao(nome)`, `listar_sessoes()`.

Todas entram em `permissions.ALLOWED`. O prompt do Alfred (`alfred.py`) explica: usar `delegar_geral` para tarefas no computador, sem `sessao` quando o usuário não nomear uma; confirmar com o usuário antes de `apagar_sessao`; `limpar` quando ele pedir para "limpar", "zerar" ou "esquecer" uma sessão.

`activity.py`: labels "Criando sessão", "Limpando sessão", "Apagando sessão", "Listando sessões". `delegar_geral` mantém "Mandando para a sessão" e continua em `SILENT_ACTIVITIES` do router.

### Config

```yaml
limits:
  max_active_sessions: 3
```

Novo modelo `Limits` em `config.py`, opcional, com o padrão acima.

### API (`api/routes/sessions.py`)

| Rota | Resposta |
|---|---|
| `GET /api/sessions` | `list[SessionView]` |
| `POST /api/sessions/{name}/clear` | `SessionView`; 404 se não existir |
| `DELETE /api/sessions/{name}` | 204; 404 se não existir; 409 se protegida |

`Sessions` vai em `app.state.sessions`, como o bus. As rotas usam métodos de `Sessions` que levantam erro tipado (`SessionNotFound`, `SessionProtected`); os métodos das tools capturam esses erros e devolvem frase.

### Eventos

| Evento | Payload |
|---|---|
| `session_created` | `session: SessionView` |
| `session_status` | `session: SessionView` (antes era só nome e status) |
| `session_cleared` | `session: SessionView` |
| `session_deleted` | `name` |

## Web

Primeira versão usou uma faixa de cartões; ficou genérica e não mostrava a ligação com o Alfred. Substituída pela **constelação**:

- Cada sessão é um nó em volta do orb do Alfred: mini orb (mesmos shaders, `src/lib/orb/`) na cor do status (âmbar ocupado, verde livre, vermelho erro), maior e com halo pulsando quando ocupado.
- Rótulo flutuante sob o nó: nome e, embaixo, a atividade atual (ocupado) ou `livre · modelo`.
- Um filamento curvo liga a borda do orb a cada nó. Livre: linha fraca. Ocupado: traço âmbar animado.
- Pulso de luz corre pelo filamento: Alfred → nó quando uma tarefa começa, nó → Alfred quando termina (derivado dos eventos `session_status`).
- Clique no nó abre o painel de detalhes (tipo, modelo, pasta, tarefa, atividade, fila, tarefas, tokens, último resumo, Limpar, Apagar com segundo clique). Esc ou clique fora fecha.
- Posições em elipse em volta do orb, lados primeiro, depois acima e abaixo; presas à área visível. Geometria pura em `features/sessions/lib/constellation.ts`, com testes.
- O dashboard passa a ref do orb do `Assistant` para a `Constellation`; as features não se importam.
- Dados: TanStack Query `GET /api/sessions` + eventos `session_*` do `/ws` no cache. `schema.ts` gerado do OpenAPI.

## Erros

- Falha na sessão: status `error` no cartão, voz "A sessão X não conseguiu terminar a tarefa", próxima tarefa reconecta (já existe). Status volta a `idle` na próxima tarefa iniciada.
- Limpar durante uma tarefa: `CancelledError` no worker não vira erro falado; a voz diz "Sessão X limpa".
- Rota com nome inexistente: 404; o cartão já some pelo evento.

## Testes

- `test_agents.py`: registro, `GeneralAgent.prompt`, `delegate_tool` repassa `(sessao or "sistema", tarefa)`.
- `test_session.py`: `options()` vem do kind; `clear()` desconecta e o próximo `run` reconecta; tokens somados.
- `test_sessions.py`: criar (nome duplicado, limite, tipo desconhecido); delegar por nome e nome desconhecido; limpar cancela tarefa em andamento e esvazia fila; apagar remove e protege `sistema`; eventos publicados.
- `test_alfred.py`/`test_tools.py`: tools de gestão repassam e estão em `ALLOWED`; Alfred continua sem Bash/Edit/Write.
- `test_api_sessions.py`: as três rotas com `TestClient`.
- Web: `make lint` e build; conferência visual no navegador com o modo demo.

## Fora desta branch

`ImplementationAgent`, worktrees, foco e atalho `<nome>:` (RF-11, RF-27), interromper sem limpar (RF-33), persistência e resume (RNF-07), `waiting_permission`, criar sessão pela tela.
