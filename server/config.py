from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, ValidationError

from errors import ConfigError
from infra.claude.agents import KINDS
from models.settings import Defaults


class Whisper(BaseModel):
    model: str
    device: Literal["cpu", "cuda"]
    compute_type: str
    language: str
    initial_prompt: str = ""


class Kokoro(BaseModel):
    voice: str
    speed: float = 1.0
    acknowledgements: list[str] = []


class Wakeword(BaseModel):
    name: str = "Alfred"
    model: str
    threshold: float


class Listener(BaseModel):
    sample_rate: int = 16000
    silence_ms: int = 1200
    max_record_s: int = 15


class Agents(BaseModel):
    default_model: str
    models: dict[str, str] = {}  # seeds per kind ("alfred", "geral", "implementacao")
    timeout_s: int = 60


class Limits(BaseModel):
    max_active_sessions: int = 3
    idle_minutes: int = 10


class Api(BaseModel):
    host: str = "0.0.0.0"
    port: int = 8000


class Storage(BaseModel):
    state_path: Path
    db_path: Path = Path("data/alfred.sqlite3")


class Config(BaseModel):
    whisper: Whisper
    kokoro: Kokoro
    wakeword: Wakeword
    listener: Listener = Listener()
    agents: Agents
    limits: Limits = Limits()
    api: Api = Api()
    storage: Storage

    def seed_defaults(self) -> Defaults:
        """What the settings table starts with; the panel edits them afterwards."""
        kinds = ("alfred", *KINDS)
        return Defaults(
            models={k: self.agents.models.get(k, self.agents.default_model) for k in kinds},
            max_active_sessions=self.limits.max_active_sessions,
            idle_minutes=self.limits.idle_minutes,
        )


def load_config(path: Path) -> Config:
    if not path.exists():
        raise ConfigError(f"config not found: {path}")
    try:
        return Config.model_validate(yaml.safe_load(path.read_text()))
    except (yaml.YAMLError, ValidationError) as e:
        raise ConfigError(f"invalid config {path}: {e}") from e
