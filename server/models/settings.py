"""Runtime settings edited on the panel: model and effort per agent kind, session limits, and
how big the panel draws the session characters.

config.yaml only seeds these on the first boot.
"""

import json
import sqlite3
from typing import Literal

from pydantic import BaseModel

Effort = str  # "low" | "medium" | "high" | "xhigh" | "max"; validated by the controller
# Where everything that floats on the desktop anchors (ADR 0014)
OverlayPosition = Literal[
    "top_right", "top_center", "top_left", "bottom_right", "bottom_center", "bottom_left"
]


class AgentSettings(BaseModel):
    kind: str
    model: str
    effort: Effort | None = None


class AppSettings(BaseModel):
    max_active_sessions: int = 3
    idle_minutes: int = 10
    mcp_disabled: list[str] = []
    image_mcp: str | None = None  # favorite image generator; None lets the model pick
    implementation_mode: Literal["worktree", "ambiente"] = "worktree"  # workspaces may override
    overlay_position: OverlayPosition = "top_right"


class Defaults(BaseModel):
    models: dict[str, str]
    max_active_sessions: int
    idle_minutes: int


def seed(db: sqlite3.Connection, defaults: Defaults) -> None:
    """Writes whatever is missing; never overwrites what the panel saved."""
    stored = load_agents(db)
    for kind, model in defaults.models.items():
        if kind not in stored:
            save_agent(db, AgentSettings(kind=kind, model=model))
    if db.execute("SELECT COUNT(*) FROM app_settings").fetchone()[0] == 0:
        save_app(
            db,
            AppSettings(
                max_active_sessions=defaults.max_active_sessions,
                idle_minutes=defaults.idle_minutes,
            ),
        )


def load_agents(db: sqlite3.Connection) -> dict[str, AgentSettings]:
    rows = db.execute("SELECT kind, model, effort FROM agent_settings")
    return {row["kind"]: AgentSettings(**dict(row)) for row in rows}


def save_agent(db: sqlite3.Connection, agent: AgentSettings) -> None:
    db.execute(
        "INSERT INTO agent_settings (kind, model, effort) VALUES (?, ?, ?)"
        " ON CONFLICT (kind) DO UPDATE SET model = excluded.model, effort = excluded.effort",
        (agent.kind, agent.model, agent.effort),
    )


def load_app(db: sqlite3.Connection) -> AppSettings:
    values = {
        row["key"]: json.loads(row["value"]) for row in db.execute("SELECT * FROM app_settings")
    }
    return AppSettings(**values)


def save_app(db: sqlite3.Connection, app: AppSettings) -> None:
    for key, value in app.model_dump().items():
        db.execute(
            "INSERT INTO app_settings (key, value) VALUES (?, ?)"
            " ON CONFLICT (key) DO UPDATE SET value = excluded.value",
            (key, json.dumps(value)),
        )
