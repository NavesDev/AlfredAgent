# 0004 — Main agent: reads allowed + browser, before the confirmation gate

- **Status:** Superseded by 0005
- **Date:** 2026-10-11

## Context

The main agent opens the Claude Code CLI, which loads the user's MCPs (claude.ai connectors such as Gmail, Calendar and Drive, and plugins such as chrome-devtools). With no explicit rule, the non-interactive mode denied every call, and the model still advertised capabilities it did not have. The voice/panel confirmation gate (phase 5) does not exist yet, so the "tainted turn" rule has no way to ask for confirmation.

## Decision

Policy in `server/infra/claude/permissions.py`, with `permission_mode="dontAsk"`:

- **Allowed without confirmation:** WebSearch, WebFetch, reading Gmail and Calendar, and the whole chrome-devtools server (open pages, click, read, run JS).
- **Hidden and denied:** everything that writes to Gmail and Calendar, the browser's `upload_file`, Drive, Claude Docs and other known MCPs.
- Any tool not listed is denied, including MCPs installed later.
- ADR 0003 still holds: no Bash, Edit or Write.

## Consequences

- Alfred now reads mail, calendar and the web, and opens pages in Chrome by voice.
- **Accepted risk:** in the same turn it may read a mail or page and act in the logged-in browser. An injected instruction could navigate to a site and leak content through the URL. The prompt tells it to treat mail and pages as data, but that mitigates, it does not prevent.
- When the phase 5 gate exists, the browser will need confirmation on tainted turns, and this ADR is superseded.
