"""The Claude plan's usage windows, as the CLI reports them, and the panel's usage view."""

from typing import Literal

from pydantic import BaseModel

LimitStatus = Literal["allowed", "allowed_warning", "rejected"]


class RateLimit(BaseModel):
    window: str  # five_hour | seven_day | seven_day_opus | seven_day_sonnet | overage | unknown
    status: LimitStatus
    utilization: float | None  # share used, 0 to 1; the CLI doesn't always send it
    resets_at: int | None  # unix seconds
    read_at: float  # unix seconds of the last report, so the panel can say how old it is


class SessionUsage(BaseModel):
    name: str
    tokens: int  # spent since the server started or the session was cleared
    context_tokens: int | None
    context_max: int | None


class UsageView(BaseModel):
    limits: list[RateLimit]  # empty until a task reports one after the server starts
    sessions: list[SessionUsage]
    open_sessions: int  # claude processes open for sessions
    max_active_sessions: int
