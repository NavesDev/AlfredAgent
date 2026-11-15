# 0006 — Computer tasks go to the "sistema" session

- **Status:** Accepted
- **Date:** 2026-10-11

## Context

Alfred has no Bash (ADR 0003), so it could not do anything on the computer (rotate the screen, count projects, handle files) and even read files through `file://` in the browser. Giving it Bash would put whoever reads mail/web and whoever runs commands in the same agent.

## Decision

- Brings part of phase 3 forward: a named session `sistema` (`infra/claude/session.py`), a persistent Claude Code with `Bash`, `Read`, `Edit`, `Write`, `Glob`, `Grep`, `cwd` in the home and `permission_mode="auto"`.
- The session loads no MCPs (`strict_mcp_config`) or user settings (`setting_sources=[]`), and has no WebSearch/WebFetch: external content never reaches it directly.
- Alfred gets the in-process tool `delegar(tarefa)` (`infra/claude/tools.py`). It queues the task in `controllers/sessions.py` and returns at once; the session runs in the background, one task at a time, and the summary is spoken when it finishes.
- Alfred's prompt tells it to describe the task in its own words, never pasting text from mail or pages.

## Consequences

- Alfred now does computer tasks by voice without blocking the conversation.
- Remaining risk: a mail or page may convince Alfred to delegate something bad. Mitigations: the rule against pasting external content and the auto mode classifier in the session.
- A single session for now; per-project sessions, worktrees and the `max_active_sessions` limit stay in phase 3.
