"""git worktree add/remove, run as subprocesses without blocking the loop."""

import asyncio
from pathlib import Path

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


async def add_worktree(parent: Path, name: str) -> tuple[Path, str]:
    """Creates <parent>-wt/<name> on branch <name>, new from HEAD unless it already exists."""
    path = parent.parent / f"{parent.name}-wt" / name
    branches = await _git(parent, "branch", "--list", name)
    if branches.strip():
        await _git(parent, "worktree", "add", str(path), name)
    else:
        await _git(parent, "worktree", "add", str(path), "-b", name)
    return path, name


async def remove_worktree(path: Path, force: bool) -> None:
    await _git(path, "worktree", "remove", *(["--force"] if force else []), str(path))


async def is_dirty(path: Path) -> bool:
    return bool((await _git(path, "status", "--porcelain")).strip())
