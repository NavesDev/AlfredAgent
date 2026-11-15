"""The MCP servers a Claude Code session would load: user, project, plugin and claude.ai ones.

Asks the CLI itself, without sending a prompt, so the panel can list them before any session
connects.
"""

import re
from pathlib import Path

import claude_agent_sdk as sdk


def tool_prefix(server: str) -> str:
    """The prefix the CLI gives a server's tools: "plugin:expo:expo" -> "mcp__plugin_expo_expo"."""
    return "mcp__" + re.sub(r"[^A-Za-z0-9_-]", "_", server)


async def mcp_server_names(cwd: Path) -> list[str]:
    client = sdk.ClaudeSDKClient(
        sdk.ClaudeAgentOptions(cwd=cwd, setting_sources=["user", "project", "local"])
    )
    await client.connect()
    try:
        status = await client.get_mcp_status()
        return [str(s["name"]) for s in status.get("mcpServers", [])]
    finally:
        await client.disconnect()
