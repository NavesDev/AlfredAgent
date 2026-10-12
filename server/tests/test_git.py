import subprocess
from pathlib import Path

import pytest

from errors import GitError
from infra import git


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    path = tmp_path / "api"
    path.mkdir()
    for args in (
        ["init", "-q", "-b", "main"],
        ["config", "user.email", "t@t"],
        ["config", "user.name", "t"],
        ["commit", "-q", "--allow-empty", "-m", "init"],
    ):
        subprocess.run(["git", *args], cwd=path, check=True)
    return path


async def test_add_worktree_creates_a_new_branch_next_to_the_repo(repo: Path) -> None:
    path, branch = await git.add_worktree(repo, "cancel")

    assert path == repo.parent / "api-wt" / "cancel"
    assert branch == "cancel"
    assert (path / ".git").exists()
    assert (
        "cancel"
        in subprocess.run(
            ["git", "branch"], cwd=repo, capture_output=True, text=True, check=True
        ).stdout
    )


async def test_add_worktree_reuses_an_existing_branch(repo: Path) -> None:
    subprocess.run(["git", "branch", "refund"], cwd=repo, check=True)

    path, branch = await git.add_worktree(repo, "refund")

    assert path.is_dir() and branch == "refund"


async def test_add_worktree_outside_a_repo_raises(tmp_path: Path) -> None:
    with pytest.raises(GitError, match="not a git repository"):
        await git.add_worktree(tmp_path, "x")


async def test_dirty_and_remove(repo: Path) -> None:
    path, _ = await git.add_worktree(repo, "cancel")
    assert not await git.is_dirty(path)

    (path / "new.txt").write_text("x")
    assert await git.is_dirty(path)
    with pytest.raises(GitError):
        await git.remove_worktree(path, force=False)

    await git.remove_worktree(path, force=True)
    assert not path.exists()
