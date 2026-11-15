"""Release check and self-update (ADR 0013): compares local and remote tags, keeps the snapshot
the panel shows and starts the update script, which outlives the server."""

import asyncio
import json
import logging
import time
from collections.abc import Callable
from pathlib import Path
from typing import Protocol

from errors import GitError, UpdateError
from events import EventBus
from models.update import UpdateResult, UpdateView, newest, notes_for, parse_version

log = logging.getLogger(__name__)

CHECK_EVERY_S = 6 * 3600


class Git(Protocol):
    async def local_tags(self, path: Path) -> list[str]: ...
    async def remote_tags(self, path: Path) -> list[str]: ...
    async def fetch_tag(self, path: Path, tag: str) -> None: ...
    async def show(self, path: Path, rev: str, file: str) -> str: ...
    async def current_branch(self, path: Path) -> str: ...
    async def is_dirty(self, path: Path) -> bool: ...


def _newer(latest: str | None, current: str | None) -> bool:
    if latest is None:
        return False
    return current is None or (parse_version(latest) or ()) > (parse_version(current) or ())


class Updates:
    def __init__(
        self,
        bus: EventBus,
        root: Path,
        *,
        git: Git,
        spawn: Callable[[str], None],
        result_path: Path,
        clock: Callable[[], float] = time.time,
    ) -> None:
        self._bus, self._root, self._git, self._spawn = bus, root, git, spawn
        self._result_path, self._clock = result_path, clock
        self._view = UpdateView(
            current=None,
            latest=None,
            available=False,
            notes="",
            status="idle",
            error=None,
            checked_at=None,
            last=None,
        )

    def view(self) -> UpdateView:
        return self._view

    def _set(self, **changes: object) -> UpdateView:
        self._view = self._view.model_copy(update=changes)
        self._bus.publish("update_status", update=self._view.model_dump())
        return self._view

    def _read_result(self) -> UpdateResult | None:
        try:
            data = json.loads(self._result_path.read_text())
            return UpdateResult(previous=data.get("from"), **data)
        except FileNotFoundError:
            return None
        except (ValueError, TypeError) as e:
            log.warning("ignoring %s: %s", self._result_path, e)
            return None

    async def check(self) -> UpdateView:
        if self._view.status == "updating":
            return self._view
        self._set(status="checking", last=self._read_result())
        try:
            current = newest(await self._git.local_tags(self._root))
            latest = newest(await self._git.remote_tags(self._root))
            available = _newer(latest, current)
            notes = ""
            if available and latest:
                await self._git.fetch_tag(self._root, latest)
                changelog = await self._git.show(self._root, latest, "CHANGELOG.md")
                notes = notes_for(changelog, latest)
        except GitError as e:
            return self._set(
                status="error", error=str(e), available=False, checked_at=self._clock()
            )
        return self._set(
            status="idle",
            error=None,
            current=current,
            latest=latest,
            available=available,
            notes=notes,
            checked_at=self._clock(),
        )

    async def apply(self) -> UpdateView:
        view = self._view
        if view.status == "updating":
            raise UpdateError("A atualização já está em andamento.")
        if not view.available or view.latest is None:
            raise UpdateError("Nenhuma versão nova para instalar.")
        try:
            branch = await self._git.current_branch(self._root)
            dirty = await self._git.is_dirty(self._root)
        except GitError as e:
            raise UpdateError(f"Não consegui ler o git: {e}") from e
        if branch != "main":
            where = branch or "HEAD solto"
            raise UpdateError(f"Só atualizo na branch main; o Alfred está em {where}.")
        if dirty:
            raise UpdateError("O repositório tem mudanças não commitadas; commite ou descarte.")
        self._spawn(view.latest)
        return self._set(status="updating", error=None)

    async def run(self, every_s: float = CHECK_EVERY_S) -> None:
        while True:
            await self.check()
            await asyncio.sleep(every_s)
