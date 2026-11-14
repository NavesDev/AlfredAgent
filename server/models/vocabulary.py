"""Names the user says out loud (sessions, projects) and the spoken aliases that stand for them.

Whisper runs in Portuguese, so English names come out spelled the Portuguese way ("saite
seils"). These helpers feed the names to Whisper and swap known aliases for the real name.
"""

import re
import unicodedata
from collections.abc import Iterable
from dataclasses import dataclass


@dataclass(frozen=True)
class Term:
    name: str
    aliases: tuple[str, ...]


def _fold(text: str) -> str:
    """Lowercase without accents, one char per char so match positions stay valid."""
    return "".join(unicodedata.normalize("NFD", c)[0].lower()[:1] or c for c in text)


def _names(terms: Iterable[Term]) -> list[str]:
    seen: dict[str, str] = {}
    for term in terms:
        seen.setdefault(_fold(term.name), term.name)
    return list(seen.values())


def canonicalize(text: str, terms: Iterable[Term]) -> str:
    """Replaces each alias said as whole words, ignoring case, accents and extra spaces."""
    by_alias = {
        " ".join(_fold(alias).split()): term.name
        for term in terms
        for alias in term.aliases
        if alias.strip()
    }
    if not by_alias:
        return text
    words = sorted(by_alias, key=len, reverse=True)  # longest first: "saite seils" before "saite"
    pattern = re.compile(
        r"(?<!\w)(" + "|".join(r"\s+".join(map(re.escape, w.split())) for w in words) + r")(?!\w)"
    )
    folded, out, last = _fold(text), [], 0
    for match in pattern.finditer(folded):
        out += [text[last : match.start()], by_alias[" ".join(match.group().split())]]
        last = match.end()
    return "".join([*out, text[last:]])


def whisper_words(terms: Iterable[Term]) -> str:
    """Hotwords for Whisper: the real names, so it learns how they are spelled."""
    return ", ".join(_names(terms))


def hint(terms: Iterable[Term]) -> str:
    """Line sent to Alfred ahead of the command, so he can fix a name Whisper got wrong."""
    names = _names(terms)
    return f"[Nomes conhecidos: {', '.join(names)}]" if names else ""
