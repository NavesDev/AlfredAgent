import asyncio
from collections.abc import AsyncIterator, Iterable
from pathlib import Path

import pytest

from controllers.projects import Projects
from errors import GitError, NoDefaultWorkspace, ProjectError, ProjectInUse, ProjectNotFound
from events import EventBus
from infra.git import GitSummary
from models import session as records
from tests.conftest import drain
from tests.test_sessions import Env, settle


class FakeGit:
    def __init__(self, dirty: bool = False, fail: bool = False) -> None:
        self.dirty, self.fail = dirty, fail
        self.removed: list[tuple[Path, bool]] = []
        self.added: list[tuple[Path, str, str]] = []
        self.trees: dict[Path, list[tuple[Path, str | None]]] = {}  # repo -> its worktrees
        self.commons: dict[Path, Path] = {}  # folder -> common dir, when not <folder>/.git
        self.broken: set[Path] = set()

    async def add_worktree(
        self, parent: Path, name: str, branch: str | None = None
    ) -> tuple[Path, str]:
        if self.fail:
            raise GitError("fatal: not a git repository")
        path = parent.parent / f"{parent.name}-wt" / name
        path.mkdir(parents=True)
        self.added.append((parent, name, branch or name))
        return path, branch or name

    async def remove_worktree(self, path: Path, force: bool) -> None:
        self.removed.append((path, force))

    async def is_dirty(self, path: Path) -> bool:
        return self.dirty

    async def common_dir(self, path: Path) -> Path:
        if not path.is_dir() or path in self.broken:
            raise GitError("fatal: not a git repository")
        return self.commons.get(path, path / ".git")

    async def list_worktrees(self, repo: Path) -> list[tuple[Path, str | None]]:
        return list(self.trees.get(repo, []))

    async def summary(self, path: Path) -> GitSummary:
        if self.fail:
            raise GitError("fatal: not a git repository")
        return GitSummary("main", 2 if self.dirty else 0, ["a1b2c3d add login", "9f8e7d6 init"])


def make(env: Env, git: FakeGit | None = None, mode: str = "worktree") -> Projects:
    return Projects(
        env.db,
        env.sessions._bus,
        git or FakeGit(),
        mode=lambda: mode,  # type: ignore[arg-type,return-value]
        drop_session=env.sessions.delete,
    )


@pytest.fixture
async def env(bus: EventBus, tmp_path: Path) -> Env:
    return Env(bus, tmp_path)


async def test_create_and_list_projects(env: Env) -> None:
    queue = env.sessions._bus.subscribe()
    projects = make(env)

    created = projects.create("Recurve", ["billing", " "])
    await settle()

    assert (created.name, created.aliases) == ("Recurve", ["billing"])
    assert [p.name for p in projects.all()] == ["Recurve"]
    assert drain(queue)[-1]["type"] == "project_created"


@pytest.mark.parametrize("name", [" ", "recurve"])
async def test_create_rejects_empty_or_taken_names(env: Env, name: str) -> None:
    projects = make(env)
    projects.create("Recurve", [])

    with pytest.raises(ProjectError):
        projects.create(name, [])


async def test_find_by_name_or_alias(env: Env) -> None:
    projects = make(env)
    p = projects.create("Recurve", ["billing"])

    assert projects.find("BILLING").id == p.id
    with pytest.raises(ProjectNotFound, match="outro"):
        projects.find("outro")


async def test_update_renames_and_publishes(env: Env) -> None:
    queue = env.sessions._bus.subscribe()
    projects = make(env)
    p = projects.create("Recurve", [])

    updated = projects.update(p.id, name="Recurve 2", aliases=["r2"])
    await settle()

    assert (updated.name, updated.aliases) == ("Recurve 2", ["r2"])
    assert drain(queue)[-1]["type"] == "project_updated"


async def test_add_folder_workspace(env: Env, tmp_path: Path) -> None:
    projects = make(env)
    p = projects.create("Recurve", [])
    (tmp_path / "api").mkdir()

    ws = projects.add_workspace(p.id, "back", str(tmp_path / "api"))

    assert (ws.kind, ws.path, ws.branch) == ("folder", str(tmp_path / "api"), None)
    assert [w.name for w in projects.get(p.id).workspaces] == ["back"]


@pytest.mark.parametrize(("name", "folder"), [(" ", "api"), ("back", "missing"), ("BACK", "api")])
async def test_add_workspace_rejects_bad_requests(
    env: Env, tmp_path: Path, name: str, folder: str
) -> None:
    projects = make(env)
    p = projects.create("Recurve", [])
    (tmp_path / "api").mkdir()
    projects.add_workspace(p.id, "back", str(tmp_path / "api"))

    with pytest.raises(ProjectError):
        projects.add_workspace(p.id, name, str(tmp_path / folder))


