import asyncio
import contextlib
from collections.abc import AsyncIterator
from pathlib import Path

import pytest

from controllers.portraits import Portraits
from controllers.settings import Settings, SettingsUpdate
from errors import AgentError, SessionNotFound
from events import EventBus
from infra.claude.portrait import Painting, Subject
from models import project
from models import session as records
from models import settings as model
from models.db import open_db
from tests.conftest import drain
from tests.test_portrait import PNG
from tests.test_settings import DEFAULTS


class FakePaint:
    def __init__(self, *results: Painting | Exception) -> None:
        self.results = list(results)
        self.calls: list[tuple[Subject, str | None, tuple[str, ...]]] = []

    async def __call__(
        self,
        subject: Subject,
        model: str,
        image_mcp: str | None,
        disabled: tuple[str, ...],
        cwd: Path,
    ) -> Painting:
        self.calls.append((subject, image_mcp, disabled))
        result = self.results.pop(0) if self.results else Painting(PNG, "png", "imagens-local")
        if isinstance(result, Exception):
            raise result
        return result


class Env:
    def __init__(self, bus: EventBus, folder: Path, paint: FakePaint) -> None:
        self.db = open_db(":memory:")
        model.seed(self.db, DEFAULTS)
        self.bus, self.paint = bus, paint
        self.settings = Settings(self.db, bus)
        self.portraits = Portraits(self.db, bus, self.settings, folder, paint)


@pytest.fixture
async def env(bus: EventBus, tmp_path: Path) -> AsyncIterator[Env]:
    e = Env(bus, tmp_path, FakePaint())
    yield e


@contextlib.asynccontextmanager
async def running(env: Env) -> AsyncIterator[None]:
    task = asyncio.create_task(env.portraits.run())
    await asyncio.sleep(0)
    try:
        yield
    finally:
        task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await task


async def settle() -> None:
    """Lets the worker finish; saving runs in a thread."""
    for _ in range(10):
        await asyncio.sleep(0.01)


async def test_boot_paints_sessions_without_portrait_and_tells_the_panel(env: Env) -> None:
    p = project.insert_project(env.db, "Recurve", [], "app de treinos")
    ws = project.insert_workspace(env.db, p.id, "api", "/r", "folder", description="API")
    record = records.insert_session(env.db, "backend", "implementacao", ws.id)
    queue = env.bus.subscribe()

    async with running(env):
        await settle()

    [(subject, image_mcp, _)] = env.paint.calls
    assert subject == Subject("backend", "Implementação", "Recurve", "app de treinos", "api", "API")
    assert image_mcp is None
    assert env.portraits.file("backend") is not None
    assert env.portraits.file("backend").read_bytes() == PNG  # type: ignore[union-attr]
    url = env.portraits.url(record.id, "backend")
    assert url is not None and url.startswith("/api/sessions/backend/portrait?v=")
    assert any(e["type"] == "portrait_updated" and e["session"] == "backend" for e in drain(queue))


async def test_first_success_without_favorite_makes_that_server_the_favorite(env: Env) -> None:
    records.insert_session(env.db, "a", "geral")
    records.insert_session(env.db, "b", "geral")
    env.paint.results = [Painting(PNG, "png", "imagens-local"), Painting(PNG, "png", "outro")]

    async with running(env):
        await settle()

    assert [c[1] for c in env.paint.calls] == [None, "imagens-local"]
    assert env.settings.get().image_mcp == "imagens-local"


async def test_new_sessions_get_painted_and_existing_portraits_are_kept(env: Env) -> None:
    records.insert_session(env.db, "a", "geral")
    async with running(env):
        await settle()
        records.insert_session(env.db, "b", "geral")
        env.bus.publish("session_created", session={"name": "b"})
        env.bus.publish("session_created", session={"name": "a"})  # already has one
        await settle()

    assert [c[0].name for c in env.paint.calls] == ["a", "b"]


async def test_failure_keeps_the_monogram_and_a_request_tries_again(env: Env) -> None:
    records.insert_session(env.db, "a", "geral")
    env.paint.results = [AgentError("serviço fora do ar")]
    env.settings.update(SettingsUpdate(mcp_disabled=["gmail"]))

    async with running(env):
        await settle()
        assert env.portraits.file("a") is None
        env.portraits.request("a")
        await settle()

    assert env.portraits.file("a") is not None
    assert env.paint.calls[0][2] == ("gmail",)


async def test_request_rejects_unknown_sessions(env: Env) -> None:
    with pytest.raises(SessionNotFound):
        env.portraits.request("ninguém")


async def test_deleting_a_session_removes_its_portrait(env: Env, tmp_path: Path) -> None:
    records.insert_session(env.db, "a", "geral")
    async with running(env):
        await settle()
        records.delete_session(env.db, "a")
        env.bus.publish("session_deleted", name="a")
        await settle()

    assert list(tmp_path.iterdir()) == []
