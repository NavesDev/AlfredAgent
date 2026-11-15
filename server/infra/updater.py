"""Starts scripts/alfred-update.sh detached from the server, which it stops and restarts."""

import os
import subprocess
from collections.abc import Callable
from pathlib import Path

from errors import UpdateError


def state_dir() -> Path:
    """The launcher's state folder: alfred.pid, alfred.log, update.log, update.json."""
    base = os.environ.get("XDG_STATE_HOME") or str(Path.home() / ".local" / "state")
    return Path(base) / "alfred"


def spawner(root: Path) -> Callable[[str], None]:
    script = root / "scripts" / "alfred-update.sh"

    def spawn(tag: str) -> None:
        try:
            subprocess.Popen(
                [str(script), tag],
                cwd=root,
                start_new_session=True,  # own process group: survives stopping Alfred
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        except OSError as e:
            raise UpdateError(f"Não consegui iniciar a atualização: {e}") from e

    return spawn
