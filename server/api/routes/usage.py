"""Plan usage windows and session slots for the header meter and the settings page."""

from fastapi import APIRouter, Request

from controllers.usage import Usage
from models.usage import UsageView

router = APIRouter(prefix="/api/usage", tags=["usage"])


@router.get("")
async def get_usage(request: Request) -> UsageView:
    usage: Usage = request.app.state.usage
    return usage.view()
