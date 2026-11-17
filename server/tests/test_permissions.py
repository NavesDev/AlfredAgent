"""ADR 0011: the main agent reads the home, never outside it, never secrets."""

from pathlib import Path
from typing import Any

import pytest

from infra.claude import permissions
from infra.claude.alfred import AlfredAgent


async def decide(home: Path, tool: str, **tool_input: Any) -> bool:
    """True when the guard lets the call through."""
    guard = permissions.path_guard(home)
    out = await guard({"tool_name": tool, "tool_input": tool_input}, None, {"signal": None})
    return "'deny'" not in repr(out)


@pytest.fixture
def home(tmp_path: Path) -> Path:
    home = tmp_path / "home"
    (home / "Projetos" / "Vrummy").mkdir(parents=True)
    (home / "Projetos" / "Vrummy" / "README.md").write_text("vrummy")
    (tmp_path / "outside.txt").write_text("secret")
    return home


async def test_reads_inside_the_home(home: Path) -> None:
    assert await decide(home, "Read", file_path=str(home / "Projetos/Vrummy/README.md"))
    assert await decide(home, "Read", file_path="Projetos/Vrummy/README.md")  # relative to home
    assert await decide(home, "Glob", pattern="**/*.md", path=str(home / "Projetos"))
    assert await decide(home, "Grep", pattern="supabase", path=str(home / "Projetos/Vrummy"))


async def test_denies_outside_the_home(home: Path) -> None:
    assert not await decide(home, "Read", file_path="/etc/passwd")
    assert not await decide(home, "Read", file_path=str(home.parent / "outside.txt"))
    assert not await decide(home, "Glob", pattern="*", path="/etc")
    assert not await decide(home, "Grep", pattern="root", path="/etc")


async def test_denies_a_symlink_that_leaves_the_home(home: Path) -> None:
    (home / "link").symlink_to(home.parent)
    assert not await decide(home, "Read", file_path=str(home / "link" / "outside.txt"))
    assert not await decide(home, "Grep", pattern="x", path=str(home / "link"))


async def test_denies_dot_dot_and_absolute_globs(home: Path) -> None:
    assert not await decide(home, "Read", file_path=str(home / "Projetos/../../outside.txt"))
    assert not await decide(home, "Glob", pattern="../*.txt")
    assert not await decide(home, "Glob", pattern="/etc/*")
    assert not await decide(home, "Grep", pattern="x", glob="../**")
    assert await decide(home, "Glob", pattern=str(home / "Projetos" / "**" / "*.md"))


async def test_a_call_without_path_checks_the_home_itself(home: Path) -> None:
    assert await decide(home, "Grep", pattern="supabase")
    assert await decide(home, "Glob", pattern="**/README.md")


async def test_other_tools_pass_untouched(home: Path) -> None:
    assert await decide(home, "WebSearch", query="x")


def test_alfred_reads_from_the_home_with_secrets_denied() -> None:
    options = AlfredAgent(None, None, "sonnet", 1)._options(None)  # type: ignore[arg-type]

    assert options.tools == ["WebSearch", "WebFetch", "Read", "Glob", "Grep"]
    assert {"Read", "Glob", "Grep"} <= set(options.allowed_tools)
    assert not {"Bash", "Edit", "Write"} & set(options.tools or [])
    assert options.cwd == Path.home()
    for rule in ("Read(**/.env*)", "Read(~/.ssh/**)", "Read(~/.claude/.credentials.json)"):
        assert rule in options.disallowed_tools
    [matcher] = options.hooks["PreToolUse"]  # type: ignore[index]
    assert matcher.hooks == [permissions.block_local_urls, permissions.guard_local_paths]


def test_readable_files_stay_in_the_home_and_skip_secrets(home: Path) -> None:
    ok = home / "Projetos/Vrummy/README.md"
    assert permissions.readable(ok, home)
    assert permissions.readable(home / "Imagens/retrato.png", home)  # existence is not its job
    for path in (
        Path("/etc/passwd"),
        home.parent / "outside.txt",
        home / "Projetos/../../outside.txt",
        home / ".ssh/id_rsa",
        home / ".ssh/config",
        home / "Projetos/Vrummy/.env.local",
        home / "certs/server.pem",
        home / ".claude/.credentials.json",
        home / ".claude.json",
        home / ".config/gh/hosts.yml",
        Path("Projetos/Vrummy/README.md"),  # relative: never guessed
    ):
        assert not permissions.readable(path, home), path


def test_readable_follows_symlinks(home: Path) -> None:
    (home / ".ssh").mkdir()
    (home / ".ssh/id_ed25519").write_text("key")
    (home / "foto.png").symlink_to(home / ".ssh/id_ed25519")
    (home / "fora").symlink_to(home.parent)
    assert not permissions.readable(home / "foto.png", home)
    assert not permissions.readable(home / "fora/outside.txt", home)
