"""Read the control lines of an agent reply: RESUMO (spoken), APRESENTAR and GUARDAR (results,
ADR 0014)."""

import re
from dataclasses import dataclass

_CODE_BLOCK = re.compile(r"```.*?```", re.S)
_RESUMO = re.compile(r"^\W*resumo\W*:\W*(.+)$", re.I | re.M)
_PRESENT = re.compile(r"^\W*(apresentar|guardar)\W*:(.*)$", re.I | re.M)
_CONTROL = re.compile(r"^\W*(resumo|apresentar|guardar)\W*:.*$\n?", re.I | re.M)
_MARKDOWN = re.compile(r"[*_`#>]")
_EDGES = re.compile(r"^[\s*_`#>]+|[\s*_`#>]+$")  # markdown around a path, never inside
_SENTENCE = re.compile(r"(.+?[.!?])(\s|$)", re.S)
_REPORT = {"relatório", "relatorio"}


@dataclass(frozen=True)
class Presentation:
    show: bool  # APRESENTAR: show it now; GUARDAR only records it
    files: list[str]
    report: bool


def parse_resumo(text: str) -> str | None:
    match = _RESUMO.search(_CODE_BLOCK.sub("", text))
    return _MARKDOWN.sub("", match.group(1)).strip() if match else None


def extract_summary(text: str) -> str:
    if (resumo := parse_resumo(text)) is not None:
        return resumo
    plain = _MARKDOWN.sub("", _CODE_BLOCK.sub("", text)).strip()
    match = _SENTENCE.match(plain)
    return (match.group(1) if match else plain).strip()


def parse_presentation(text: str) -> Presentation | None:
    """What the reply asks to record; None without APRESENTAR/GUARDAR lines or items."""
    show, files, report = False, [], False
    for verb, items in _PRESENT.findall(_CODE_BLOCK.sub("", text)):
        show = show or verb.lower() == "apresentar"
        for item in (_EDGES.sub("", i) for i in items.split(";")):
            if item.lower() in _REPORT:
                report = True
            elif item and item not in files:
                files.append(item)
    return Presentation(show, files, report) if files or report else None


def strip_control(text: str) -> str:
    """The reply without its control lines: the details a report shows."""
    return _CONTROL.sub("", text).strip()
