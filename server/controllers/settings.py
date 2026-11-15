"""Settings edited on the panel: model and effort per agent kind, limits, disabled MCP servers
and the favorite image generator.

Sessions read them on every connect, so changes apply to the next connection.
"""

import asyncio
import logging
import sqlite3
from collections.abc import Awaitable, Callable

from pydantic import BaseModel

from errors import SettingsError
from events import EventBus
from infra.claude.agents import KINDS
from models import settings as model

log = logging.getLogger(__name__)

AGENT_KINDS = ("alfred", *KINDS)
EFFORTS = ("low", "medium", "high", "xhigh", "max")


class SettingsView(BaseModel):
    agents: list[model.AgentSettings]
    max_active_sessions: int
    idle_minutes: int
    mcp_disabled: list[str]
    image_mcp: str | None
    image_mcp_servers: list[str]  # user-scope MCP servers that can be the image generator
    known_mcp_servers: list[str]  # user-scope servers plus the ones sessions reported


class SettingsUpdate(BaseModel):
    agents: list[model.AgentSettings] = []
    max_active_sessions: int | None = None
    idle_minutes: int | None = None
    mcp_disabled: list[str] | None = None
    image_mcp: str | None = None  # "" goes back to automatic


class Settings:
    def __init__(
        self,
        db: sqlite3.Connection,
        bus: EventBus,
        image_servers: Callable[[], list[str]] = list,
        mcp_servers: Callable[[], Awaitable[list[str]]] | None = None,
    ) -> None:
        self._db, self._bus, self._image_servers = db, bus, image_servers
        self._mcp_servers = mcp_servers
        self._known_mcp: set[str] = set()

    def get(self) -> SettingsView:
        app = self.app()
        agents = model.load_agents(self._db)
        user_servers = self._image_servers()
        return SettingsView(
            agents=[agents[k] for k in AGENT_KINDS if k in agents],
            max_active_sessions=app.max_active_sessions,
            idle_minutes=app.idle_minutes,
            mcp_disabled=app.mcp_disabled,
            image_mcp=app.image_mcp,
            image_mcp_servers=sorted(user_servers),
            known_mcp_servers=sorted(self._known_mcp | set(user_servers)),
        )

    def app(self) -> model.AppSettings:
        return model.load_app(self._db)

    def update(self, update: SettingsUpdate) -> SettingsView:
        for agent in update.agents:
            _validate(agent)
        app = self.app().model_copy(
            update={k: v for k, v in update.model_dump(exclude={"agents"}).items() if v is not None}
        )
        app.image_mcp = (app.image_mcp or "").strip() or None
        if app.max_active_sessions < 1:
            raise SettingsError("O limite de sessões precisa ser pelo menos 1.")
        if app.idle_minutes < 1:
            raise SettingsError("O tempo ocioso precisa ser pelo menos 1 minuto.")
        for agent in update.agents:
            model.save_agent(self._db, agent.model_copy(update={"model": agent.model.strip()}))
        model.save_app(self._db, app)
        view = self.get()
        self._bus.publish("settings_updated", settings=view.model_dump())
        return view

    def resolve(
        self, kind: str, model_override: str | None, effort: str | None
    ) -> tuple[str, str | None]:
        """Model and effort of a session: its own override, else its kind's setting."""
        agent = model.load_agents(self._db)[kind]
        return model_override or agent.model, effort or agent.effort

    async def run(self) -> None:
        """Remembers the MCP servers the CLI and sessions report, as suggestions for the panel."""
        queue = self._bus.subscribe()
        try:
            if self._mcp_servers:
                try:
                    self._known_mcp.update(await self._mcp_servers())
                except Exception:  # sessions still report theirs when they connect
                    log.warning("could not list the MCP servers", exc_info=True)
            while True:
                event = await queue.get()
                if event["type"] == "mcp_servers_seen":
                    self._known_mcp.update(event["names"])
        except asyncio.CancelledError:
            self._bus.unsubscribe(queue)
            raise


def _validate(agent: model.AgentSettings) -> None:
    if agent.kind not in AGENT_KINDS:
        raise SettingsError(f"Não conheço o tipo {agent.kind}.")
    if not agent.model.strip():
        raise SettingsError(f"O tipo {agent.kind} precisa de um modelo.")
    if agent.effort is not None and agent.effort not in EFFORTS:
        raise SettingsError(f"Effort inválido: {agent.effort}. Use {', '.join(EFFORTS)}.")
