"""What the main agent may use. Until the confirmation gate exists (phase 5), anything with a
side effect outside the browser stays off: it is hidden from the model and denied anyway.

The CLI also loads the user's own MCP servers (claude.ai connectors, plugins). With
permission_mode "dontAsk" every tool not listed in ALLOWED is denied, so a newly installed
server is safe by default; HIDDEN only keeps known ones out of the model's context so it does
not offer capabilities it cannot use. Never add Bash, Edit or Write here (ADR 0003).
"""

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
    BROWSER,  # whole server; risk accepted in ADR 0004
]

HIDDEN = [
    *(
        GMAIL + name
        for name in (
            "send_message",
            "reply",
            "forward",
            "create_draft",
            "update_draft",
            "delete_draft",
            "trash_message",
            "trash_thread",
            "untrash_message",
            "untrash_thread",
            "mark_message_spam",
            "mark_thread_spam",
            "unmark_message_spam",
            "unmark_thread_spam",
            "label_message",
            "label_thread",
            "unlabel_message",
            "unlabel_thread",
            "update_message_labels",
            "create_label",
            "update_label",
            "delete_label",
        )
    ),
    *(
        CALENDAR + name
        for name in ("create_event", "update_event", "delete_event", "respond_to_event")
    ),
    BROWSER + "__upload_file",  # would read local files into a web page
    "mcp__claude_ai_Google_Drive",
    "mcp__claude_ai_Claude_Docs",
    "mcp__shoogle",
]
