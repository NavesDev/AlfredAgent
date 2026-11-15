"""What the main agent may use (ADR 0005, 0011).

The CLI loads the user's own MCP servers (claude.ai connectors, plugins). ALLOWED runs without
asking; every other tool goes to Claude Code's auto mode classifier, which approves or denies
each call. Hard limits stay regardless: no Bash, Edit or Write (ADR 0003), no url outside
http/https (block_local_urls), no file outside the home (guard_local_paths) and no secret
(SECRET_RULES).
"""

import os
from collections.abc import Awaitable, Callable
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

from claude_agent_sdk import HookContext, HookJSONOutput

from infra.claude.agents import KINDS

GMAIL = "mcp__claude_ai_Gmail__"
CALENDAR = "mcp__claude_ai_Google_Calendar__"
BROWSER = "mcp__plugin_chrome-devtools-mcp_chrome-devtools"

READ_TOOLS = ["Read", "Glob", "Grep"]
BUILTIN_TOOLS = ["WebSearch", "WebFetch", *READ_TOOLS]

# Claude Code applies Read rules to Grep and Glob too.
SECRET_RULES = [
    f"Read({glob})"
    for glob in (
        "**/.env*",
        "~/.ssh/**",
        "~/.gnupg/**",
        "~/.aws/**",
        "~/.config/gh/**",
        "~/.claude/.credentials.json",
        "~/.claude.json",
        "**/*.pem",
        "**/*.key",
        "**/id_*",
        "~/.netrc",
    )
]

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
            "criar_ambiente",
            "criar_worktree",
            "apagar_ambiente",
            "definir_apelidos",
            "definir_descricao",
            "ver_ambiente",
            "iniciar_feature",
            "definir_ambiente_padrao",
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


Hook = Callable[[Any, str | None, HookContext], Awaitable[HookJSONOutput]]


def path_guard(home: Path) -> Hook:
    """PreToolUse for Read, Glob and Grep: the real path must stay inside the home.

    A path is resolved against the home and through symlinks; no path means the home itself.
    Glob patterns and Grep's file filter may not climb with '..' nor point outside."""
    root = home.resolve()

    def inside(raw: str) -> bool:
        path = Path(os.path.expanduser(raw))
        return (root / path).resolve().is_relative_to(root)

    def allowed(tool: str, args: dict[str, Any]) -> bool:
        if tool == "Read":
            return isinstance(raw := args.get("file_path"), str) and inside(raw)
        base = args.get("path")
        if base is not None and not (isinstance(base, str) and inside(base)):
            return False
        for key in ("pattern", "glob") if tool == "Glob" else ("glob",):
            pattern = args.get(key)
            if not isinstance(pattern, str):
                continue
            if ".." in Path(pattern).parts:
                return False
            if pattern.startswith(("/", "~")):
                static = pattern.split("*", 1)[0].rsplit("/", 1)[0] or "/"
                if not inside(static):
                    return False
        return True

    async def hook(
        hook_input: Any, tool_use_id: str | None, context: HookContext
    ) -> HookJSONOutput:
        tool = hook_input.get("tool_name")
        if tool not in READ_TOOLS or allowed(tool, hook_input.get("tool_input") or {}):
            return {}
        return {
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "permissionDecision": "deny",
                "permissionDecisionReason": "Fora da home; só leio arquivos dentro dela.",
            }
        }

    return hook


guard_local_paths = path_guard(Path.home())