async def test_add_worktree_from_a_parent_workspace(env: Env, tmp_path: Path) -> None:
    projects = make(env)
    p = projects.create("Recurve", [])
    (tmp_path / "api").mkdir()
    back = projects.add_workspace(p.id, "back", str(tmp_path / "api"))

    wt = await projects.add_worktree(p.id, back.id, "cancel")

    assert (wt.kind, wt.parent_id, wt.branch) == ("worktree", back.id, "cancel")
    assert wt.path == str(tmp_path / "api-wt" / "cancel")


async def test_failed_worktree_is_not_registered(env: Env, tmp_path: Path) -> None:
    projects = make(env, FakeGit(fail=True))
    p = projects.create("Recurve", [])
    (tmp_path / "api").mkdir()
    back = projects.add_workspace(p.id, "back", str(tmp_path / "api"))

    with pytest.raises(GitError):
        await projects.add_worktree(p.id, back.id, "cancel")
    assert [w.name for w in projects.get(p.id).workspaces] == ["back"]


async def test_delete_folder_workspace_keeps_the_folder(env: Env, tmp_path: Path) -> None:
    git = FakeGit()
    projects = make(env, git)
    p = projects.create("Recurve", [])
    (tmp_path / "api").mkdir()
    back = projects.add_workspace(p.id, "back", str(tmp_path / "api"))

    await projects.delete_workspace(back.id)

    assert projects.get(p.id).workspaces == [] and (tmp_path / "api").is_dir()
    assert git.removed == []


async def test_delete_worktree_refuses_when_dirty_unless_forced(env: Env, tmp_path: Path) -> None:
    git = FakeGit(dirty=True)
    projects = make(env, git)
    p = projects.create("Recurve", [])
    (tmp_path / "api").mkdir()
    back = projects.add_workspace(p.id, "back", str(tmp_path / "api"))
    wt = await projects.add_worktree(p.id, back.id, "cancel")

    with pytest.raises(ProjectInUse, match="não commitadas"):
        await projects.delete_workspace(wt.id)
    await projects.delete_workspace(wt.id, force=True)

    assert git.removed == [(Path(wt.path), True)]
    assert [w.name for w in projects.get(p.id).workspaces] == ["back"]


async def test_cannot_delete_what_is_in_use(env: Env, tmp_path: Path) -> None:
    projects = make(env)
    p = projects.create("Recurve", [])
    (tmp_path / "api").mkdir()
    back = projects.add_workspace(p.id, "back", str(tmp_path / "api"))
    records.insert_session(env.db, "back", "implementacao", workspace_id=back.id)

    with pytest.raises(ProjectInUse, match="back"):
        await projects.delete_workspace(back.id)
    with pytest.raises(ProjectInUse):
        projects.delete(p.id)

    records.delete_session(env.db, "back")
    await projects.delete_workspace(back.id)
    projects.delete(p.id)
    assert projects.all() == []


async def test_worktree_of_a_worktree_blocks_deleting_the_parent(env: Env, tmp_path: Path) -> None:
    projects = make(env)
    p = projects.create("Recurve", [])
    (tmp_path / "api").mkdir()
    back = projects.add_workspace(p.id, "back", str(tmp_path / "api"))
    await projects.add_worktree(p.id, back.id, "cancel")

    with pytest.raises(ProjectInUse, match="cancel"):
        await projects.delete_workspace(back.id)


async def test_projects_and_workspaces_carry_a_short_description(env: Env, tmp_path: Path) -> None:
    (tmp_path / "api").mkdir()
    projects = make(env)

    p = projects.create("Recurve", [], "  Cobrança recorrente ")
    ws = projects.add_workspace(p.id, "back", str(tmp_path / "api"), "API")
    wt = await projects.add_worktree(p.id, ws.id, "cancel", "Fluxo de cancelamento")
    changed = projects.update_workspace(ws.id, description="API em Spring")
    renamed = projects.update(p.id, description="")

    assert p.description == "Cobrança recorrente"
    assert wt.description == "Fluxo de cancelamento"
    assert changed.description == "API em Spring"
    assert renamed.description == ""
    assert [w.description for w in projects.get(p.id).workspaces] == [
        "API em Spring",
        "Fluxo de cancelamento",
    ]


