"""One-shot agent that paints a session's portrait with the user's image MCP (ADR 0009).

It only has MCP tools: no Bash, files or web, no hooks, plugins or claude.ai connectors. It loads
the user-scope MCP servers of Claude Code (~/.claude.json): only the favorite one when set, else
every enabled one, and the model picks the image generator.
"""

import asyncio
import base64
import binascii
import json
import re
from collections.abc import AsyncIterator, Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import claude_agent_sdk as sdk

from errors import AgentError
from infra.claude.agents import MAX_BUFFER
from infra.claude.alfred import failure

MAX_BYTES = 20 * 1024 * 1024
CLAUDE_JSON = Path.home() / ".claude.json"
_PATH_LINE = re.compile(r"^\W*imagem\W*:\s*(/\S+)\s*$", re.I | re.M)

Query = Callable[..., AsyncIterator[Any]]


@dataclass(frozen=True)
class Subject:
    """What the portrait is of."""

    name: str
    kind: str
    project: str | None = None
    project_description: str = ""
    workspace: str | None = None
    workspace_description: str = ""


@dataclass(frozen=True)
class Painting:
    data: bytes
    ext: str  # png | jpg | webp
    server: str | None  # MCP server that drew it, when known


def user_mcp_servers(path: Path = CLAUDE_JSON) -> dict[str, Any]:
    """The user-scope MCP servers of Claude Code; none if the file is missing or broken."""
    try:
        servers = json.loads(path.read_text()).get("mcpServers") or {}
    except (OSError, ValueError, AttributeError):
        return {}
    return {str(k): v for k, v in servers.items() if isinstance(v, dict)}


def pick_servers(
    servers: dict[str, Any], image_mcp: str | None, mcp_disabled: tuple[str, ...]
) -> dict[str, Any]:
    if image_mcp:
        if image_mcp not in servers:
            raise AgentError(f"o gerador {image_mcp} não está nos MCPs do Claude Code")
        return {image_mcp: servers[image_mcp]}
    enabled = {k: v for k, v in servers.items() if k not in mcp_disabled}
    if not enabled:
        raise AgentError("nenhum MCP ligado para gerar imagem")
    return enabled


def options(model: str, servers: dict[str, Any], cwd: Path) -> sdk.ClaudeAgentOptions:
    return sdk.ClaudeAgentOptions(
        model=model,
        tools=[],  # MCP tools only
        mcp_servers=servers,
        strict_mcp_config=True,  # no plugin or claude.ai servers
        setting_sources=[],  # no hooks, plugins, CLAUDE.md or permission rules
        allowed_tools=[f"mcp__{name}" for name in servers],
        permission_mode="dontAsk",  # anything else is denied
        cwd=cwd,
        max_buffer_size=MAX_BUFFER,
    )


def prompt(subject: Subject, image_mcp: str | None) -> str:
    place = ""
    if subject.project:
        place = f"\nProjeto: {subject.project}. {subject.project_description}".rstrip()
    if subject.workspace:
        place += f"\nAmbiente: {subject.workspace}. {subject.workspace_description}".rstrip()
    tool = f"do servidor MCP {image_mcp}" if image_mcp else "de geração de imagem dos seus MCPs"
    return f"""Gere o retrato da sessão "{subject.name}" (tipo {subject.kind}) do Alfred, \
um assistente de voz.{place}

Use só uma ferramenta {tool}, uma vez, e nenhuma outra ferramenta.
Imagem quadrada (1024x1024 se der), sem texto. Prompt do gerador em inglês, neste estilo:
"3D clay portrait bust of <a character that fits the session's name and work>, soft matte clay, \
rounded friendly shapes, centered, plain soft gradient background, studio lighting".
Se a ferramenta devolver só o caminho do arquivo, termine com a linha: IMAGEM: <caminho absoluto>"""


def image_ext(data: bytes) -> str | None:
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return "png"
    if data.startswith(b"\xff\xd8\xff"):
        return "jpg"
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "webp"
    return None


async def paint(
    subject: Subject,
    model: str,
    image_mcp: str | None,
    mcp_disabled: tuple[str, ...],
    cwd: Path,
    query: Query = sdk.query,
    claude_json: Path = CLAUDE_JSON,
) -> Painting:
    servers = pick_servers(
        await asyncio.to_thread(user_mcp_servers, claude_json), image_mcp, mcp_disabled
    )
    used: dict[str, str] = {}  # tool_use_id -> MCP server
    found: tuple[bytes, str | None] | None = None
    final: sdk.ResultMessage | None = None
    try:
        async for message in query(
            prompt=prompt(subject, image_mcp), options=options(model, servers, cwd)
        ):
            if isinstance(message, sdk.AssistantMessage):
                for block in message.content:
                    if isinstance(block, sdk.ToolUseBlock) and block.name.startswith("mcp__"):
                        used[block.id] = block.name.split("__")[1]
            elif isinstance(message, sdk.UserMessage) and found is None:
                found = _image_block(message, used)
            elif isinstance(message, sdk.ResultMessage):
                final = message
    except sdk.ClaudeSDKError as e:
        raise AgentError(str(e)) from e
    if final is None or final.is_error:
        raise AgentError(failure(final) if final else "o agente do retrato não respondeu")
    if found is None:
        match = _PATH_LINE.search(final.result or "")
        if match is None:
            raise AgentError("o gerador não devolveu imagem")
        last = list(used.values())[-1] if used else None
        found = (await _read(Path(match.group(1))), last)
    data, server = found
    ext = image_ext(data)
    if ext is None or len(data) > MAX_BYTES:
        raise AgentError("o gerador devolveu algo que não é PNG, JPEG ou WebP até 20 MB")
    return Painting(data, ext, server)


def _image_block(message: sdk.UserMessage, used: dict[str, str]) -> tuple[bytes, str | None] | None:
    if isinstance(message.content, str):
        return None
    for block in message.content:
        if not isinstance(block, sdk.ToolResultBlock) or not isinstance(block.content, list):
            continue
        for item in block.content:
            source = item.get("source") or {}
            if item.get("type") == "image" and source.get("type") == "base64":
                try:
                    data = base64.b64decode(source.get("data", ""), validate=True)
                except (binascii.Error, ValueError):
                    continue
                return data, used.get(block.tool_use_id)
    return None


async def _read(path: Path) -> bytes:
    def read() -> bytes:
        if not path.is_file() or path.stat().st_size > MAX_BYTES:
            raise AgentError(f"imagem inválida em {path}")
        with path.open("rb") as f:
            return f.read(MAX_BYTES + 1)

    try:
        return await asyncio.to_thread(read)
    except OSError as e:
        raise AgentError(f"não consegui ler {path}: {e}") from e
