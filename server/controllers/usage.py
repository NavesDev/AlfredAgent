"""Keeps the latest report of each plan usage window and joins it with the session slots."""

import time
from collections.abc import Callable
from typing import Any

from controllers.sessions import Sessions
from controllers.settings import Settings
from events import EventBus
from models.usage import RateLimit, SessionUsage, UsageView


class Usage:
    def __init__(
        self,
        bus: EventBus,
        sessions: Sessions,
        settings: Settings,
        task_timeout_s: int,
        clock: Callable[[], float] = time.time,
    ) -> None:
        self._bus, self._sessions, self._settings = bus, sessions, settings
        self._timeout_s, self._clock = task_timeout_s, clock
        self._limits: dict[str, RateLimit] = {}

    def view(self) -> UsageView:
        sessions = self._sessions.list()
        return UsageView(
            limits=list(self._limits.values()),
            sessions=[
                SessionUsage(
                    name=v.name,
                    tokens=v.tokens,
                    context_tokens=v.context_tokens,
                    context_max=v.context_max,
                )
                for v in sessions
            ],
            open_sessions=sum(v.connected for v in sessions),
            max_active_sessions=self._settings.app().max_active_sessions,
            task_timeout_s=self._timeout_s,
        )

    def apply(self, event: dict[str, Any]) -> None:
        """A report may leave out the share used; keep the last known one then."""
        before = self._limits.get(event["window"])
        utilization = event.get("utilization")
        if utilization is None and before is not None:
            utilization = before.utilization
        self._limits[event["window"]] = RateLimit(
            window=event["window"],
            status=event["status"],
            utilization=utilization,
            resets_at=event.get("resets_at") or (before.resets_at if before else None),
            read_at=self._clock(),
        )

    async def run(self) -> None:
        queue = self._bus.subscribe()
        try:
            while True:
                event = await queue.get()
                if event["type"] == "rate_limit":
                    self.apply(event)
        finally:
            self._bus.unsubscribe(queue)
