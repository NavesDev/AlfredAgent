"""Projects and their workspaces: any folder, or a git worktree made from a workspace."""

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Protocol

from errors import ProjectError, ProjectInUse, ProjectNotFound
from events import EventBus
from infra import git as real_git
from models import project
from models import session as records
from models.project import Project, Workspace


class Git(Protocol):
    async def add_worktree(self, parent: Path, name: str) -> tuple[Path, str]: ...
    async def remove_worktree(self, path: Path, force: bool) -> None: ...
    async def is_dirty(self, path: Path) -> bool: ...


class Projects:
    def __init__(self, db: sqlite3.Connection, bus: EventBus, git: Git = real_git) -> None:
        self._db, self._bus, self._git = db, bus, git

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

    def create(self, name: str, aliases: list[str]) -> Project:
        name = self._free_name(name)
        created = project.insert_project(self._db, name, _clean(aliases))
        self._bus.publish("project_created", project=created.model_dump())
        return created

    def update(self, id: int, name: str | None = None, aliases: list[str] | None = None) -> Project:
        current = self.get(id)
        if name is not None and name.strip().lower() != current.name.lower():
            name = self._free_name(name)
        project.update_project(
            self._db,
            id,
            name.strip() if name else None,
            _clean(aliases) if aliases is not None else None,
        )
        return self._publish_updated(id)

    def delete(self, id: int) -> None:
        current = self.get(id)
        if current.workspaces:
            raise ProjectInUse(f"O projeto {current.name} ainda tem workspaces. Apague-os antes.")
        project.delete_project(self._db, id)
        self._bus.publish("project_deleted", id=id)

    def add_workspace(self, project_id: int, name: str, path: str) -> Workspace:
        current = self.get(project_id)
        name = self._free_workspace_name(current, name)
        folder = Path(path).expanduser()
        if not folder.is_dir():
            raise ProjectError(f"A pasta {path} não existe.")
        ws = project.insert_workspace(self._db, project_id, name, str(folder), "folder")
        self._publish_updated(project_id)
        return ws

    async def add_worktree(self, project_id: int, parent_id: int, name: str) -> Workspace:
        current = self.get(project_id)
        name = self._free_workspace_name(current, name)
        parent = next((w for w in current.workspaces if w.id == parent_id), None)
        if parent is None:
            raise ProjectNotFound(f"O workspace de origem não existe no projeto {current.name}.")
        path, branch = await self._git.add_worktree(Path(parent.path), name)
        ws = project.insert_workspace(
            self._db, project_id, name, str(path), "worktree", parent.id, branch
        )
        self._publish_updated(project_id)
        return ws

    async def delete_workspace(self, id: int, force: bool = False) -> None:
        ws = project.get_workspace(self._db, id)
        if ws is None:
            raise ProjectNotFound("Esse workspace não existe.")
        if names := records.sessions_in_workspace(self._db, id):
            raise ProjectInUse(f"O workspace {ws.name} tem sessões: {', '.join(names)}.")
        children = [
            w.name for w in project.workspaces_of(self._db, ws.project_id) if w.parent_id == id
        ]
        if children:
            raise ProjectInUse(f"O workspace {ws.name} tem worktrees: {', '.join(children)}.")
        if ws.kind == "worktree":
            path = Path(ws.path)
            if not force and await self._git.is_dirty(path):
                raise ProjectInUse(f"O worktree {ws.name} tem mudanças não commitadas.")
            await self._git.remove_worktree(path, force)
        project.delete_workspace(self._db, id)
        self._publish_updated(ws.project_id)

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
            raise ProjectError("O workspace precisa de um nome.")
        if any(w.name.lower() == name.lower() for w in current.workspaces):
            raise ProjectError(f"O projeto {current.name} já tem um workspace chamado {name}.")
        return name

    def _publish_updated(self, id: int) -> Project:
        updated = self.get(id)
        self._bus.publish("project_updated", project=updated.model_dump())
        return updated


def _clean(aliases: list[str]) -> list[str]:
    return [a.strip() for a in aliases if a.strip()]
