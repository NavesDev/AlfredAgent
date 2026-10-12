from fastapi import FastAPI

from api import ws
from api.routes import alfred, projects, sessions, settings, usage


def create_app() -> FastAPI:
    """main attaches the bus and controllers later.

    app.state: .bus, .alfred, .sessions, .projects, .settings, .usage.
    """
    app = FastAPI(title="Alfred")
    app.include_router(ws.router)
    app.include_router(alfred.router)
    app.include_router(sessions.router)
    app.include_router(projects.router)
    app.include_router(settings.router)
    app.include_router(usage.router)

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    return app
