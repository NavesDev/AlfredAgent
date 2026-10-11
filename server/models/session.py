"""What the panel and Alfred see of a named session."""

from typing import Literal

from pydantic import BaseModel

Status = Literal["idle", "busy", "error"]


class SessionView(BaseModel):
    name: str
    kind: str
    label: str
    model: str
    cwd: str
    status: Status
    task: str | None
    activity: str | None
    queue: int
    tasks_done: int
    tokens: int
    last_summary: str | None
    protected: bool
