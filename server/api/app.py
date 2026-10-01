from fastapi import FastAPI

from api import ws


def create_app() -> FastAPI:
    """The event bus is attached later as app.state.bus by main."""
    app = FastAPI(title="Alfred")
    app.include_router(ws.router)

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    return app
