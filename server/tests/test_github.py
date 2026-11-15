"""GitHub issues read through gh with fixed, read-only arguments (ADR 0011)."""

import json
from pathlib import Path

import pytest

from errors import GitHubError
from infra import github


class Recorder:
    def __init__(self, out: object = None, fail: str | None = None) -> None:
        self.out, self.fail = out, fail
        self.calls: list[tuple[Path, tuple[str, ...]]] = []

    async def __call__(self, cwd: Path, *args: str) -> str:
        self.calls.append((cwd, args))
        if self.fail:
            raise GitHubError(self.fail)
        return json.dumps(self.out)


async def test_issue_reads_one_issue_with_fixed_args(tmp_path: Path) -> None:
    run = Recorder(
        {
            "number": 12,
            "title": "Login quebra",
            "state": "OPEN",
            "labels": [{"name": "bug"}],
            "body": "x" * 5000,
            "url": "https://github.com/o/r/issues/12",
            "comments": [{"author": {"login": f"u{i}"}, "body": f"c{i}"} for i in range(8)],
        }
    )

    issue = await github.issue(tmp_path, 12, run=run)

    assert run.calls == [
        (
            tmp_path,
            ("issue", "view", "12", "--json", "number,title,state,labels,body,url,comments"),
        )
    ]
    assert (issue.number, issue.title, issue.labels) == (12, "Login quebra", ["bug"])
    assert len(issue.body) == 4000
    assert issue.comments == [f"u{i}: c{i}" for i in range(3, 8)]


async def test_issues_lists_with_search_as_one_value(tmp_path: Path) -> None:
    run = Recorder([{"number": 3, "title": "Doc", "labels": []}])

    found = await github.issues(tmp_path, "--repo evil", "all", run=run)

    assert run.calls[0][1] == (
        "issue",
        "list",
        "--state",
        "all",
        "--limit",
        "20",
        "--json",
        "number,title,labels",
        "--search=--repo evil",
    )
    assert [(i.number, i.title) for i in found] == [(3, "Doc")]


@pytest.mark.parametrize("state", ["merged", "--x", ""])
async def test_issues_refuses_an_unknown_state(tmp_path: Path, state: str) -> None:
    run = Recorder([])
    with pytest.raises(GitHubError):
        await github.issues(tmp_path, None, state, run=run)
    assert run.calls == []


async def test_gh_errors_surface_as_github_errors(tmp_path: Path) -> None:
    with pytest.raises(GitHubError, match="no git remotes"):
        await github.issue(tmp_path, 1, run=Recorder(fail="no git remotes found"))


async def test_real_gh_runs_without_a_shell(tmp_path: Path) -> None:
    with pytest.raises(GitHubError):
        await github.issue(tmp_path, 1)  # not a repo: gh fails, nothing else runs
