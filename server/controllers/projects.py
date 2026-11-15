"""Projects and their workspaces: any folder, or a git worktree made from a workspace."""

from __future__ import annotations

import asyncio
import logging
import re
import sqlite3
import unicodedata
from collections.abc import AsyncIterator, Awaitable, Callable, Iterable
from pathlib import Path
from typing import Protocol

from errors import (
    GitError,
    NoDefaultWorkspace,
    ProjectError,
    ProjectInUse,
    ProjectNotFound,
    SessionError,
)
from events import EventBus
from infra import git as real_git
from infra.git import GitSummary
from models import project
from models import session as records
from models.project import ImplementationMode, Project, Workspace

log = logging.getLogger(__name__)

KEEP = object()  # update_workspace: leave the implementation mode as it is


class Git(Protocol):
    async def add_worktree(
        self, parent: Path, name: str, branch: str | None = None
    ) -> tuple[Path, str]: ...
    async def remove_worktree(self, path: Path, force: bool) -> None: ...
    async def is_dirty(self, path: Path) -> bool: ...
    async def summary(self, path: Path) -> GitSummary: ...
    async def common_dir(self, path: Path) -> Path: ...
    async def list_worktrees(self, repo: Path) -> list[tuple[Path, str | None]]: ...


class Projects:
    def __init__(
        self,
        db: sqlite3.Connection,
        bus: EventBus,
        git: Git = real_git,
        mode: Callable[[], ImplementationMode] = lambda: "worktree",
        drop_session: Callable[[str], Awaitable[None]] | None = None,
        watch: Callable[[Iterable[Path], asyncio.Event], AsyncIterator[Path]] | None = None,
    ) -> None:
        self._db, self._bus, self._git, self._mode = db, bus, git, mode
        self._drop_session, self._watch = drop_session, watch
        self._rewatch = asyncio.Event()

    def all(self) -> list[Project]:
        return project.list_projects(self._db)

    def get(self, id: int) -> Project:
        found = project.get_project(self._db, id)
        if found is None:
            raise ProjectNotFound("Esse projeto não existe.")
        return found

    def find(self, name: str) -> Project:
        found = project.find_project(self._db, name)
        if found is None:
            raise ProjectNotFound(f"Não existe projeto chamado {name}.")
        return found

    def create(self, name: str, aliases: list[str], description: str = "") -> Project:
        name = self._free_name(name)
        created = project.insert_project(self._db, name, _clean(aliases), _description(description))
        self._bus.publish("project_created", project=created.model_dump())
        return created

    def update(
        self,
        id: int,
        name: str | None = None,
        aliases: list[str] | None = None,
        description: str | None = None,
        default_workspace_id: int | None = None,
    ) -> Project:
        current = self.get(id)
        if name is not None and name.strip().lower() != current.name.lower():
            name = self._free_name(name)
        if default_workspace_id is not None and all(
            w.id != default_workspace_id for w in current.workspaces
        ):
            raise ProjectNotFound(f"Esse ambiente não é do projeto {current.name}.")
        project.update_project(
            self._db,
            id,
            name.strip() if name else None,
            _clean(aliases) if aliases is not None else None,
            _description(description) if description is not None else None,
            default_workspace_id,
        )
        return self._publish_updated(id)

    def delete(self, id: int) -> None:
        current = self.get(id)
        if current.workspaces:
            raise ProjectInUse(f"O projeto {current.name} ainda tem ambientes. Apague-os antes.")
        project.delete_project(self._db, id)
        self._bus.publish("project_deleted", id=id)

    def add_workspace(
        self, project_id: int, name: str, path: str, description: str = ""
    ) -> Workspace:
        current = self.get(project_id)
        name = self._free_workspace_name(current, name)
        description = _description(description)
        folder = Path(path).expanduser()
        if not folder.is_dir():
            raise ProjectError(f"A pasta {path} não existe.")
        ws = project.insert_workspace(
            self._db, project_id, name, str(folder), "folder", description=description
        )
        if current.default_workspace_id is None:
            project.update_project(self._db, project_id, default_workspace_id=ws.id)
        self._publish_updated(project_id)
        self._rewatch.set()  # maybe a new repo to watch
        return ws

    async def add_worktree(
        self,
        project_id: int,
        parent_id: int,
        name: str,
        description: str = "",
        branch: str | None = None,
    ) -> Workspace:
        current = self.get(project_id)
        name = self._free_workspace_name(current, name)
        description = _description(description)
        parent = next((w for w in current.workspaces if w.id == parent_id), None)
        if parent is None:
            raise ProjectNotFound(f"O ambiente de origem não existe no projeto {current.name}.")
        path, branch = await self._git.add_worktree(Path(parent.path), name, branch)
        synced = next(  # the watcher may have registered it first
            (w for w in self.get(project_id).workspaces if _real(w.path) == _real(str(path))),
            None,
        )
        if synced is not None:
            return synced
        ws = project.insert_workspace(
            self._db, project_id, name, str(path), "worktree", parent.id, branch, description
        )
        self._publish_updated(project_id)
        return ws

    def workspace(self, project_name: str, name: str) -> Workspace:
        found = self.find(project_name)
        ws = next((w for w in found.workspaces if w.name.lower() == name.strip().lower()), None)
        if ws is None:
            raise ProjectNotFound(f"O projeto {found.name} não tem o ambiente {name}.")
        return ws

    async def summary(self, project_name: str, name: str) -> tuple[Workspace, GitSummary]:
        ws = self.workspace(project_name, name)
        return ws, await self._git.summary(Path(ws.path))

    def update_workspace(
        self,
        id: int,
        description: str | None = None,
        implementation_mode: ImplementationMode | object | None = KEEP,
    ) -> Workspace:
        ws = project.get_workspace(self._db, id)
        if ws is None:
            raise ProjectNotFound("Esse ambiente não existe.")
        if description is not None:
            project.update_workspace(self._db, id, _description(description))
        if implementation_mode is not KEEP:
            if implementation_mode not in (None, "worktree", "ambiente"):
                raise ProjectError("Modo de implementação inválido: use worktree ou ambiente.")
            project.set_implementation_mode(self._db, id, implementation_mode)
        self._publish_updated(ws.project_id)
        updated = project.get_workspace(self._db, id)
        assert updated is not None
        return updated

    def mode_of(self, ws: Workspace) -> ImplementationMode:
        """The workspace's own mode, else the global one; a worktree always works in itself."""
        if ws.kind == "worktree":
            return "ambiente"
        return ws.implementation_mode or self._mode()

    async def start_feature(
        self,
        project_name: str,
        feature: str,
        workspace: str | None = None,
        branch: str | None = None,
        worktree: bool | None = None,
    ) -> Workspace:
        """Where a new feature gets implemented: the workspace named (else the project's
        default) or a worktree of it. `worktree` is Alfred's call; without it the workspace's
        mode decides. A worktree workspace always works in itself."""
        found = self.find(project_name)
        base = (
            self.workspace(found.name, workspace)
            if workspace
            else next((w for w in found.workspaces if w.id == found.default_workspace_id), None)
        )
        if base is None:
            raise NoDefaultWorkspace(
                f"O projeto {found.name} não tem ambiente padrão; diga em qual ambiente."
            )
        if branch is not None and not _BRANCH.fullmatch(branch):
            raise ProjectError(f"Nome de branch inválido: {branch!r}.")
        wants = worktree if worktree is not None else self.mode_of(base) == "worktree"
        if base.kind == "worktree" or not wants:
            return base
        slug = _slug(feature)
        existing = next((w for w in found.workspaces if w.name.lower() == slug), None)
        if existing is not None:
            return existing
        return await self.add_worktree(found.id, base.id, slug, branch=branch or f"feat/{slug}")

    async def delete_workspace(self, id: int, force: bool = False) -> None:
        ws = project.get_workspace(self._db, id)
        if ws is None:
            raise ProjectNotFound("Esse ambiente não existe.")
        if names := records.sessions_in_workspace(self._db, id):
            raise ProjectInUse(f"O ambiente {ws.name} tem sessões: {', '.join(names)}.")
        children = [
            w.name for w in project.workspaces_of(self._db, ws.project_id) if w.parent_id == id
        ]
        if children:
            raise ProjectInUse(f"O ambiente {ws.name} tem worktrees: {', '.join(children)}.")
        if ws.kind == "worktree":
            path = Path(ws.path)
            if not force and await self._git.is_dirty(path):
                raise ProjectInUse(f"O worktree {ws.name} tem mudanças não commitadas.")
            await self._git.remove_worktree(path, force)
        project.delete_workspace(self._db, id)
        self._publish_updated(ws.project_id)

    async def _groups(self) -> dict[Path, list[Workspace]]:
        """Folder workspaces by the repo they belong to; folders git can't read are left out."""
        groups: dict[Path, list[Workspace]] = {}
        for p in self.all():
            for ws in p.workspaces:
                if ws.kind != "folder":
                    continue
                try:
                    common = await self._git.common_dir(Path(ws.path))
                except GitError as e:
                    log.debug("not a repo, not synced: %s (%s)", ws.path, e)
                    continue
                groups.setdefault(common, []).append(ws)
        return groups

    async def repos(self) -> list[Path]:
        return sorted(await self._groups())

    async def sync_worktrees(
        self, common: Path | None = None
    ) -> tuple[list[Workspace], list[Workspace]]:
        """Makes the workspaces mirror the worktrees git has (ADR 0011): a worktree made outside
        becomes a workspace of the repo's first folder; a vanished one takes its workspace and
        sessions with it. Only `common`'s repo when given."""
        added: list[Workspace] = []
        removed: list[Workspace] = []
        for repo, folders in (await self._groups()).items():
            if common is not None and repo != common:
                continue
            parent = folders[0]
            try:
                listed = await self._git.list_worktrees(Path(parent.path))
            except GitError as e:
                log.warning("could not list worktrees of %s: %s", parent.path, e)
                continue
            current = self.get(parent.project_id)
            known = {_real(w.path) for p in self.all() for w in p.workspaces}
            for path, branch in listed:
                if _real(str(path)) in known:
                    continue
                name = self._spare_name(current, path.name)
                ws = project.insert_workspace(
                    self._db, current.id, name, str(path), "worktree", parent.id, branch
                )
                current = self.get(current.id)
                added.append(ws)
            alive = {_real(str(path)) for path, _ in listed}
            roots = {w.id for w in folders}
            for ws in sorted(_worktrees_under(current, roots), key=lambda w: -w.id):
                if _real(ws.path) not in alive and await self._drop(ws):
                    removed.append(ws)
            if added or removed:
                self._publish_updated(current.id)
        return added, removed

    async def _drop(self, ws: Workspace) -> bool:
        for name in records.sessions_in_workspace(self._db, ws.id):
            try:
                if self._drop_session is None:
                    raise SessionError("no way to drop sessions")
                await self._drop_session(name)
            except SessionError as e:
                log.warning("kept workspace %s: session %s stays (%s)", ws.name, name, e)
                return False
        project.delete_workspace(self._db, ws.id)
        return True

    async def watch_worktrees(self) -> None:
        """Syncs everything once, then each repo whenever git adds or removes a worktree."""
        if self._watch is None:
            return
        await self.sync_worktrees()
        while True:
            repos = await self.repos()
            watched = _watched(repos)
            self._rewatch.clear()
            stop = asyncio.Event()
            relay = asyncio.create_task(_relay(self._rewatch, stop))
            try:
                async for repo in self._watch(repos, stop):
                    await self.sync_worktrees(repo)
                    if _watched(repos) != watched:  # a repo got its first worktrees/ folder
                        stop.set()
            finally:
                relay.cancel()

    def _free_name(self, name: str) -> str:
        name = name.strip()
        if not name:
            raise ProjectError("O projeto precisa de um nome.")
        if project.find_project(self._db, name) is not None:
            raise ProjectError(f"Já existe um projeto chamado {name}.")
        return name

    def _free_workspace_name(self, current: Project, name: str) -> str:
        name = name.strip()
        if not name:
            raise ProjectError("O ambiente precisa de um nome.")
        if any(w.name.lower() == name.lower() for w in current.workspaces):
            raise ProjectError(f"O projeto {current.name} já tem um ambiente chamado {name}.")
        return name

    def _spare_name(self, current: Project, name: str) -> str:
        taken = {w.name.lower() for w in current.workspaces}
        candidate, n = name, 2
        while candidate.lower() in taken:
            candidate, n = f"{name}-{n}", n + 1
        return candidate

    def _publish_updated(self, id: int) -> Project:
        updated = self.get(id)
        self._bus.publish("project_updated", project=updated.model_dump())
        return updated


