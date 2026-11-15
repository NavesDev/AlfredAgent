"""Opens a file in its default app, or shows it in its folder, on this computer (ADR 0014)."""

import asyncio
from pathlib import Path

from errors import OpenerError

ERROR_MAX = 200


async def _run(*args: str) -> None:
    try:
        process = await asyncio.create_subprocess_exec(
            *args, stdout=asyncio.subprocess.DEVNULL, stderr=asyncio.subprocess.PIPE
        )
    except OSError as e:
        raise OpenerError(str(e)) from e
    _, err = await process.communicate()
    if process.returncode != 0:
        raise OpenerError(err.decode().strip()[:ERROR_MAX] or f"{args[0]} failed")


async def open_path(path: Path, reveal: bool) -> None:
    """`reveal` selects the file in the file manager (FileManager1 over D-Bus), else opens its
    folder; otherwise the file opens in its default app."""
    if not reveal:
        await _run("xdg-open", str(path))
        return
    try:
        await _run(
            "gdbus", "call", "--session",
            "--dest", "org.freedesktop.FileManager1",
            "--object-path", "/org/freedesktop/FileManager1",
            "--method", "org.freedesktop.FileManager1.ShowItems",
            f"['{path.as_uri()}']", "",
        )  # fmt: skip
    except OpenerError:
        await _run("xdg-open", str(path.parent))
