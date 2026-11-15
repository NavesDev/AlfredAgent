# 0003 — Main agent without Bash or Edit

- **Status:** Accepted
- **Date:** 2026-10-01

## Context

The main agent reads untrusted external content (mail, web pages). That content may carry prompt injection.

## Decision

The `alfred` agent gets no Bash, Edit or Write. Repository work is always delegated to a named session through `delegar`. Besides, a turn that read mail or the web becomes "tainted": any action with side effects in it needs confirmation through the `tainted_turn` channel.

## Consequences

- Whoever reads external content never runs commands directly.
- `delegar` becomes the checkpoint: it is an action with side effects and goes through the tainted-turn gate.
- Simple flows ("create a notes file") get one step longer.
