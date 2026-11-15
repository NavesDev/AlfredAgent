# 0008 — Implementation agent with the full Claude Code harness

- **Status:** Accepted
- **Date:** 2026-10-11

## Context

`geral` sessions (ADR 0006, 0007) run isolated. They do not read the user's settings (`setting_sources=[]`), load no MCPs (`strict_mcp_config`) and use a fixed tool list. To work on a project's code, that is not enough: the repository's CLAUDE.md, the skills, plugins, hooks and MCPs the user relies on in everyday Claude Code (docs, browser, design) are missing.

## Decision

- New `implementacao` kind (`ImplementationAgent` in `infra/claude/agents.py`), always tied to a project workspace.
- The kind uses the `claude_code` preset prompt with an `append` (session name, project, `RESUMO:` line) and loads:
  - `setting_sources=["user", "project", "local"]`;
  - `skills="all"`;
  - every tool, with no fixed list;
  - `permission_mode="auto"`.
- All of the user's MCPs are on by default. The settings screen keeps a list of disabled servers, which becomes `disallowed_tools=["mcp__<name>"]`.
- The prompt says to use external MCPs (mail, calendar, browser) only when the task explicitly asks for it.

## Consequences

- The implementation session behaves like Claude Code in the user's terminal, with the same context and the same tools.
- **Accepted risk:** this session can read external content (mail or web, through MCP) and run commands in the same turn. That is the scenario ADRs 0003 and 0006 avoid for Alfred and for `sistema`.
- **Mitigations:**
  - the auto mode classifier;
  - the prompt rule about external MCPs;
  - the disabled-MCP list;
  - Alfred still has no Bash/Edit/Write and describes tasks in its own words.
- F5's configurable permissions (denylist, per-channel confirmation) will apply to this kind too when they land.
