# 0007 — Polymorphic agent kinds and voice-managed sessions

- **Status:** Accepted
- **Date:** 2026-10-11

## Context

ADR 0006 created a fixed `sistema` session and a `delegar(tarefa)` tool tied to it. The roadmap expects other agent kinds (the next one is implementation, tied to a project), and the user wants to create, clear and delete sessions by voice and see each one on screen.

## Decision

- Each agent kind is a subclass of `AgentKind` (`infra/claude/agents.py`) that defines the Claude Code tools, the prompt and Alfred's own delegation tool (`delegar_<kind>`). The `KINDS` registry is the single source of kinds.
- The first kind is `geral` (`GeneralAgent`), which inherits everything from ADR 0006's `sistema` session. `sistema` becomes a session of that kind, created at boot and protected from deletion.
- Lifecycle tools are generic: `criar_sessao`, `limpar_sessao`, `apagar_sessao`, `listar_sessoes`. Clearing cancels the running task and resets the context; deleting also removes the session.
- Sessions live in memory and respect `limits.max_active_sessions`.
- The panel shows a card per session and lets you clear and delete through the API.

## Consequences

- Adding a kind means creating a subclass and registering it; Alfred gets the tool without changing the controller.
- Alfred still has no Bash/Edit/Write (ADR 0003): the new tools only touch the session registry.
- A mail or page can still convince Alfred to create or delete sessions. Deleting needs a spoken confirmation and `sistema` is protected; the worst case is losing a session's context.
- Restarting the server loses sessions created by voice until F4 (SQLite + resume).
