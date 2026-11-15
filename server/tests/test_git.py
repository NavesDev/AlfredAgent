import asyncio
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


def run(repo: Path, *args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=repo, capture_output=True, text=True, check=True
    ).stdout


async def test_add_worktree_takes_a_branch_apart_from_the_folder_name(repo: Path) -> None:
    path, branch = await git.add_worktree(repo, "cancel", "feat/cancel")

    assert path == repo.parent / "api-wt" / "cancel"
    assert branch == "feat/cancel"
    assert run(path, "branch", "--show-current").strip() == "feat/cancel"


async def test_summary_tells_branch_changes_and_last_commits(repo: Path) -> None:
    (repo / "a.txt").write_text("a")
    run(repo, "add", "a.txt")
    run(repo, "commit", "-q", "-m", "add a")
    (repo / "a.txt").write_text("changed")
    (repo / "b.txt").write_text("new")

    summary = await git.summary(repo)

    assert summary.branch == "main"
    assert summary.changed == 2
    assert [c.split(" ", 1)[1] for c in summary.commits] == ["add a", "init"]
    assert summary.branches == ["main"]
    run(repo, "branch", "fix/1-a")
    assert set((await git.summary(repo)).branches) == {"main", "fix/1-a"}


async def test_summary_outside_a_repo_raises(tmp_path: Path) -> None:
    with pytest.raises(GitError):
        await git.summary(tmp_path)


async def test_list_worktrees_and_common_dir(repo: Path) -> None:
    assert await git.list_worktrees(repo) == []
    path, _ = await git.add_worktree(repo, "cancel", "feat/cancel")
    run(repo, "worktree", "add", "-q", "--detach", str(repo.parent / "loose"))

    listed = await git.list_worktrees(repo)

    assert listed == [(path, "feat/cancel"), (repo.parent / "loose", None)]
    assert await git.common_dir(path) == await git.common_dir(repo) == repo / ".git"


async def test_watch_worktrees_yields_the_repo_on_add_and_remove(repo: Path) -> None:
    common = repo / ".git"
    (common / "worktrees").mkdir()
    stop = asyncio.Event()
    seen: list[Path] = []

    async def collect() -> None:
        async for changed in git.watch_worktrees([common], stop):
            seen.append(changed)
            stop.set()

    task = asyncio.create_task(collect())
    await asyncio.sleep(0.3)
    await git.add_worktree(repo, "cancel", "feat/cancel")
    await asyncio.wait_for(task, 10)

    assert seen == [common]


async def test_watch_worktrees_ignores_other_git_activity(repo: Path) -> None:
    common = repo / ".git"
    stop = asyncio.Event()
    seen: list[Path] = []

    async def collect() -> None:
        async for changed in git.watch_worktrees([common], stop):
            seen.append(changed)

    task = asyncio.create_task(collect())
    await asyncio.sleep(0.3)
    run(repo, "commit", "-q", "--allow-empty", "-m", "noise")
    await asyncio.sleep(1.5)
    stop.set()
    await asyncio.wait_for(task, 5)

    assert seen == []


@pytest.fixture
def cloned(repo: Path, tmp_path: Path) -> Path:
    """A clone of `repo` (its origin), which has tags v0.1.0 and v0.2.0 and a CHANGELOG."""
    for tag, text in (("v0.1.0", "# Changelog\n\n## [0.1.0] (x)\n\nOne\n"), ("v0.2.0", "two")):
        (repo / "CHANGELOG.md").write_text(text)
        subprocess.run(["git", "add", "."], cwd=repo, check=True)
        subprocess.run(["git", "commit", "-q", "-m", tag], cwd=repo, check=True)
        subprocess.run(["git", "tag", tag], cwd=repo, check=True)
    clone = tmp_path / "clone"
    subprocess.run(["git", "clone", "-q", str(repo), str(clone)], check=True)
    subprocess.run(["git", "tag", "-d", "v0.2.0"], cwd=clone, check=True, capture_output=True)
    return clone


async def test_local_and_remote_tags(cloned: Path) -> None:
    assert await git.local_tags(cloned) == ["v0.1.0"]
    assert sorted(await git.remote_tags(cloned)) == ["v0.1.0", "v0.2.0"]


async def test_fetch_tag_then_show_a_file_at_it(cloned: Path) -> None:
    await git.fetch_tag(cloned, "v0.2.0")

    assert await git.show(cloned, "v0.2.0", "CHANGELOG.md") == "two"
    assert await git.local_tags(cloned) == ["v0.1.0", "v0.2.0"]


async def test_current_branch(cloned: Path) -> None:
    assert await git.current_branch(cloned) == "main"
