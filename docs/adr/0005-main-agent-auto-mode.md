# 0005 — Main agent in Claude Code's auto mode

- **Status:** Accepted
- **Date:** 2026-10-11
- Supersedes [0004](0004-main-agent-read-only-plus-browser.md)

## Context

With ADR 0004's fixed list, Alfred could not act (send mail, create an event, use Drive) and the phase 5 confirmation gate does not exist yet. A hole also showed up: through the browser it read local files with `file://`.

## Decision

- `permission_mode="auto"`: Gmail/Calendar reads, web and browser run right away (`ALLOWED`); any other tool goes to the auto mode classifier, which approves or denies each call.
- Fixed limits, outside the classifier:
  - no Bash, Edit or Write (ADR 0003);
  - a `PreToolUse` hook (`block_local_urls`) denies any `url` that is not http/https, in any tool;
  - the browser's `upload_file` is hidden.
- Auto mode requires Sonnet or Opus; with Haiku the CLI falls back to the default mode and denies everything outside `ALLOWED`.

## Consequences

- Alfred can send mail and change the calendar and Drive if the classifier approves, without your confirmation.
- Prompt injection in a mail or page remains the main risk; the defense becomes the classifier plus the instruction to treat external content as data.
- When the phase 5 gate exists, sensitive actions (`send_email` etc.) should go back to asking for confirmation on the configured channel.
