"""Named sessions for the panel: list, create, change model/effort, clear, delete, portrait.

Routes are async so SQLite stays on the event loop's thread.
"""

from fastapi import APIRouter, HTTPException, Request, Response
from fastapi.responses import FileResponse
from pydantic import BaseModel

from controllers.portraits import Portraits
from controllers.sessions import Sessions
from errors import SessionError, SessionNotFound, SessionProtected
from models.session import SessionView

router = APIRouter(prefix="/api/sessions", tags=["sessions"])


class NewSession(BaseModel):
    kind: str
    name: str
    workspace_id: int | None = None
    model: str | None = None
    effort: str | None = None
    aliases: list[str] = []


class SessionChange(BaseModel):
    model: str | None = None  # "" goes back to the kind's setting
    effort: str | None = None
    aliases: list[str] | None = None  # replaces the list


def _sessions(request: Request) -> Sessions:
    sessions: Sessions = request.app.state.sessions
    return sessions


@router.get("")
async def list_sessions(request: Request) -> list[SessionView]:
    return _sessions(request).list()


@router.post("", status_code=201)
async def create_session(body: NewSession, request: Request) -> SessionView:
    try:
        return _sessions(request).create(
            body.kind, body.name, body.workspace_id, body.model, body.effort, body.aliases
        )
    except SessionError as e:
        raise HTTPException(422, str(e)) from e


@router.patch("/{name}")
async def update_session(name: str, body: SessionChange, request: Request) -> SessionView:
    try:
        sessions = _sessions(request)
        if body.aliases is not None:
            name = sessions.set_aliases(name, body.aliases).name  # may have been an old alias
        return sessions.update(name, body.model, body.effort)
    except SessionNotFound as e:
        raise HTTPException(404, str(e)) from e
    except SessionError as e:
        raise HTTPException(422, str(e)) from e


@router.post("/{name}/clear")
async def clear_session(name: str, request: Request) -> SessionView:
    try:
        return await _sessions(request).clear(name)
    except SessionNotFound as e:
        raise HTTPException(404, str(e)) from e


@router.delete("/{name}", status_code=204)
async def delete_session(name: str, request: Request) -> Response:
    try:
        await _sessions(request).delete(name)
    except SessionNotFound as e:
        raise HTTPException(404, str(e)) from e
    except SessionProtected as e:
        raise HTTPException(409, str(e)) from e
    return Response(status_code=204)


def _portraits(request: Request) -> Portraits:
    portraits: Portraits = request.app.state.portraits
    return portraits


@router.get("/{name}/portrait", response_class=FileResponse)
async def get_portrait(name: str, request: Request) -> FileResponse:
    path = _portraits(request).file(name)
    if path is None:
        raise HTTPException(404, f"A sessão {name} ainda não tem retrato.")
    return FileResponse(path, headers={"Cache-Control": "max-age=31536000, immutable"})


@router.post("/{name}/portrait", status_code=202)
async def repaint(name: str, request: Request) -> Response:
    """Paints the portrait again in the background."""
    try:
        _portraits(request).request(name)
    except SessionNotFound as e:
        raise HTTPException(404, str(e)) from e
    return Response(status_code=202)
