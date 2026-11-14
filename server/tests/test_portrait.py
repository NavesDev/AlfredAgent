import base64
import json
from collections.abc import AsyncIterator
from pathlib import Path
from typing import Any

import pytest
from claude_agent_sdk import (
    AssistantMessage,
    ClaudeAgentOptions,
    ToolResultBlock,
    ToolUseBlock,
    UserMessage,
)

from errors import AgentError
from infra.claude.portrait import (
    Subject,
    image_ext,
    options,
    paint,
    pick_servers,
    prompt,
    user_mcp_servers,
)
from tests.test_alfred import result

PNG = b"\x89PNG\r\n\x1a\n" + b"0" * 32
SUBJECT = Subject(
    name="backend",
    kind="Implementação",
    project="Recurve",
    project_description="app de treinos",
    workspace="api",
    workspace_description="API em FastAPI",
)


def use(server: str, id: str = "t1") -> AssistantMessage:
    block = ToolUseBlock(id=id, name=f"mcp__{server}__gerar", input={"prompt": "clay"})
    return AssistantMessage(content=[block], model="m")


def image(data: bytes, id: str = "t1") -> UserMessage:
    source = {"type": "base64", "media_type": "image/png", "data": base64.b64encode(data).decode()}
    content: list[dict[str, Any]] = [
        {"type": "text", "text": "ok"},
        {"type": "image", "source": source},
    ]
    return UserMessage(content=[ToolResultBlock(tool_use_id=id, content=content)])


class FakeQuery:
    def __init__(self, *messages: Any) -> None:
        self.messages = messages
        self.calls: list[tuple[str, ClaudeAgentOptions]] = []

    async def __call__(self, *, prompt: str, options: ClaudeAgentOptions) -> AsyncIterator[Any]:
        self.calls.append((prompt, options))
        for message in self.messages:
            yield message


HTTP = {"type": "http", "url": "http://127.0.0.1:8765/mcp"}
SERVERS = {"imagens-local": HTTP, "shoogle": HTTP, "gmail": HTTP}


@pytest.fixture
def claude_json(tmp_path: Path) -> Path:
    path = tmp_path / ".claude.json"
    path.write_text(json.dumps({"mcpServers": SERVERS, "projects": {}}))
    return path


def test_user_mcp_servers_reads_claude_json(claude_json: Path, tmp_path: Path) -> None:
    assert user_mcp_servers(claude_json) == SERVERS
    assert user_mcp_servers(tmp_path / "missing.json") == {}


def test_pick_servers_without_favorite_takes_every_enabled_one() -> None:
    assert set(pick_servers(SERVERS, None, ("gmail",))) == {"imagens-local", "shoogle"}
    with pytest.raises(AgentError):
        pick_servers(SERVERS, None, tuple(SERVERS))


def test_pick_servers_with_favorite_takes_only_it() -> None:
    assert pick_servers(SERVERS, "imagens-local", ("imagens-local",)) == {"imagens-local": HTTP}
    with pytest.raises(AgentError):
        pick_servers(SERVERS, "plugin:x", ())


def test_options_load_only_the_picked_servers_and_their_tools() -> None:
    opts = options("haiku", {"imagens-local": HTTP}, Path("/tmp"))

    assert opts.tools == []  # no Bash, Read, Write or web
    assert opts.mcp_servers == {"imagens-local": HTTP}
    assert (opts.strict_mcp_config, opts.setting_sources) == (True, [])
    assert opts.allowed_tools == ["mcp__imagens-local"]
    assert opts.permission_mode == "dontAsk"  # everything else is denied


def test_prompt_names_the_session_and_its_place() -> None:
    text = prompt(SUBJECT, "imagens-local")

    for part in ("backend", "Implementação", "Recurve", "app de treinos", "API em FastAPI"):
        assert part in text
    assert "imagens-local" in text and "clay" in text


def test_image_ext_checks_the_bytes() -> None:
    assert image_ext(PNG) == "png"
    assert image_ext(b"\xff\xd8\xff\xe0rest") == "jpg"
    assert image_ext(b"RIFF\0\0\0\0WEBPVP8 ") == "webp"
    assert image_ext(b"-----BEGIN OPENSSH PRIVATE KEY") is None


async def test_paint_takes_the_image_block_and_its_server(claude_json: Path) -> None:
    query = FakeQuery(use("imagens-local"), image(PNG), result("pronto"))

    painting = await paint(
        SUBJECT, "haiku", None, (), Path("/tmp"), query=query, claude_json=claude_json
    )

    assert (painting.data, painting.ext, painting.server) == (PNG, "png", "imagens-local")


async def test_paint_falls_back_to_the_path_line(tmp_path: Path, claude_json: Path) -> None:
    file = tmp_path / "out.png"
    file.write_bytes(PNG)
    query = FakeQuery(use("outro"), result(f"Feito.\nIMAGEM: {file}"))

    painting = await paint(
        SUBJECT, "haiku", None, (), tmp_path, query=query, claude_json=claude_json
    )

    assert (painting.data, painting.server) == (PNG, "outro")


@pytest.mark.parametrize("text", ["sem imagem", "IMAGEM: /etc/passwd", "IMAGEM: /nao/existe.png"])
async def test_paint_fails_without_a_valid_image(text: str, claude_json: Path) -> None:
    with pytest.raises(AgentError):
        await paint(SUBJECT, "haiku", None, (), Path("/tmp"), FakeQuery(result(text)), claude_json)


async def test_paint_fails_when_the_agent_fails(claude_json: Path) -> None:
    query = FakeQuery(result("erro", is_error=True))

    with pytest.raises(AgentError):
        await paint(SUBJECT, "haiku", None, (), Path("/tmp"), query=query, claude_json=claude_json)