async def test_descriptions_longer_than_200_chars_are_refused(env: Env, tmp_path: Path) -> None:
    (tmp_path / "api").mkdir()
    projects = make(env)
    p = projects.create("Recurve", [])
    ws = projects.add_workspace(p.id, "back", str(tmp_path / "api"))

    with pytest.raises(ProjectError, match="200"):
        projects.create("Vrummy", [], "x" * 201)
    with pytest.raises(ProjectError, match="200"):
        projects.update_workspace(ws.id, description="x" * 201)
    with pytest.raises(ProjectNotFound):
        projects.update_workspace(99, description="nada")


def folders(tmp_path: Path, *names: str) -> list[str]:
    for name in names:
        (tmp_path / name).mkdir()
    return [str(tmp_path / name) for name in names]


async def test_the_first_folder_becomes_the_default_workspace(env: Env, tmp_path: Path) -> None:
    projects = make(env)
    back, front = folders(tmp_path, "back", "front")
    recurve = projects.create("Recurve", [])

    first = projects.add_workspace(recurve.id, "back", back)
    second = projects.add_workspace(recurve.id, "front", front)

    assert projects.get(recurve.id).default_workspace_id == first.id
    queue = env.sessions._bus.subscribe()
    projects.update(recurve.id, default_workspace_id=second.id)
    await settle()
    assert projects.get(recurve.id).default_workspace_id == second.id
    assert drain(queue)[-1]["type"] == "project_updated"


async def test_default_workspace_must_belong_to_the_project(env: Env, tmp_path: Path) -> None:
    projects = make(env)
    (back,) = folders(tmp_path, "back")
    recurve, other = projects.create("Recurve", []), projects.create("Other", [])
    ws = projects.add_workspace(other.id, "back", back)

    with pytest.raises(ProjectNotFound):
        projects.update(recurve.id, default_workspace_id=ws.id)


async def test_deleting_the_default_workspace_clears_it(env: Env, tmp_path: Path) -> None:
    projects = make(env)
    (back,) = folders(tmp_path, "back")
    recurve = projects.create("Recurve", [])
    ws = projects.add_workspace(recurve.id, "back", back)

    await projects.delete_workspace(ws.id)

    assert projects.get(recurve.id).default_workspace_id is None


async def test_mode_per_workspace_with_a_global_default(env: Env, tmp_path: Path) -> None:
    projects = make(env, mode="worktree")
    back, front = folders(tmp_path, "back", "front")
    recurve = projects.create("Recurve", [])
    plain = projects.add_workspace(recurve.id, "back", back)
    own = projects.add_workspace(recurve.id, "front", front)

    own = projects.update_workspace(own.id, implementation_mode="ambiente")
    assert projects.mode_of(plain) == "worktree"
    assert projects.mode_of(own) == "ambiente"
    own = projects.update_workspace(own.id, implementation_mode=None)
    assert projects.mode_of(own) == "worktree"
    tree = await projects.add_worktree(recurve.id, plain.id, "x")
    assert projects.mode_of(tree) == "ambiente"  # a worktree never nests another


async def test_start_feature_in_worktree_mode_opens_a_worktree(env: Env, tmp_path: Path) -> None:
    git = FakeGit()
    projects = make(env, git)
    (back,) = folders(tmp_path, "back")
    recurve = projects.create("Recurve", [])
    projects.add_workspace(recurve.id, "back", back)

    ws = await projects.start_feature("Recurve", "Cancelamento de Pedido")

    assert (ws.kind, ws.name, ws.branch) == (
        "worktree",
        "cancelamento-de-pedido",
        "feat/cancelamento-de-pedido",
    )
    assert git.added == [(Path(back), "cancelamento-de-pedido", "feat/cancelamento-de-pedido")]
    assert await projects.start_feature("Recurve", "cancelamento de pedido") == ws  # reused
    assert len(git.added) == 1


async def test_start_feature_in_workspace_mode_uses_the_workspace(env: Env, tmp_path: Path) -> None:
    git = FakeGit()
    projects = make(env, git, mode="ambiente")
    back, front = folders(tmp_path, "back", "front")
    recurve = projects.create("Recurve", [])
    projects.add_workspace(recurve.id, "back", back)
    projects.add_workspace(recurve.id, "front", front)

    ws = await projects.start_feature("Recurve", "login", workspace="front")

    assert ws.name == "front" and git.added == []


async def test_start_feature_without_a_default_refuses(env: Env) -> None:
    projects = make(env)
    projects.create("Recurve", [])

    with pytest.raises(NoDefaultWorkspace):
        await projects.start_feature("Recurve", "login")


