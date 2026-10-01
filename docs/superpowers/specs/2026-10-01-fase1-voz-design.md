# Fase 1 — Voz de ponta a ponta (design)

- **Data:** 2026-10-01
- **Status:** Aprovado
- **Requisitos cobertos:** RF-01, RF-02, RF-03, RF-04, RF-13, RF-20, RF-28; RNF-01, RNF-05, RNF-08, RNF-09 (parcial: eventos + `/ws`)

## Objetivo

Falar com o Alfred e ouvir a resposta: wake word → gravação → Whisper → agente principal (Claude via harness do Claude Code) → Kokoro lendo só o `RESUMO:`. Ao mesmo tempo, publicar eventos em tempo real num `/ws` para o front poder animar estados desde já.

## Decisões

| Tema | Decisão |
|---|---|
| Wake word | Modelo pré-treinado `hey_jarvis` do openWakeWord até o `alfred.onnx` ficar pronto. Script de treino do `alfred.onnx` faz parte desta fase |
| Autenticação Claude | `claude-agent-sdk` usando o CLI `claude` já logado (assinatura). Sem `ANTHROPIC_API_KEY` |
| Ritmo da conversa | Toda fala começa pela wake word; sem janela de follow-up |
| Pipeline | Um processo asyncio; captura, STT e TTS em threads; event bus em memória |
| Front | Sem painel; `GET /ws` mínimo despejando o bus em JSON |
| Fora desta fase | SQLite, interrupção "para", barge-in, tools do agente (web/e-mail), fallback Haiku, painel |

## Componentes

Todos em `server/`.

