# Contribuindo

Guia para trabalhar no Alfred. Leia antes [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).

## Ambiente

Pré-requisitos em [README.md](README.md#requisitos-de-máquina).

```bash
make setup     # uv sync (server) + pnpm install (web)
make dev       # server + Vite juntos
make test      # pytest + vitest
make lint      # ruff + mypy + eslint
make fmt       # ruff format + prettier
```

Config local:

```bash
cp server/config.example.yaml server/config.yaml
cp .env.example .env    # ANTHROPIC_API_KEY, credenciais Google
```

`config.yaml` e `.env` nunca são commitados.

## Idioma

- **Código, nomes de arquivo, pastas, config, identificadores, commits e PRs:** inglês.
- **Documentação em `docs/`, README e textos falados/exibidos ao usuário:** português (pt-BR).

## Convenções do server (Python)

- Python 3.11+, type hints em tudo que é público; `mypy --strict` no CI.
- `ruff` para lint e format (linha de 100).
- Respeitar as camadas: `models` não importa `infra`; só `controllers` junta `models` com `infra`; `api` fala com `controllers`. Detalhes em [ARCHITECTURE.md](docs/ARCHITECTURE.md#camadas-do-server).
- Nada bloqueante no loop asyncio. Trabalho de áudio/STT/TTS fica nas threads do `infra/audio`.
- Comunicação entre partes desacopladas via `events.py`, não chamada direta entre `talker` e `api`.
- Testes com `pytest` + `pytest-asyncio`. Claude, microfone e git são mockados nos testes unitários; testes que precisam de hardware ou rede ficam marcados com `@pytest.mark.integration`.

## Convenções do web (TypeScript)

- Organização por feature (`src/features/<feature>/{pages,components,hooks}`).
- Acesso à API **só** nos hooks da feature, via TanStack Query.
- Feature não importa de outra feature (exceção: `dashboard`).
- `src/api/schema.ts` é gerado: `make gen-api`. Não editar à mão.
- Sem estado global além do TanStack Query.
- Componentes de UI base via shadcn em `src/components/ui/`.

## Branches e worktrees

- `main` sempre funcional.
- Branches: `feat/<tema>`, `fix/<tema>`, `docs/<tema>`, `chore/<tema>`, `refactor/<tema>`.
- Trabalho paralelo em worktrees é bem-vindo (é o próprio caso de uso do Alfred).

## Commits

[Conventional Commits](https://www.conventionalcommits.org/), em inglês, no imperativo:

```text
feat(router): add fuzzy match for session aliases
fix(talker): drop queued speech on barge-in
docs(architecture): describe permission flow
```

Escopos sugeridos: `server`, `router`, `sessions`, `alfred`, `permissions`, `audio`, `listener`, `talker`, `api`, `web`, `docs`, `build`.

## Pull requests

- Um assunto por PR, pequeno o suficiente para revisar de uma vez.
- Descrição: o quê, por quê, como testar. Referencie o requisito (`RF-xx`, `RNF-xx`) quando houver.
- `make lint test` passando.
- Mudou comportamento descrito em `docs/`? Atualize o doc no mesmo PR.
- Decisão de arquitetura nova ou que contraria a spec? Abra um ADR em `docs/adr/`.

## ADRs

Copie [docs/adr/0000-template.md](docs/adr/0000-template.md) para `docs/adr/NNNN-titulo-curto.md`, numeração sequencial. ADR aceito não é editado; uma decisão nova o substitui (`Superseded by NNNN`).

## Segurança

- Nunca commitar chaves, tokens, `config.yaml` ou `.env`.
- Mudanças em `infra/claude/permissions.py`, na denylist ou nas tools do agente principal exigem revisão cuidadosa e teste cobrindo o caso negado.
- O agente principal não pode ganhar Bash nem Edit (ver [ADR 0003](docs/adr/0003-main-agent-without-exec-tools.md)).
