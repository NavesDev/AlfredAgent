import asyncio
import sqlite3

import pytest

from controllers.vocabulary import Vocabulary
from events import EventBus
from models import project, session
from models.db import open_db
from models.vocabulary import Term, canonicalize, hint, whisper_words

TERMS = [
    Term("Site Sales", ("saite seils", "vendas")),
    Term("Developer", ("dev",)),
    Term("Recurve", ()),
]


@pytest.mark.parametrize(
    ("spoken", "expected"),
    [
        ("manda pro saite seils rodar os testes", "manda pro Site Sales rodar os testes"),
        ("Saite  Seils, roda os testes", "Site Sales, roda os testes"),
        ("pede pro DEV revisar", "pede pro Developer revisar"),
        ("o devedor pagou", "o devedor pagou"),  # only whole words
        ("nada aqui", "nada aqui"),
    ],
)
def test_canonicalize_swaps_aliases_for_the_real_name(spoken: str, expected: str) -> None:
    assert canonicalize(spoken, TERMS) == expected


def test_canonicalize_ignores_accents() -> None:
    assert canonicalize("roda no recúrve", [Term("Recurve", ("recurve",))]) == "roda no Recurve"


def test_whisper_words_and_hint_list_each_name_once() -> None:
    terms = [*TERMS, Term("recurve", ())]

    assert whisper_words(terms) == "Site Sales, Developer, Recurve"
    assert hint(terms) == "[Nomes conhecidos: Site Sales, Developer, Recurve]"
    assert hint([]) == ""


@pytest.fixture
def db() -> sqlite3.Connection:
    return open_db(":memory:")


async def test_vocabulary_reads_sessions_and_projects(
    bus: EventBus, db: sqlite3.Connection
) -> None:
    session.insert_session(db, "Site Sales", "geral", aliases=["saite seils"])
    project.insert_project(db, "Vrummy", ["vrumi"])

    vocabulary = Vocabulary(db, bus)

    assert vocabulary.whisper_words == "Site Sales, Vrummy"
    assert vocabulary.canonicalize("o vrumi e o saite seils") == "o Vrummy e o Site Sales"
    assert vocabulary.hint() == "[Nomes conhecidos: Site Sales, Vrummy]"


async def test_vocabulary_refreshes_when_names_change(
    bus: EventBus, db: sqlite3.Connection
) -> None:
    vocabulary = Vocabulary(db, bus)
    job = asyncio.create_task(vocabulary.run())
    await asyncio.sleep(0)

    session.insert_session(db, "Design", "geral")
    bus.publish("session_created", session={})
    for _ in range(5):
        await asyncio.sleep(0)
    job.cancel()

    assert vocabulary.whisper_words == "Design"
