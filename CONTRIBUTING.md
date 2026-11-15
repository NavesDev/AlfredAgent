# Contributing

How to work on Alfred. Read [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) first.

## Setup

Prerequisites in [README.md](README.md#requirements).

```bash
make setup     # uv sync (server) + pnpm install (web, desktop)
make dev       # server + Vite together
make test      # pytest + vitest
make lint      # ruff + mypy + oxlint/tsc + clippy
make fmt       # ruff format + prettier + cargo fmt
```

Local config:

```bash
cp server/config.example.yaml server/config.yaml
cp .env.example .env    # ANTHROPIC_API_KEY, Google credentials
```

`config.yaml` and `.env` are never committed.

## Language

- **Everything in the repo:** English (code, names, config, commits, PRs, docs, README, CHANGELOG).
- **Text spoken or shown to the user:** Brazilian Portuguese (pt-BR).

## Server conventions (Python)

- Python 3.11+, type hints on everything public; `mypy --strict`.
- `ruff` for lint and format (100-character lines).
- Respect the layers: `models` never imports `infra`; only `controllers` joins `models` and `infra`; `api` talks to `controllers`. Details in [ARCHITECTURE.md](docs/ARCHITECTURE.md).
- Nothing blocking on the asyncio loop. Audio, STT and TTS work stays in the `infra/audio` threads.
- Decoupled parts talk through `events.py`, not direct calls between `talker` and `api`.
- Tests with `pytest` + `pytest-asyncio`. Claude, the microphone and git are mocked in unit tests; tests that need hardware or network are marked `@pytest.mark.integration`.

## Web conventions (TypeScript)

- Organized by feature (`src/features/<feature>/{pages,components,hooks}`).
- API access **only** in the feature hooks, through TanStack Query.
- A feature never imports from another feature (exception: `dashboard`).
- `src/api/schema.ts` is generated: `make gen-api`. Do not edit by hand.
- No global state besides TanStack Query.

## Branches

- `main` always works.
- Branches: `feat/<topic>`, `fix/<topic>`, `docs/<topic>`, `chore/<topic>`, `refactor/<topic>`.

## Commits

[Conventional Commits](https://www.conventionalcommits.org/), imperative mood. They drive the version and the CHANGELOG, so pick the type with care:

```text
feat(router): add fuzzy match for session aliases
fix(talker): drop queued speech on barge-in
docs(architecture): describe permission flow
```

Suggested scopes: `server`, `router`, `sessions`, `alfred`, `permissions`, `audio`, `listener`, `talker`, `api`, `web`, `desktop`, `docs`, `build`.

## Pull requests

- One subject per PR, small enough to review in one go.
- Description: what, why, how to test. Reference the requirement (`RF-xx`, `RNF-xx`) when there is one.
- `make lint test` passing.
- Changed behavior described in `docs/`? Update the doc in the same PR.
- New architecture decision, or one that contradicts the spec? Open an ADR in `docs/adr/`.

## Versions and releases

- [SemVer](https://semver.org/), one version for the whole repo (server, web and desktop), tagged `vX.Y.Z` on `main`.
- [release-please](https://github.com/googleapis/release-please) ([workflow](.github/workflows/release-please.yml), [config](release-please-config.json)) keeps a release PR open with the next version and its CHANGELOG, built from the commits merged into `main`. Before 1.0: `feat` bumps the minor, `fix` bumps the patch, a breaking change (`feat!:`) bumps the minor.
- Merging the release PR bumps the versions in `server/pyproject.toml`, `server/uv.lock`, `apps/web/package.json`, `Cargo.toml`, `Cargo.lock` and `tauri.conf.json`, then creates the tag and the GitHub release. The lockfiles matter: the self-update refuses a dirty checkout, and `uv sync` or the build would rewrite them otherwise.
- `docs`, `chore` and `test` commits stay out of the CHANGELOG.

## ADRs

Copy [docs/adr/0000-template.md](docs/adr/0000-template.md) to `docs/adr/NNNN-short-title.md`, numbered in sequence. An accepted ADR is not edited; a new decision supersedes it (`Superseded by NNNN`).

## Security

- Never commit keys, tokens, `config.yaml` or `.env`.
- Changes to `infra/claude/permissions.py`, the denylist or the main agent's tools need careful review and a test covering the denied case.
- The main agent never gets Bash or Edit ([ADR 0003](docs/adr/0003-main-agent-without-exec-tools.md)).
