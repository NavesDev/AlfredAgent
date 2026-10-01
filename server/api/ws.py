"""Streams every bus event to the web app as JSON."""

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

router = APIRouter()


@router.websocket("/ws")
async def events(ws: WebSocket) -> None:
    bus = ws.app.state.bus
    queue = bus.subscribe()  # before accept, so nothing published after connect is lost
    await ws.accept()
    try:
        while True:
            await ws.send_json(await queue.get())
    except WebSocketDisconnect:
        pass
    finally:
        bus.unsubscribe(queue)
