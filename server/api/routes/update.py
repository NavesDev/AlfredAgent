"""Release check and self-update (ADR 0013)."""

from fastapi import APIRouter, HTTPException, Request

from controllers.updates import Updates
from errors import UpdateError
from models.update import UpdateView

router = APIRouter(prefix="/api/update", tags=["update"])


def _updates(request: Request) -> Updates:
    updates: Updates = request.app.state.updates
    return updates


@router.get("")
async def get_update(request: Request) -> UpdateView:
    return _updates(request).view()


@router.post("/check")
async def check_update(request: Request) -> UpdateView:
    return await _updates(request).check()


@router.post("/apply", status_code=202)
async def apply_update(request: Request) -> UpdateView:
    try:
        return await _updates(request).apply()
    except UpdateError as e:
        raise HTTPException(409, str(e)) from e
