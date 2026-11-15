"""The server opens a result's file or its folder on this computer (ADR 0014)."""

import os
from pathlib import Path

import pytest

from errors import OpenerError
from infra import opener


@pytest.fixture
def bin_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Fake xdg-open and gdbus that log their arguments."""
    folder = tmp_path / "bin"
    folder.mkdir()
    for name in ("xdg-open", "gdbus"):
        script = folder / name
        script.write_text(f'#!/bin/sh\necho "{name} $*" >> "{tmp_path}/calls"\n')
        script.chmod(0o755)
    monkeypatch.setenv("PATH", f"{folder}{os.pathsep}/usr/bin:/bin")
    return folder


def calls(tmp_path: Path) -> list[str]:
    return (tmp_path / "calls").read_text().splitlines()


async def test_open_runs_xdg_open(bin_dir: Path, tmp_path: Path) -> None:
    await opener.open_path(Path("/home/u/a b.png"), reveal=False)
    assert calls(tmp_path) == ["xdg-open /home/u/a b.png"]


async def test_reveal_asks_the_file_manager_over_dbus(bin_dir: Path, tmp_path: Path) -> None:
    await opener.open_path(Path("/home/u/a b.png"), reveal=True)
    [call] = calls(tmp_path)
    assert call.startswith("gdbus call --session --dest org.freedesktop.FileManager1")
    assert "['file:///home/u/a%20b.png']" in call


async def test_reveal_falls_back_to_the_folder(bin_dir: Path, tmp_path: Path) -> None:
    (bin_dir / "gdbus").write_text("#!/bin/sh\nexit 1\n")
    await opener.open_path(Path("/home/u/a.png"), reveal=True)
    assert calls(tmp_path) == ["xdg-open /home/u"]


async def test_a_failure_raises(bin_dir: Path) -> None:
    (bin_dir / "xdg-open").write_text("#!/bin/sh\necho no app >&2\nexit 3\n")
    with pytest.raises(OpenerError, match="no app"):
        await opener.open_path(Path("/home/u/a.png"), reveal=False)


async def test_missing_tool_raises(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("PATH", str(tmp_path))
    with pytest.raises(OpenerError):
        await opener.open_path(Path("/home/u/a.png"), reveal=False)
