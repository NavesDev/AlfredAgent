# Alfred

Assistente pessoal por voz para a rotina de dev. Tira dúvidas, pesquisa na web, lê e-mail e agenda, controla tarefas e gerencia várias sessões do Claude Code em paralelo — cada uma com nome próprio, presa a um projeto e a um worktree.

```text
"Alfred, backend: cria o endpoint de cancelamento"
"Alfred, tenho e-mail importante hoje?"
"Alfred, manda o backend fazer a tarefa de reembolso"
```

O Alfred escuta continuamente com wake word, transcreve localmente (Whisper), decide para onde mandar o comando, conversa com o Claude na nuvem e responde falando (Kokoro) só a linha de resumo.

> **Status:** pré-MVP. Este repositório contém, por enquanto, a documentação de base. Veja o [roadmap](docs/REQUIREMENTS.md#roadmap-do-mvp).

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
- Opcional: GPU NVIDIA com CUDA (Whisper na GPU libera ~2 GB de RAM)
- Conta Anthropic (API key) e, para e-mail/agenda, credenciais Google

## Começando

> Os comandos abaixo passam a funcionar a partir da fase 1 do roadmap.

```bash
git clone <repo> alfred && cd alfred
make setup        # instala dependências do server e do web
cp server/config.example.yaml server/config.yaml
make dev          # sobe server (voz + API) e Vite juntos
```

Painel em `http://localhost:5173` (dev) ou `http://localhost:8000` (build servido pelo FastAPI).

## Licença

A definir.
