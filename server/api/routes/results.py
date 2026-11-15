"""Results for the panel, the overlay and the viewer (ADR 0014).

Files go only to this computer: a client that is not loopback gets 403 (RN-12).
"""

import ipaddress
from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, Request, Response
from fastapi.responses import FileResponse
from pydantic import BaseModel

from controllers.results import Results
from errors import FileGone, ResultNotFound, ResultNotReadable, SessionNotFound
from models.result import MAX_PER_SESSION, PresentMode, ResultView

router = APIRouter(prefix="/api/results", tags=["results"])
presentation = APIRouter(prefix="/api/presentation", tags=["results"])


class Present(BaseModel):
    mode: PresentMode


def _results(request: Request) -> Results:
    results: Results = request.app.state.results
    return results


def _loopback(request: Request) -> bool:
    """Fail-closed: no client address, or one that does not parse, is not this computer."""
    host = request.client.host if request.client else ""
    try:
        address = ipaddress.ip_address(host)
    except ValueError:
        return False
    if isinstance(address, ipaddress.IPv6Address) and address.ipv4_mapped:
        address = address.ipv4_mapped
    return address.is_loopback


@router.get("")
async def list_results(
    session: str,
    request: Request,
    limit: Annotated[int, Query(ge=1, le=MAX_PER_SESSION)] = MAX_PER_SESSION,
) -> list[ResultView]:
    try:
        return _results(request).list(session, limit)
    except SessionNotFound as e:
        raise HTTPException(404, str(e)) from e


@router.get("/{result_id}")
async def get_result(result_id: int, request: Request) -> ResultView:
    try:
        return _results(request).get(result_id)
    except ResultNotFound as e:
        raise HTTPException(404, str(e)) from e


@router.get("/{result_id}/files/{index}", response_class=FileResponse)
async def get_file(result_id: int, index: int, request: Request) -> FileResponse:
    if not _loopback(request):
        raise HTTPException(403, "Arquivos só no computador.")
    try:
        path = _results(request).file(result_id, index)
    except ResultNotFound as e:
        raise HTTPException(404, str(e)) from e
    except ResultNotReadable as e:
        raise HTTPException(403, str(e)) from e
    except FileGone as e:
        raise HTTPException(410, str(e)) from e
    return FileResponse(path, headers={"Cache-Control": "no-store"})


@router.post("/{result_id}/present", status_code=204)
async def present(result_id: int, body: Present, request: Request) -> Response:
    try:
        _results(request).present(result_id, body.mode)
    except ResultNotFound as e:
        raise HTTPException(404, str(e)) from e
    return Response(status_code=204)


@presentation.post("/close", status_code=204)
async def close(request: Request) -> Response:
    _results(request).close()
    return Response(status_code=204)
