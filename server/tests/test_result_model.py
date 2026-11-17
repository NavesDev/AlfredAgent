import sqlite3

import pytest

from models import result, session
from models.db import SCHEMA_VERSION, open_db
from models.result import FileChange


@pytest.fixture
def db() -> sqlite3.Connection:
    return open_db(":memory:")


def test_schema_is_version_5_with_the_result_table(db: sqlite3.Connection) -> None:
    assert SCHEMA_VERSION == 5
    columns = {r["name"] for r in db.execute("PRAGMA table_info(result)")}
    assert columns == {
        "id",
        "session_id",
        "source",
        "title",
        "summary",
        "report",
        "changes",
        "files",
        "created_at",
    }


def test_insert_and_read_back(db: sqlite3.Connection) -> None:
    s = session.insert_session(db, "Design", "geral")
    record = result.insert_result(
        db,
        s.id,
        "session",
        "Retrato pronto",
        summary="Retrato pronto.",
        report="Mudei **x**.",
        changes=[FileChange(path="a.py", added=3, removed=1)],
        files=["/home/u/a.png"],
    )

    loaded = result.get_result(db, record.id)
    assert loaded == record
    assert loaded.session_id == s.id and loaded.changes[0].added == 3
    assert loaded.created_at > 0


def test_alfred_results_have_no_session(db: sqlite3.Connection) -> None:
    record = result.insert_result(db, None, "alfred", "x.pdf", files=["/home/u/x.pdf"])
    assert result.list_results(db, None) == [record]


def test_list_is_newest_first_and_prune_keeps_the_last(db: sqlite3.Connection) -> None:
    s = session.insert_session(db, "Design", "geral")
    ids = [result.insert_result(db, s.id, "session", f"r{i}").id for i in range(5)]

    result.prune(db, s.id, keep=3)

    assert [r.id for r in result.list_results(db, s.id)] == ids[:1:-1]
    assert [r.id for r in result.list_results(db, s.id, limit=2)] == ids[:2:-1]


def test_unknown_source_is_refused(db: sqlite3.Connection) -> None:
    with pytest.raises(sqlite3.IntegrityError):
        result.insert_result(db, None, "web", "x")  # type: ignore[arg-type]


def test_deleting_a_session_deletes_its_results(db: sqlite3.Connection) -> None:
    s = session.insert_session(db, "Design", "geral")
    result.insert_result(db, s.id, "session", "r")
    session.delete_session(db, "Design")
    assert db.execute("SELECT COUNT(*) FROM result").fetchone()[0] == 0


@pytest.mark.parametrize(
    ("name", "kind"),
    [
        ("a.PNG", "image"),
        ("b.gif", "image"),
        ("c.svg", "image"),
        ("d.mp4", "video"),
        ("e.webm", "video"),
        ("f.pdf", "pdf"),
        ("g.md", "markdown"),
        ("h.log", "text"),
        ("i.py", "text"),
        ("j.json", "text"),
        ("k.html", "html"),
        ("l.zip", "other"),
        ("Makefile", "other"),
    ],
)
def test_kind_from_the_extension(name: str, kind: str) -> None:
    assert result.kind_of(name) == kind
