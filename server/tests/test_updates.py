import asyncio
from pathlib import Path

import pytest

from controllers.updates import Updates
from errors import GitError, UpdateError
from events import EventBus
from tests.conftest import drain

CHANGELOG = "# Changelog\n\n## [0.2.0](x) (2026-12-01)\n\n### Features\n\n* pill\n"


class FakeGit:
    def __init__(self) -> None:
        self.local = ["v0.1.0"]
        self.remote = ["v0.1.0", "v0.2.0"]
        self.branch = "main"
        self.dirty = False
        self.fail: str | None = None
        self.fetched: list[str] = []

    async def local_tags(self, path: Path) -> list[str]:
        return self.local

    async def remote_tags(self, path: Path) -> list[str]:
        if self.fail:
            raise GitError(self.fail)
        return self.remote

    async def fetch_tag(self, path: Path, tag: str) -> None:
        self.fetched.append(tag)

    async def show(self, path: Path, rev: str, file: str) -> str:
        return CHANGELOG

    async def current_branch(self, path: Path) -> str:
        return self.branch

    async def is_dirty(self, path: Path) -> bool:
        return self.dirty


class Env:
    def __init__(self, bus: EventBus, tmp_path: Path) -> None:
        self.git = FakeGit()
        self.spawned: list[str] = []
        self.result = tmp_path / "update.json"
        self.updates = Updates(
            bus,
            tmp_path,
            git=self.git,
            spawn=self.spawned.append,
            result_path=self.result,
            clock=lambda: 1000.0,
        )


@pytest.fixture
def env(bus: EventBus, tmp_path: Path) -> Env:
    return Env(bus, tmp_path)


async def test_check_finds_a_newer_tag_with_its_notes(env: Env, bus: EventBus) -> None:
    queue = bus.subscribe()

    view = await env.updates.check()

    assert (view.current, view.latest, view.available) == ("v0.1.0", "v0.2.0", True)
    assert view.notes == "### Features\n\n* pill"
    assert (view.status, view.checked_at) == ("idle", 1000.0)
    assert env.git.fetched == ["v0.2.0"]
    await asyncio.sleep(0)
    events = [e for e in drain(queue) if e["type"] == "update_status"]
    assert events[-1]["update"]["available"] is True


async def test_check_up_to_date_has_no_notes(env: Env) -> None:
    env.git.local = ["v0.1.0", "v0.2.0"]

    view = await env.updates.check()

    assert (view.available, view.notes, env.git.fetched) == (False, "", [])


async def test_check_failure_keeps_the_error_and_no_update(env: Env) -> None:
    env.git.fail = "Could not read from remote repository."

    view = await env.updates.check()

    assert (view.status, view.available) == ("error", False)
    assert view.error == "Could not read from remote repository."


async def test_apply_starts_the_script_with_the_tag(env: Env) -> None:
    await env.updates.check()

    view = await env.updates.apply()

    assert env.spawned == ["v0.2.0"]
    assert view.status == "updating"


@pytest.mark.parametrize(
    ("change", "message"),
    [
        ({"dirty": True}, "mudanças não commitadas"),
        ({"branch": "feat/x"}, "branch main"),
        ({"remote": ["v0.1.0"]}, "Nenhuma versão nova"),
    ],
)
async def test_apply_refuses(env: Env, change: dict[str, object], message: str) -> None:
    for key, value in change.items():
        setattr(env.git, key, value)
    await env.updates.check()

    with pytest.raises(UpdateError, match=message):
        await env.updates.apply()

    assert env.spawned == []


async def test_apply_twice_refuses_while_updating(env: Env) -> None:
    await env.updates.check()
    await env.updates.apply()

    with pytest.raises(UpdateError, match="já está"):
        await env.updates.apply()


async def test_last_result_is_read_from_the_script_file(env: Env) -> None:
    env.result.write_text(
        '{"from": "v0.1.0", "to": "v0.2.0", "ok": false, "error": "uv sync falhou", "at": 5}'
    )

    view = await env.updates.check()

    assert view.last is not None
    assert (view.last.to, view.last.ok, view.last.error) == ("v0.2.0", False, "uv sync falhou")


async def test_broken_result_file_is_ignored(env: Env) -> None:
    env.result.write_text("{not json")

    assert (await env.updates.check()).last is None
