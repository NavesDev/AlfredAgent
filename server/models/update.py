"""Release tags (`vX.Y.Z`), their CHANGELOG notes and the panel's update view (ADR 0013)."""

import re
from collections.abc import Iterable
from typing import Literal

from pydantic import BaseModel

_TAG = re.compile(r"v(\d+)\.(\d+)\.(\d+)")


def parse_version(tag: str) -> tuple[int, int, int] | None:
    """Release tags only: `v1.2.3`; pre-releases and other tags are ignored."""
    match = _TAG.fullmatch(tag)
    return (int(match[1]), int(match[2]), int(match[3])) if match else None


def newest(tags: Iterable[str]) -> str | None:
    versions = [(v, t) for t in tags if (v := parse_version(t))]
    return max(versions)[1] if versions else None


def notes_for(changelog: str, tag: str) -> str:
    """The body of the `## [X.Y.Z]` section, without its heading."""
    out: list[str] = []
    inside = False
    for line in changelog.splitlines():
        if line.startswith("## "):
            if inside:
                break
            inside = line.startswith(f"## [{tag.removeprefix('v')}]")
        elif inside:
            out.append(line)
    return re.sub(r"\n{3,}", "\n\n", "\n".join(out)).strip()


class UpdateResult(BaseModel):
    """What the update script wrote when it last ran."""

    previous: str | None = None  # "from" in the script's file
    to: str
    ok: bool
    error: str | None = None
    at: float  # unix seconds


class UpdateView(BaseModel):
    current: str | None  # newest local release tag
    latest: str | None  # newest tag on origin
    available: bool
    notes: str  # CHANGELOG section of `latest` when available, markdown
    status: Literal["idle", "checking", "updating", "error"]
    error: str | None
    checked_at: float | None  # unix seconds
    last: UpdateResult | None
