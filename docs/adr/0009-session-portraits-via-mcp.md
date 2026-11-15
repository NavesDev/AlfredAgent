# 0009 — Session portraits painted by an agent with the user's MCPs

- **Status:** Accepted
- **Date:** 2026-11-14

## Context

The panel shows a picture per session: a clay-style 3D portrait (`docs/DESIGN.md`), with the monogram while it does not exist. The user already has image generators as MCP servers in Claude Code (today `imagens-local`, on the GPU), and may swap or add others. Tying Alfred to one service's API would require new code for each generator.

## Decision

- **Who paints:** a one-question agent (`infra/claude/portrait.py`, the Agent SDK's `query()`), with Alfred's model. It gets a simple prompt (session name, kind, project and workspace with their descriptions, portrait style) and uses whatever image generator it finds among the user's MCPs.
- **Tools:** MCPs only. `tools=[]` removes every native tool (no Bash, Read, Write, web). The server reads Claude Code's user-scope MCPs (`mcpServers` in `~/.claude.json`) and passes only those (`mcp_servers` + `strict_mcp_config`), with `setting_sources=[]`: no hooks, plugins, CLAUDE.md or claude.ai connectors (Gmail, Drive). `allowed_tools` allows the loaded servers and `permission_mode="dontAsk"` denies the rest.
- **Favorite generator (`image_mcp`, in `app_settings`):**
  - set: only that server is loaded;
  - empty ("Automático"): loads every enabled user server (outside `mcp_disabled`) and the model picks the generator. On the first successful generation, the server used becomes the favorite. The panel changes the favorite or goes back to "Automático", picking among the user servers (`image_mcp_servers`).
- **Image:** comes from the image block in the MCP tool result; if the generator only returns a path, the agent answers `IMAGEM: <path>`. The server accepts only PNG, JPEG or WebP (by the leading bytes), up to 20 MB, and copies it to `data/portraits/<session id>.<ext>`.
- **When:** on session creation and, at boot, for sessions without a portrait. One generation at a time, in a background queue (`controllers/portraits.py`) that never blocks creation. `POST /api/sessions/{name}/portrait` asks again.
- **Failure** (service down, no generator, invalid image): the monogram stays and the error goes to the log; it tries again on the next boot or on request.
- **Serving:** `GET /api/sessions/{name}/portrait`; `SessionView.portrait` carries that URL with `?v=<mtime>` (or `null`). The `portrait_updated` event makes the session republish its status.

## Consequences

- Switching generators means configuring another MCP in Claude Code, without changing Alfred.
- **Accepted risk:** with no favorite, the first generation may call any enabled user MCP; the prompt only asks for an image and carries no external content. After the first success, the favorite narrows it to the generator.
- Plugin or claude.ai MCPs do not work as generators; the generator must be added with `claude mcp add --scope user`.
- The real test with `imagens-local` took ~2 min on the first generation (model load on the GPU).
- Each portrait costs one short call to Alfred's model, plus GPU time.