| Arquivo | Responsabilidade | Depende de |
|---|---|---|
| `errors.py` | Hierarquia `AlfredError` → `ConfigError`, `DependencyError`, `AudioError`, `AgentError` (ver [ARCHITECTURE.md](../../ARCHITECTURE.md#erros)) | — |
| `main.py` | Carrega config, cria bus, sobe threads de áudio, agente e Uvicorn no mesmo loop | tudo |
| `config.py` | Modelo pydantic do `config.yaml`; `load_config(path) -> Config` | pydantic, pyyaml |
| `events.py` | `EventBus`: `publish(type, **data)` (seguro de qualquer thread), `subscribe() -> asyncio.Queue`, `unsubscribe(q)` | asyncio |
| `controllers/router.py` | `Router.handle(text, source)`: na fase 1 entrega tudo ao agente e manda o resumo ao talker | events, infra |
| `infra/audio/listener.py` | Thread: microfone 16 kHz mono, frames de 80 ms → openWakeWord → grava com Silero VAD até 800 ms de silêncio (máx. 15 s) → faster-whisper → callback `on_transcript(text)` | openwakeword, faster-whisper, sounddevice |
| `infra/audio/talker.py` | Thread: consome fila de frases → Kokoro (`lang_code='p'`, voz/velocidade do config) → toca. Expõe `say(text)` e `is_speaking` | kokoro, sounddevice |
| `infra/claude/alfred.py` | `AlfredAgent.ask(text) -> Reply`: `ClaudeSDKClient`, modelo Sonnet, sem tools, system prompt pt-BR exigindo `RESUMO:`; streaming vira `agent_progress` | claude-agent-sdk, events, state |
| `infra/claude/summary.py` | `extract_summary(text) -> str`: linha `RESUMO:`; senão primeira frase; remove markdown/código | — |
| `infra/claude/state.py` | Lê/grava `data/alfred_state.json` `{date, claude_session_id}`; dia novo = sessão nova | — |
| `api/app.py` | FastAPI: `GET /health`, monta `ws.py` | fastapi |
| `api/ws.py` | `GET /ws`: assina o bus e envia cada evento como JSON | events |
| `wakeword/train/` | Script que gera `wakeword/alfred.onnx` (amostras Piper pt-BR e en, frases "Alfred"/"Alfredo") com o pipeline de treino do openWakeWord | openwakeword, piper |

As camadas seguem [ARCHITECTURE.md](../../ARCHITECTURE.md): `infra` não importa `controllers`; `router` é quem liga listener → agente → talker.

## Eventos

Formato no fio: `{"type": str, "ts": float, ...dados}`.

| `type` | Dados | Quando |
|---|---|---|
| `voice_state` | `state`: `idle`, `listening`, `transcribing`, `thinking`, `speaking` | Cada transição |
| `audio_level` | `source`: `mic` ou `tts`; `level`: 0–1 (RMS normalizado) | ~15×/s em `listening` e `speaking` |
| `transcript` | `text`, `source`: `voice` | Whisper terminou com texto não vazio |
| `agent_progress` | `session`: `alfred`; `kind`: `text` ou `tool`; `content` | Cada bloco do stream do SDK |
| `alfred_reply` | `session`, `text`, `summary` | Resposta final |
| `error` | `where`, `message` | Falha tratada |

## Fluxo

1. `idle`: listener alimenta o openWakeWord; score ≥ threshold → `listening`.
2. Grava até 800 ms de silêncio no VAD ou 15 s; publica `audio_level` do mic.
3. `transcribing`: faster-whisper (`language=pt`, `initial_prompt` do config). Texto vazio → `idle`.
4. `transcript` → `Router.handle`.
5. `thinking`: `AlfredAgent.ask` faz streaming (`agent_progress`) até o resultado.
6. `alfred_reply` → `talker.say(summary)` → `speaking` → `idle`.

Enquanto `talker.is_speaking`, o listener descarta detecções da wake word (evita autodisparo). Barge-in é fase 5.

## Sessão diária do agente

- Ao iniciar o primeiro `ask` do dia, se `state.date == hoje`, retoma com `resume=claude_session_id`.
- Caso contrário, abre sessão nova e grava o novo `claude_session_id` com a data de hoje.
- "Dia" usa o fuso local da máquina, virando à meia-noite. Conversa em andamento na virada continua na sessão em que começou.

## Tratamento de erros

Exceções em camadas e fail-fast conforme [ARCHITECTURE.md](../../ARCHITECTURE.md#erros). Modelos são carregados na inicialização.

| Situação | Comportamento |
|---|---|
| Transcrição vazia/ruído | Volta a `idle` sem falar |
| SDK/CLI falha ou passa de 60 s | Publica `error`, fala "Não consegui falar com o Claude agora", volta a `idle` |
| CLI `claude` ausente ou deslogado | Erro claro na inicialização, processo encerra |
| Microfone indisponível | Erro claro na inicialização, processo encerra |
| Exceção dentro de thread de áudio | Loga, publica `error`, estado `idle`, thread continua |
| Resume com `claude_session_id` inválido | Descarta, abre sessão nova, grava novo id |

## Configuração (acréscimos)

```yaml
wakeword:
  model: hey_jarvis          # nome pré-treinado ou caminho para .onnx
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

## Testes

Unitários (pytest + pytest-asyncio), sem hardware nem rede:

- `events`: publish de outra thread chega ao subscriber; unsubscribe para entrega.
- `summary`: com `RESUMO:`, sem `RESUMO:`, com bloco de código, resposta vazia.
- `config`: carrega `config.example.yaml`; erro claro em campo inválido.
- `state`: mesmo dia retoma id; dia novo gera sessão nova; arquivo ausente.
- `listener`: máquina de estados com wake word, VAD e Whisper falsos injetados (sequência de frames → transições e `transcript`).
- `alfred`: cliente SDK fake emitindo stream → `agent_progress` + `Reply` com resumo; timeout → erro.
- `router`: transcript → agente fake → talker fake recebe o resumo.
- `ws`: TestClient conecta e recebe evento publicado.

Smoke manual: "Hey Jarvis, qual a diferença entre JWT e sessão?" → resposta falada em 1–2 frases; `websocat ws://localhost:8000/ws` mostra a sequência de eventos.

## Setup

- `uv` (gerenciador Python).
- Sistema: `libportaudio2`, `espeak-ng`.
- Python: `claude-agent-sdk`, `faster-whisper`, `kokoro`, `openwakeword`, `sounddevice`, `numpy`, `pydantic`, `pyyaml`, `fastapi`, `uvicorn`; dev: `pytest`, `pytest-asyncio`, `httpx`, `ruff`, `mypy`.
- Whisper em CPU (máquina sem GPU NVIDIA): `device: cpu`, `compute_type: int8`.

## Riscos

- **Termos de uso:** usar a assinatura do Claude via Agent SDK em projeto próprio é zona cinzenta; se virar problema, trocar para `ANTHROPIC_API_KEY` é só configurar o ambiente.
- **Latência em CPU:** large-v3-turbo int8 em 12 cores deve ficar em ~1–3 s por comando curto; se passar disso, `medium` ou `small`.
- **Treino da wake word:** baixa alguns GB e leva horas em CPU; roda à parte e não bloqueia o resto da fase.
- **Pronúncia:** Kokoro em pt-BR depende do `espeak-ng`; validar no smoke.
