# Alfred

Assistente pessoal por voz para a rotina de dev. Tira dúvidas, pesquisa na web, lê e-mail e agenda, controla tarefas e gerencia várias sessões do Claude Code em paralelo — cada uma com nome próprio, presa a um projeto e a um worktree.

```text
"Alfred, backend: cria o endpoint de cancelamento"
"Alfred, tenho e-mail importante hoje?"
"Alfred, manda o backend fazer a tarefa de reembolso"
```

O Alfred escuta continuamente com wake word, transcreve localmente (Whisper), decide para onde mandar o comando, conversa com o Claude na nuvem e responde falando (Kokoro) só a linha de resumo.

> **Status:** fase 1 (voz de ponta a ponta). Wake word: **"Alfred"** (modelo próprio, ainda em validação com voz real). Veja o [roadmap](docs/REQUIREMENTS.md#roadmap-do-mvp).

## Objetivos

- **Hands-free:** escuta contínua com wake word, sem teclado.
- **Um ponto de entrada só:** o mesmo "Alfred" serve pro dia a dia e pra código.
- **Voz 100% local:** Whisper + Kokoro; raciocínio e integrações rodam na nuvem.
- **Organizado por voz:** projetos, worktrees, sessões nomeadas e tarefas.
- **Leve:** alvo de ≤ 3 GB de RAM no total, rodando junto dos ambientes de dev.

## Documentação

| Documento | Conteúdo |
|---|---|
| [docs/SPEC.md](docs/SPEC.md) | Spec original do produto (fonte da verdade) |
| [docs/REQUIREMENTS.md](docs/REQUIREMENTS.md) | Requisitos funcionais, não funcionais, regras de negócio e roadmap |
| [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) | Componentes, fluxo de um comando, modelo de dados, event bus, permissões |
| [docs/STACK.md](docs/STACK.md) | Tecnologias escolhidas, versões e motivo de cada uma |
| [docs/adr/](docs/adr/) | Registro de decisões de arquitetura (ADRs) |
| [CONTRIBUTING.md](CONTRIBUTING.md) | Como rodar, convenções de código, commits e PRs |

## Estrutura do repositório

```text
alfred/
├── server/        # Python 3.11+: voz + agentes + API (FastAPI)
├── apps/
│   ├── web/       # React + TypeScript + Vite (painel)
│   └── desktop/   # Tauri (futuro)
├── docs/          # spec, requisitos, arquitetura, stack, ADRs
└── Makefile       # make dev = server + vite juntos
```

Detalhes em [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md#estrutura-de-pastas).

## Requisitos de máquina

- Linux ou macOS com microfone e alto-falante
- Python 3.11+ e [uv](https://docs.astral.sh/uv/)
- Node.js 20+ e pnpm
- Git 2.40+ (worktrees)
- Sistema: `libportaudio2`, `espeak-ng`
- Opcional: GPU NVIDIA com driver CUDA 12+ (Whisper em ~0,3 s em vez de ~6 s; cai para a CPU se a GPU estiver ocupada)
- [Claude Code](https://claude.com/claude-code) instalado e logado (`claude`)
- Para e-mail/agenda: credenciais Google

## Começando

```bash
sudo apt install libportaudio2
git clone <repo> alfred && cd alfred
make setup        # instala dependências (uv sync + pnpm install)
cp server/config.example.yaml server/config.yaml
make dev          # sobe voz + agente + API + painel (Vite)
```

A primeira execução baixa os modelos (Whisper ~1,6 GB, Kokoro ~330 MB). Diga **"Alfred"**, espere um instante e faça a pergunta. Se não acordar bem, `wakeword.model: hey_jarvis` no `config.yaml` volta ao modelo pronto.

Painel em http://localhost:5173: um orbe 3D que reage ao estado (ouvindo, transcrevendo, pensando, falando) e ao volume do microfone/voz. O botão **Transcrição** (ou tecla `T`) abre o histórico com o que foi ouvido, as tools usadas, o que foi falado, a resposta completa e os tempos (STT, 1ª fala, resposta); **Copiar** exporta em Markdown para avaliar. **Demo** simula uma conversa sem o servidor.

Eventos crus em tempo real (estado da voz, nível de áudio, progresso do agente):

```bash
websocat ws://localhost:8000/ws
```

## Licença

A definir.
