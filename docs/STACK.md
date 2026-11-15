# Stack

Tecnologias do Alfred e o motivo de cada escolha. Mudanças relevantes viram um [ADR](adr/).

## Visão geral

| Camada | Tecnologia |
|---|---|
| Runtime do server | Python 3.11+, asyncio, um processo só |
| Gerenciador de pacotes (Python) | uv + `pyproject.toml` |
| Agentes | Claude Agent SDK (Python), usando o CLI `claude` logado (harness do Claude Code) |
| Modelos | Sonnet (padrão), Haiku (perguntas simples e resumos de fallback) |
| Integrações | MCP Gmail, MCP Google Calendar, WebSearch/WebFetch nativos do SDK |
| Tools internas | Servidor MCP in-process (tools Python definidas no próprio código) |
| Wake word | openWakeWord (modelo `alfred.onnx` treinado) |
| VAD | Silero VAD |
| STT | faster-whisper `large-v3-turbo`, `int8_float16` na GPU sob demanda, `int8` na CPU ([ADR 0010](adr/0010-voice-models-on-demand-gpu.md)) |
| TTS | Kokoro (`pf_dora` ou `pm_alex`), GPU sob demanda ou CPU |
| Áudio I/O | sounddevice (PortAudio) |
| Fuzzy match | rapidfuzz |
| Persistência | SQLite |
| API | FastAPI + Uvicorn, WebSocket nativo |
| Front | React + TypeScript + Vite |
| UI | Tailwind CSS + shadcn/ui; esfera do Alfred: Strands (React Bits, WebGL2) com versão em CSS |
| Estado do servidor no front | TanStack Query |
| Cliente tipado | openapi-typescript + openapi-fetch (tipos gerados do OpenAPI do FastAPI) |
| Rotas | React Router |
| Testes | pytest + pytest-asyncio (server), Vitest + Testing Library (web) |
| Lint/format | ruff + mypy (server), ESLint + Prettier (web) |
| Gerenciador de pacotes (Node) | pnpm |
| Desktop | Tauri v2 (WebKitGTK no Linux), carregando o `apps/web` ([ADR 0012](adr/0012-desktop-shell-tauri.md)) |

## Server

**Python 3.11+ com asyncio.** O ecossistema de voz local (faster-whisper, Kokoro, openWakeWord, Silero) é Python, e o Agent SDK tem SDK Python de primeira classe. Um processo só simplifica o MVP: o event bus fica em memória e não há IPC.

**Threads para áudio.** Captura, STT e TTS são CPU/GPU-bound ou bloqueantes. Rodam em threads próprias e conversam com o loop via `asyncio.Queue` / `loop.call_soon_threadsafe`, para não travar os agentes.

**Claude Agent SDK.** Dá sessões com resume, `canUseTool` para o gate de permissões, auto mode, WebSearch/WebFetch e servidores MCP (externos e in-process). Cada sessão nomeada é uma instância do SDK com `cwd` no ambiente.

**SQLite.** Um usuário, uma máquina, poucas escritas. Sem servidor de banco para manter. Acesso via `sqlite3`/`aiosqlite` direto ou SQLModel — decisão na fase 3.

**FastAPI.** Async nativo (mesmo loop do resto), WebSocket embutido e OpenAPI automático, que alimenta os tipos do front.

**rapidfuzz.** Whisper erra nomes próprios ("backend" → "bequi end"). Apelidos + fuzzy match com corte ~85% resolvem sem chamar modelo.

## Voz

| Componente | RAM aprox. | Quando pesa |
|---|---|---|
| openWakeWord + Silero | ~150 MB | Sempre ligado, CPU quase zero |
| faster-whisper large-v3-turbo | ~1,1 GB de VRAM (`int8_float16`), ~2 GB de RAM no fallback de CPU | Da wake word até 30 s depois do último comando |
| Kokoro | ~350 MB de VRAM ou ~400 MB de RAM | Até 10 s depois da última fala |
| Contextos CUDA | ~470 MB de VRAM | Enquanto o Alfred roda |
| Sessões Claude Code (3) | ~0,5–1 GB | Enquanto rodam tarefas |

- **faster-whisper `large-v3-turbo` int8:** melhor relação qualidade/velocidade em pt. `initial_prompt` com o jargão (Spring, Liferay, endpoint, worktree, commit, nomes das sessões) melhora termos técnicos. Se a máquina apertar, trocar para `medium` é uma linha no config.
- **Kokoro:** TTS local leve, com vozes em português. 8 s de fala em 0,14 s na GPU, 2,3 s na CPU.
- **GPU sob demanda:** a GPU é dividida com o serviço de imagens. Whisper e Kokoro sobem quando usados, soltam a VRAM ociosos e caem para a CPU se ela estiver ocupada ([ADR 0010](adr/0010-voice-models-on-demand-gpu.md)). torch vem do índice `cu126`, cujos wheels `nvidia-*` (cuBLAS, cuDNN 9) também servem ao CTranslate2.
- **openWakeWord:** permite treinar a wake word própria ("Alfred") e roda em CPU com custo quase zero.

## Web

- **Vite + React + TS:** dev server rápido, build estático servido pelo FastAPI em produção (porta única).
- **TanStack Query:** todo estado do servidor; o WebSocket só atualiza o cache. Sem Redux/Zustand.
- **openapi-typescript + openapi-fetch:** `api/schema.ts` gerado do FastAPI; contrato único entre server e front, sem tipos duplicados à mão.
- **shadcn/ui + Tailwind:** componentes copiados para o repo, sem dependência de biblioteca de UI fechada.
- **Strands (React Bits):** a esfera do Alfred, copiada para o repo (MIT + Commons Clause). WebGL2 puro, sem three.js; onde não há WebGL2 entra a versão em CSS. Direção visual em [DESIGN.md](DESIGN.md).

## Versões mínimas

| Ferramenta | Versão |
|---|---|
| Python | 3.11 |
| Node.js | 20 LTS |
| pnpm | 9 |
| Git | 2.40 |
| Driver NVIDIA (opcional) | CUDA 12+ |

## Configuração

Arquivo único `server/config.yaml` (versionado apenas como `config.example.yaml`). Pontos principais:

```yaml
whisper:
  model: large-v3-turbo
  device: cuda          # cuda | cpu; fallback para CPU com a GPU ocupada
  compute_type: int8_float16
  language: pt
  initial_prompt: "Spring, Liferay, endpoint, worktree, commit, backend, frontend"
  idle_s: 30            # solta a GPU depois disso sem uso

kokoro:
  voice: pf_dora        # ou pm_alex
  speed: 1.1
  device: cuda
  idle_s: 10

wakeword:
  name: Alfred
  model: wakeword/alfred.onnx  # treinado em wakeword/train
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
  timeout_s: 60                    # sem resposta = negado
```

Autenticação do Claude vem do login do Claude Code. Segredos (credenciais Google, API key se um dia trocar) ficam em variáveis de ambiente / `.env`, nunca no YAML.
