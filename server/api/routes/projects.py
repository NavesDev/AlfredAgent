"""Projects and workspaces for the panel. Async so SQLite stays on the event loop's thread."""

from fastapi import APIRouter, HTTPException, Request, Response
from pydantic import BaseModel

from controllers.projects import Projects
from errors import GitError, ProjectError, ProjectInUse, ProjectNotFound
from models.project import Project, Workspace

router = APIRouter(prefix="/api", tags=["projects"])


class NewProject(BaseModel):
    name: str
    aliases: list[str] = []
    description: str = ""


class ProjectChange(BaseModel):
    name: str | None = None
    aliases: list[str] | None = None
    description: str | None = None


class NewWorkspace(BaseModel):
    name: str
    path: str
    description: str = ""


class NewWorktree(BaseModel):
    parent_id: int
    name: str
    description: str = ""


class WorkspaceChange(BaseModel):
    description: str


def _projects(request: Request) -> Projects:
    projects: Projects = request.app.state.projects
    return projects


def _http(e: Exception) -> HTTPException:
    if isinstance(e, ProjectNotFound):
        return HTTPException(404, str(e))
    if isinstance(e, ProjectInUse):
        return HTTPException(409, str(e))
    return HTTPException(422, str(e))


@router.get("/projects")
async def list_projects(request: Request) -> list[Project]:
    return _projects(request).all()


@router.post("/projects", status_code=201)
async def create_project(body: NewProject, request: Request) -> Project:
    try:
        return _projects(request).create(body.name, body.aliases, body.description)
    except ProjectError as e:
        raise _http(e) from e


@router.get("/projects/{id}")
async def get_project(id: int, request: Request) -> Project:
    try:
        return _projects(request).get(id)
    except ProjectError as e:
        raise _http(e) from e


@router.patch("/projects/{id}")
async def update_project(id: int, body: ProjectChange, request: Request) -> Project:
    try:
        return _projects(request).update(id, body.name, body.aliases, body.description)
    except ProjectError as e:
        raise _http(e) from e


@router.delete("/projects/{id}", status_code=204)
async def delete_project(id: int, request: Request) -> Response:
    try:
        _projects(request).delete(id)
    except ProjectError as e:
        raise _http(e) from e
    return Response(status_code=204)


@router.post("/projects/{id}/workspaces", status_code=201)
async def add_workspace(id: int, body: NewWorkspace, request: Request) -> Workspace:
    try:
        return _projects(request).add_workspace(id, body.name, body.path, body.description)
    except ProjectError as e:
        raise _http(e) from e


@router.post("/projects/{id}/worktrees", status_code=201)
async def add_worktree(id: int, body: NewWorktree, request: Request) -> Workspace:
    try:
        return await _projects(request).add_worktree(
            id, body.parent_id, body.name, body.description
        )
    except (ProjectError, GitError) as e:
        raise _http(e) from e


@router.patch("/workspaces/{id}")
async def update_workspace(id: int, body: WorkspaceChange, request: Request) -> Workspace:
    try:
        return _projects(request).update_workspace(id, body.description)
    except ProjectError as e:
        raise _http(e) from e


@router.delete("/workspaces/{id}", status_code=204)
async def delete_workspace(id: int, request: Request, force: bool = False) -> Response:
    try:
        await _projects(request).delete_workspace(id, force)
    except (ProjectError, GitError) as e:
        raise _http(e) from e
    return Response(status_code=204)
