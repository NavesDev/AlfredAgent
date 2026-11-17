"""ADR 0014: results recorded from a session's reply, shown on request, files under the guard."""

import sqlite3
from pathlib import Path

import pytest

from controllers.results import Results
from errors import FileGone, ResultNotFound, ResultNotReadable, SessionNotFound
from events import EventBus
from models import result, session
from models.db import open_db
from models.result import FileChange
from tests.conftest import drain


class FakeGit:
    def __init__(self) -> None:
        self.calls: list[tuple[Path, str]] = []
        self.fail = False

    async def head(self, path: Path) -> str | None:
        return "abc"

    async def numstat(self, path: Path, base: str) -> list[FileChange]:
        from errors import GitError

        self.calls.append((path, base))
        if self.fail:
            raise GitError("bad revision")
        return [FileChange(path="login.py", added=12, removed=3)]


class Env:
    def __init__(self, bus: EventBus, home: Path) -> None:
        self.db: sqlite3.Connection = open_db(":memory:")
        self.home, self.git = home, FakeGit()
        self.results = Results(self.db, bus, home, git=self.git)
        session.insert_session(self.db, "Design", "geral", aliases=["dizain"])
        self.queue = bus.subscribe()

    def file(self, rel: str, data: bytes = b"x") -> Path:
        path = self.home / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        return path

    def events(self) -> list[tuple[str, dict]]:  # type: ignore[type-arg]
        return [(e["type"], e) for e in drain(self.queue)]


@pytest.fixture
async def env(bus: EventBus, tmp_path: Path) -> Env:
    home = tmp_path / "home"
    home.mkdir()
    return Env(bus, home)


async def settle() -> None:
    import asyncio

    for _ in range(5):
        await asyncio.sleep(0)


# --- record (C3-C7) ---------------------------------------------------------------------------


async def test_apresentar_records_and_shows_a_card(env: Env) -> None:
    png = env.file("Imagens/retrato.png", b"12345")
    reply = f"RESUMO: Retrato pronto.\nAPRESENTAR: {png}"

    view = await env.results.record("Design", reply, env.home, None)
    await settle()

    assert view is not None
    assert (view.session, view.source, view.title, view.summary) == (
        "Design",
        "session",
        "Retrato pronto.",
        "Retrato pronto.",
    )
    [f] = view.files
    assert (f.name, f.kind, f.size, f.exists) == ("retrato.png", "image", 5, True)
    assert "home" not in view.model_dump_json()  # the path never leaves the server
    types = [t for t, _ in env.events()]
    assert types == ["result_created", "result_presented"]


async def test_presented_event_carries_mode_card(env: Env) -> None:
    png = env.file("a.png")
    await env.results.record("Design", f"APRESENTAR: {png}", env.home, None)
    await settle()
    [(_, created), (_, presented)] = env.events()
    assert presented["mode"] == "card"
    assert presented["result"]["id"] == created["result"]["id"]


async def test_guardar_records_without_showing(env: Env) -> None:
    view = await env.results.record("Design", "RESUMO: Feito.\nGUARDAR: relatório", None, None)
    await settle()
    assert view is not None and view.report == ""
    assert [t for t, _ in env.events()] == ["result_created"]


async def test_no_control_lines_records_nothing(env: Env) -> None:
    assert await env.results.record("Design", "RESUMO: Li.", env.home, "abc") is None
    await settle()
    assert env.events() == []
    assert env.results.list("Design") == []


async def test_report_has_text_and_numstat_since_the_start(env: Env) -> None:
    reply = "RESUMO: Corrigi o login.\nMudei a validação.\nAPRESENTAR: relatório"

    view = await env.results.record("Design", reply, env.home / "repo", "abc")

    assert view is not None
    assert view.report == "Mudei a validação."
    assert [(c.path, c.added, c.removed) for c in view.changes] == [("login.py", 12, 3)]
    assert env.git.calls == [(env.home / "repo", "abc")]


async def test_report_without_git_has_no_changes(env: Env) -> None:
    view = await env.results.record("Design", "RESUMO: ok\nAPRESENTAR: relatório", env.home, None)
    assert view is not None and view.changes == [] and env.git.calls == []


async def test_a_git_failure_keeps_the_report_without_changes(env: Env) -> None:
    env.git.fail = True
    view = await env.results.record("Design", "Feito.\nAPRESENTAR: relatório", env.home, "abc")
    assert view is not None and view.changes == [] and view.report == "Feito."


async def test_secret_or_outside_items_are_dropped_and_the_rest_stays(
    env: Env, caplog: pytest.LogCaptureFixture
) -> None:
    key = env.file(".ssh/id_rsa")
    ok = env.file("ok.png")
    reply = f"APRESENTAR: {key}; /etc/passwd; relativo.png; {env.home}/sumiu.png; {ok}"

    view = await env.results.record("Design", reply, None, None)

    assert view is not None and [f.name for f in view.files] == ["ok.png"]
    assert "id_rsa" in caplog.text and "/etc/passwd" in caplog.text


async def test_only_dropped_items_record_nothing(env: Env) -> None:
    assert await env.results.record("Design", "APRESENTAR: /etc/passwd", None, None) is None


async def test_title_falls_back_to_the_file_name(env: Env) -> None:
    gif = env.file("demo.gif")
    view = await env.results.record("Design", f"APRESENTAR: {gif}", None, None)
    assert view is not None and view.title == "demo.gif"