MAX_DESCRIPTION = 200


def _description(text: str) -> str:
    text = " ".join(text.split())
    if len(text) > MAX_DESCRIPTION:
        raise ProjectError(f"A descrição passa de {MAX_DESCRIPTION} caracteres; encurte.")
    return text


_BRANCH = re.compile(r"(?!-)(?!.*\.\.)[A-Za-z0-9._/-]{1,100}")


def _real(path: str) -> str:
    return str(Path(path).expanduser().resolve())


def _worktrees_under(current: Project, roots: set[int]) -> list[Workspace]:
    """Worktree workspaces whose chain of parents reaches one of the given folders."""
    by_id = {w.id: w for w in current.workspaces}

    def root(ws: Workspace) -> int | None:
        while ws.parent_id is not None and ws.parent_id in by_id:
            ws = by_id[ws.parent_id]
        return ws.id

    return [w for w in current.workspaces if w.kind == "worktree" and root(w) in roots]


def _watched(repos: list[Path]) -> set[Path]:
    return {p for r in repos for p in (r, r / "worktrees") if p.is_dir()}


async def _relay(source: asyncio.Event, target: asyncio.Event) -> None:
    await source.wait()
    target.set()


def _slug(text: str) -> str:
    ascii_text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
    slug = re.sub(r"[^a-z0-9]+", "-", ascii_text.lower()).strip("-")[:40].strip("-")
    if not slug:
        raise ProjectError("A feature precisa de um nome com letras ou números.")
    return slug


def _clean(aliases: list[str]) -> list[str]:
    return [a.strip() for a in aliases if a.strip()]
