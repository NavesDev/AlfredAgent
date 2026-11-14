# CLAUDE.md

Alfred: voice assistant (Python server) that routes spoken commands to a main agent or to named Claude Code sessions, plus a React web panel.

## Read first

- `docs/SPEC.md` — product spec (source of truth)
- `docs/REQUIREMENTS.md` — RF/RNF/RN ids, roadmap, open questions
- `docs/ARCHITECTURE.md` — layers, data model, events, permissions
- `CONTRIBUTING.md` — conventions
- `docs/DESIGN.md` — visual direction of the web panel

## Rules

- Code, identifiers, config keys, commits: English. Docs and user-facing speech: pt-BR.
- Server layers: `models` (no voice/Claude) → `infra` (external world) → `controllers` (only place joining both) → `api`. Don't add extra layers or interfaces.
- Never block the asyncio loop; audio/STT/TTS live in threads in `infra/audio`.
- The main agent (`infra/claude/alfred.py`) must never get Bash/Edit/Write tools (ADR 0003).
- Web: API access only in feature hooks (TanStack Query); features never import other features (except `dashboard`); `src/api/schema.ts` is generated.
- Commands: `make setup | dev | test | lint | fmt | gen-api`.
