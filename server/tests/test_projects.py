from pathlib import Path

import pytest

from controllers.projects import Projects
from errors import GitError, ProjectError, ProjectInUse, ProjectNotFound
from events import EventBus
from models import session as records
from tests.conftest import drain
from tests.test_sessions import Env, settle


class FakeGit:
    def __init__(self, dirty: bool = False, fail: bool = False) -> None:
        self.dirty, self.fail = dirty, fail
        self.removed: list[tuple[Path, bool]] = []

    async def add_worktree(self, parent: Path, name: str) -> tuple[Path, str]:
        if self.fail:
            raise GitError("fatal: not a git repository")
        path = parent.parent / f"{parent.name}-wt" / name
        path.mkdir(parents=True)
        return path, name

    async def remove_worktree(self, path: Path, force: bool) -> None:
        self.removed.append((path, force))

    async def is_dirty(self, path: Path) -> bool:
        return self.dirty


def make(env: Env, git: FakeGit | None = None) -> Projects:
    return Projects(env.db, env.sessions._bus, git or FakeGit())


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
