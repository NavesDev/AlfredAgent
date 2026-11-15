"""GitHub issues for the main agent, through the gh CLI the user is logged in to (ADR 0011).

Arguments are fixed and read-only, run without a shell, in the workspace's folder so gh picks
the repo from its remote. Alfred never gets gh itself.
"""

import asyncio
import json
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from errors import GitHubError

ERROR_MAX = 200
BODY_MAX = 4000
COMMENTS = 5
LIST_LIMIT = 20
STATES = ("open", "closed", "all")

Run = Callable[..., Awaitable[str]]


@dataclass(frozen=True)
class Issue:
    number: int
    title: str
    state: str = ""
    labels: list[str] | None = None
    body: str = ""
    url: str = ""
    comments: list[str] | None = None  # "<login>: <text>", the last ones


async def _gh(cwd: Path, *args: str) -> str:
    try:
        process = await asyncio.create_subprocess_exec(
            "gh",
            *args,
            cwd=cwd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
    except OSError as e:
        raise GitHubError(f"Não consegui rodar o gh: {e}") from e
    out, err = await process.communicate()
    if process.returncode != 0:
        raise GitHubError(err.decode().strip()[:ERROR_MAX] or f"gh {args[0]} falhou")
    return out.decode()


def _labels(raw: dict[str, Any]) -> list[str]:
    return [str(label["name"]) for label in raw.get("labels") or []]


async def issue(repo: Path, number: int, run: Run = _gh) -> Issue:
    raw = json.loads(
        await run(
            repo,
            "issue",
            "view",
            str(int(number)),
            "--json",
            "number,title,state,labels,body,url,comments",
        )
    )
    comments = [
        f"{c.get('author', {}).get('login', '?')}: {c.get('body', '')}"
        for c in (raw.get("comments") or [])[-COMMENTS:]
    ]
    return Issue(
        number=int(raw["number"]),
        title=str(raw["title"]),
        state=str(raw.get("state", "")),
        labels=_labels(raw),
        body=str(raw.get("body") or "")[:BODY_MAX],
        url=str(raw.get("url", "")),
        comments=comments,
    )


async def issues(repo: Path, search: str | None, state: str, run: Run = _gh) -> list[Issue]:
    if state not in STATES:
        raise GitHubError(f"Estado inválido: {state!r}. Use open, closed ou all.")
    args = [
        "issue",
        "list",
        "--state",
        state,
        "--limit",
        str(LIST_LIMIT),
        "--json",
        "number,title,labels",
    ]
    if search:
        args.append(f"--search={search}")  # one value, never parsed as another flag
    raw = json.loads(await run(repo, *args))
    return [Issue(int(i["number"]), str(i["title"]), labels=_labels(i)) for i in raw]
