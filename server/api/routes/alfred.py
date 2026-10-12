"""The main agent for the panel: clear its conversation."""

from fastapi import APIRouter, Request, Response

from infra.claude.alfred import AlfredAgent

router = APIRouter(prefix="/api/alfred", tags=["alfred"])


@router.post("/clear", status_code=204)
async def clear_alfred(request: Request) -> Response:
    agent: AlfredAgent = request.app.state.alfred
    await agent.reset()
    return Response(status_code=204)
