"""Named sessions for the panel: list, clear, delete. Creating is by voice only (ADR 0007)."""

from fastapi import APIRouter, HTTPException, Request, Response

from controllers.sessions import Sessions
from errors import SessionNotFound, SessionProtected
from models.session import SessionView

router = APIRouter(prefix="/api/sessions", tags=["sessions"])


def _sessions(request: Request) -> Sessions:
    sessions: Sessions = request.app.state.sessions
    return sessions


@router.get("")
def list_sessions(request: Request) -> list[SessionView]:
    return _sessions(request).list()


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