async def test_history_keeps_the_last_30(env: Env) -> None:
    for i in range(31):
        await env.results.record("Design", f"RESUMO: r{i}\nGUARDAR: relatório", None, None)

    views = env.results.list("Design")

    assert len(views) == 30 and views[0].summary == "r30" and views[-1].summary == "r1"


async def test_list_of_an_unknown_session_raises(env: Env) -> None:
    with pytest.raises(SessionNotFound):
        env.results.list("Nada")


# --- present and close (C13-C16) --------------------------------------------------------------


async def test_present_last_by_name_or_alias(env: Env) -> None:
    await env.results.record("Design", "RESUMO: um\nGUARDAR: relatório", None, None)
    await env.results.record("Design", "RESUMO: dois\nGUARDAR: relatório", None, None)
    await settle()
    env.events()

    view = env.results.present_last("dizain", "ampliado")
    await settle()

    assert view.summary == "dois"
    [(kind, event)] = env.events()
    assert (kind, event["mode"], event["result"]["id"]) == ("result_presented", "ampliado", view.id)


async def test_present_last_without_results_raises(env: Env) -> None:
    with pytest.raises(ResultNotFound, match="Design"):
        env.results.present_last("Design", "card")


async def test_present_path_records_an_alfred_result(env: Env) -> None:
    pdf = env.file("Documentos/x.pdf")

    view = env.results.present_paths(["~/Documentos/x.pdf".replace("~", str(env.home))], "card")
    await settle()

    assert (view.session, view.source, view.title) == ("alfred", "alfred", "x.pdf")
    assert view.files[0].kind == "pdf"
    assert [t for t, _ in env.events()] == ["result_created", "result_presented"]
    assert env.results.list("alfred")[0].id == view.id
    assert env.results.file(view.id, 0) == pdf


async def test_present_paths_shows_several_files_as_one_result(env: Env) -> None:
    pdf = env.file("Documentos/x.pdf")
    png = env.file("Imagens/y.png")

    view = env.results.present_paths([str(pdf), str(png), str(pdf)], "ampliado")
    await settle()

    assert view.title == "2 arquivos"
    assert [f.name for f in view.files] == ["x.pdf", "y.png"]
    assert env.results.file(view.id, 1) == png


async def test_present_paths_refuses_the_set_when_one_file_is_secret(env: Env) -> None:
    pdf = env.file("Documentos/x.pdf")
    env.file(".env")
    with pytest.raises(ResultNotReadable, match=r"\.env"):
        env.results.present_paths([str(pdf), str(env.home / ".env")], "card")
    await settle()
    assert env.events() == []


@pytest.mark.parametrize("raw", ["/etc/passwd", "{home}/.env", "{home}/nada.pdf", "rel.pdf"])
async def test_present_path_refuses_what_alfred_cannot_read(env: Env, raw: str) -> None:
    env.file(".env")
    with pytest.raises(ResultNotReadable):
        env.results.present_paths([raw.format(home=env.home)], "card")
    await settle()
    assert env.events() == []


async def test_present_by_id_and_close(env: Env) -> None:
    view = await env.results.record("Design", "GUARDAR: relatório", None, None)
    assert view is not None
    await settle()
    env.events()

    env.results.present(view.id, "card")
    env.results.close()
    await settle()

    assert [t for t, _ in env.events()] == ["result_presented", "presentation_closed"]
    with pytest.raises(ResultNotFound):
        env.results.present(999, "card")


# --- serve a file (C18, RNF-01) --------------------------------------------------------------


async def test_file_is_guarded_again_when_served(env: Env) -> None:
    png = env.file("a.png")
    view = await env.results.record("Design", f"APRESENTAR: {png}", None, None)
    assert view is not None
    assert env.results.file(view.id, 0) == png

    png.unlink()
    with pytest.raises(FileGone):
        env.results.file(view.id, 0)
    assert env.results.get(view.id).files[0].exists is False

    png.parent.joinpath("a.png").symlink_to(env.file(".ssh/id_rsa"))
    with pytest.raises(ResultNotReadable):
        env.results.file(view.id, 0)

    with pytest.raises(ResultNotFound):
        env.results.file(view.id, 1)
    with pytest.raises(ResultNotFound):
        env.results.file(999, 0)


async def test_results_of_a_deleted_session_go_with_it(env: Env) -> None:
    await env.results.record("Design", "GUARDAR: relatório", None, None)
    session.delete_session(env.db, "Design")
    assert env.db.execute("SELECT COUNT(*) FROM result").fetchone()[0] == 0
    assert result.list_results(env.db, None) == []


async def test_open_goes_through_the_guard(env: Env) -> None:
    opened: list[tuple[Path, bool]] = []

    async def fake_open(path: Path, reveal: bool) -> None:
        opened.append((path, reveal))

    env.results._open = fake_open
    png = env.file("a.png")
    view = await env.results.record("Design", f"APRESENTAR: {png}", None, None)
    assert view is not None

    await env.results.open(view.id, 0, reveal=True)
    assert opened == [(png, True)]

    png.unlink()
    with pytest.raises(FileGone):
        await env.results.open(view.id, 0, reveal=False)
    assert len(opened) == 1


async def test_an_open_failure_becomes_a_result_error(env: Env) -> None:
    from errors import OpenerError, ResultError

    async def broken(path: Path, reveal: bool) -> None:
        raise OpenerError("xdg-open: no app")

    env.results._open = broken
    png = env.file("a.png")
    view = await env.results.record("Design", f"APRESENTAR: {png}", None, None)
    assert view is not None
    with pytest.raises(ResultError, match="Não consegui abrir"):
        await env.results.open(view.id, 0, reveal=False)
