"""What the main agent may use (ADR 0005).

The CLI loads the user's own MCP servers (claude.ai connectors, plugins). ALLOWED runs without
asking; every other tool goes to Claude Code's auto mode classifier, which approves or denies
each call. Two hard limits stay regardless: no Bash, Edit or Write (ADR 0003), and no url
outside http/https (block_local_urls).
"""

from typing import Any
from urllib.parse import urlsplit

from claude_agent_sdk import HookContext, HookJSONOutput

from infra.claude.agents import KINDS

GMAIL = "mcp__claude_ai_Gmail__"
CALENDAR = "mcp__claude_ai_Google_Calendar__"
BROWSER = "mcp__plugin_chrome-devtools-mcp_chrome-devtools"

BUILTIN_TOOLS = ["WebSearch", "WebFetch"]

ALLOWED = [
    *BUILTIN_TOOLS,
    *(
        GMAIL + name
        for name in (
            "search_threads",
            "get_thread",
            "get_message",
            "list_labels",
            "list_drafts",
            "get_draft",
        )
    ),
    *(
        CALENDAR + name
        for name in ("list_calendars", "list_events", "get_event", "search_events", "suggest_time")
    ),
    BROWSER,
    *(
        f"mcp__alfred__{name}"
        for name in (
            *(f"delegar_{kind}" for kind in KINDS),
            "criar_sessao",
            "limpar_sessao",
            "apagar_sessao",
            "listar_sessoes",
            "criar_projeto",
            "listar_projetos",
            "criar_workspace",
            "criar_worktree",
            "apagar_workspace",
        )
    ),
]

HIDDEN = [
    BROWSER + "__upload_file",  # would read local files into a web page
]

WEB_SCHEMES = {"http", "https"}


async def block_local_urls(
    hook_input: Any, tool_use_id: str | None, context: HookContext
) -> HookJSONOutput:
    """PreToolUse: any tool given a url may only reach the web. Without this the browser
    reads local files through file:// (and could leak them by navigating elsewhere)."""
    url = (hook_input.get("tool_input") or {}).get("url")
    if not isinstance(url, str) or urlsplit(url.strip()).scheme.lower() in WEB_SCHEMES:
        return {}
    return {
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "permissionDecisionReason": "Só http/https; arquivos locais estão bloqueados.",
        }
    }
