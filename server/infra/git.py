"""git worktrees and status, run as subprocesses without blocking the loop, plus a watcher of
the worktrees each repo has (ADR 0011)."""

import asyncio
from collections.abc import AsyncIterator, Iterable
from dataclasses import dataclass
from pathlib import Path

import watchfiles

from errors import GitError

ERROR_MAX = 200


async def _git(cwd: Path, *args: str) -> str:
    try:
        process = await asyncio.create_subprocess_exec(
            "git",
            *args,
            cwd=cwd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
    except OSError as e:
        raise GitError(str(e)) from e
    out, err = await process.communicate()
    if process.returncode != 0:
        raise GitError(err.decode().strip()[:ERROR_MAX] or f"git {args[0]} failed")
    return out.decode()


async def add_worktree(parent: Path, name: str, branch: str | None = None) -> tuple[Path, str]:
    """Creates <parent>-wt/<name> on <branch> (default: the name), new from HEAD unless the
    branch already exists."""
    branch = branch or name
    path = parent.parent / f"{parent.name}-wt" / name
    branches = await _git(parent, "branch", "--list", branch)
    if branches.strip():
        await _git(parent, "worktree", "add", str(path), branch)
    else:
        await _git(parent, "worktree", "add", str(path), "-b", branch)
    return path, branch


async def remove_worktree(path: Path, force: bool) -> None:
    await _git(path, "worktree", "remove", *(["--force"] if force else []), str(path))


async def is_dirty(path: Path) -> bool:
    return bool((await _git(path, "status", "--porcelain")).strip())


@dataclass(frozen=True)
class GitSummary:
    branch: str
    changed: int  # files modified, added, deleted or untracked
    commits: list[str]  # "<short hash> <subject>", newest first
    branches: list[str]  # local branches, most recently committed first: naming patterns


async def summary(path: Path, commits: int = 5, branches: int = 10) -> GitSummary:
    branch = (await _git(path, "branch", "--show-current")).strip() or "HEAD solto"
    status = await _git(path, "status", "--porcelain")
    log = await _git(path, "log", f"-{commits}", "--format=%h %s")
    refs = await _git(
        path,
        "for-each-ref",
        "--sort=-committerdate",
        f"--count={branches}",
        "--format=%(refname:short)",
        "refs/heads",
    )
    return GitSummary(branch, len(status.splitlines()), log.splitlines(), refs.split())


async def common_dir(path: Path) -> Path:
    """The .git folder shared by a repo and all its worktrees."""
    out = await _git(path, "rev-parse", "--path-format=absolute", "--git-common-dir")
    return Path(out.strip())


async def list_worktrees(repo: Path) -> list[tuple[Path, str | None]]:
    """The repo's linked worktrees as (folder, branch); branch is None when detached."""
    entries: list[tuple[Path, str | None]] = []
    for block in (await _git(repo, "worktree", "list", "--porcelain")).split("\n\n"):
        lines = dict(line.partition(" ")[::2] for line in block.splitlines() if line)
        if "worktree" in lines and "bare" not in lines:
            branch = lines.get("branch", "").removeprefix("refs/heads/") or None
            entries.append((Path(lines["worktree"]), branch))
    return entries[1:]  # the first entry is the main checkout


def _worktrees_change(_: watchfiles.Change, path: str) -> bool:
    p = Path(path)
    return p.name == "worktrees" or p.parent.name == "worktrees"


async def watch_worktrees(commons: Iterable[Path], stop: asyncio.Event) -> AsyncIterator[Path]:
    """Yields a repo's common dir whenever a worktree is added to or removed from it.

    Watches, without recursion, each common dir (to see its worktrees/ folder appear) and its
    worktrees/ folder; nothing else in .git wakes it up."""
    paths = [p for c in commons for p in (c, c / "worktrees") if p.is_dir()]
    if not paths:
        await stop.wait()
        return
    async for changes in watchfiles.awatch(
        *paths,
        watch_filter=_worktrees_change,
        recursive=False,
        debounce=1000,
        stop_event=stop,
    ):
        changed = {
            p.parent if p.name == "worktrees" else p.parent.parent
            for p in (Path(path) for _, path in changes)
        }
        for common in sorted(changed):
            yield common