async def test_sync_registers_worktrees_made_outside_and_drops_vanished_ones(
    env: Env, tmp_path: Path
) -> None:
    git = FakeGit()
    projects = make(env, git)
    (back,) = folders(tmp_path, "back")
    recurve = projects.create("Recurve", [])
    parent = projects.add_workspace(recurve.id, "back", back)
    gone = await projects.add_worktree(recurve.id, parent.id, "old")
    env.sessions.create("implementacao", "velha", gone.id)
    outside = tmp_path / "back-wt" / "login"
    outside.mkdir(parents=True)
    git.trees[Path(back)] = [(outside, "feat/login"), (tmp_path / "loose", None)]
    queue = env.sessions._bus.subscribe()

    added, removed = await projects.sync_worktrees()
    await settle()

    assert [(w.name, w.kind, w.parent_id, w.branch) for w in added] == [
        ("login", "worktree", parent.id, "feat/login"),
        ("loose", "worktree", parent.id, None),
    ]
    assert [w.name for w in removed] == ["old"]
    assert "velha" not in {v.name for v in env.sessions.list()}
    assert {w.name for w in projects.get(recurve.id).workspaces} == {"back", "login", "loose"}
    assert "project_updated" in {e["type"] for e in drain(queue)}
    assert await projects.sync_worktrees() == ([], [])  # idempotent


async def test_sync_of_one_repo_leaves_the_others(env: Env, tmp_path: Path) -> None:
    git = FakeGit()
    projects = make(env, git)
    back, front = folders(tmp_path, "back", "front")
    recurve = projects.create("Recurve", [])
    projects.add_workspace(recurve.id, "back", back)
    projects.add_workspace(recurve.id, "front", front)
    for repo, name in ((back, "a"), (front, "b")):
        (tmp_path / name).mkdir()
        git.trees[Path(repo)] = [(tmp_path / name, name)]

    added, _ = await projects.sync_worktrees(Path(front) / ".git")

    assert [w.name for w in added] == ["b"]


async def test_sync_skips_broken_repos_and_missing_folders(env: Env, tmp_path: Path) -> None:
    git = FakeGit()
    projects = make(env, git)
    back, front = folders(tmp_path, "back", "front")
    recurve = projects.create("Recurve", [])
    parent = projects.add_workspace(recurve.id, "back", back)
    projects.add_workspace(recurve.id, "front", front)
    kept = await projects.add_worktree(recurve.id, parent.id, "kept")
    git.broken.add(Path(back))  # git fails there: nothing of it is touched
    (tmp_path / "x").mkdir()
    git.trees[Path(front)] = [(tmp_path / "x", "x")]

    added, removed = await projects.sync_worktrees()

    assert [w.name for w in added] == ["x"] and removed == []
    assert kept.id in {w.id for w in projects.get(recurve.id).workspaces}


async def test_two_folders_of_one_repo_share_it(env: Env, tmp_path: Path) -> None:
    git = FakeGit()
    projects = make(env, git)
    back, mirror = folders(tmp_path, "back", "mirror")
    git.commons[Path(mirror)] = Path(back) / ".git"
    recurve = projects.create("Recurve", [])
    projects.add_workspace(recurve.id, "back", back)
    projects.add_workspace(recurve.id, "mirror", mirror)
    (tmp_path / "t").mkdir()
    git.trees[Path(back)] = git.trees[Path(mirror)] = [(tmp_path / "t", "t")]

    added, _ = await projects.sync_worktrees()

    assert [w.name for w in added] == ["t"]
    assert await projects.repos() == [Path(back) / ".git"]


async def test_watch_syncs_at_start_and_on_each_event(env: Env, tmp_path: Path) -> None:
    git = FakeGit()
    events: asyncio.Queue[Path] = asyncio.Queue()
    watched: list[list[Path]] = []

    async def watch(repos: Iterable[Path], stop: asyncio.Event) -> AsyncIterator[Path]:
        watched.append(list(repos))
        while not stop.is_set():
            yield await events.get()

    projects = Projects(env.db, env.sessions._bus, git, watch=watch)
    (back,) = folders(tmp_path, "back")
    recurve = projects.create("Recurve", [])
    projects.add_workspace(recurve.id, "back", back)
    (tmp_path / "early").mkdir()
    git.trees[Path(back)] = [(tmp_path / "early", "early")]  # made while Alfred was off

    task = asyncio.create_task(projects.watch_worktrees())
    await settle()
    assert "early" in {w.name for w in projects.get(recurve.id).workspaces}

    (tmp_path / "late").mkdir()
    git.trees[Path(back)].append((tmp_path / "late", "late"))
    await events.put(Path(back) / ".git")
    await settle()
    task.cancel()

    assert "late" in {w.name for w in projects.get(recurve.id).workspaces}
    assert watched == [[Path(back) / ".git"]]  # one watch, no polling
