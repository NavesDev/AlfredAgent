from fastapi import FastAPI

from api import ws
from api.routes import sessions


def create_app() -> FastAPI:
    """main attaches the event bus and the sessions later, as app.state.bus/.sessions."""
    app = FastAPI(title="Alfred")
    app.include_router(ws.router)
    app.include_router(sessions.router)

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    return app
