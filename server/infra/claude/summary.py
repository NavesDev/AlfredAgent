"""Pick the spoken line from an agent reply: RESUMO line, else first sentence."""

import re

_CODE_BLOCK = re.compile(r"```.*?```", re.S)
_RESUMO = re.compile(r"^\W*resumo\W*:\W*(.+)$", re.I | re.M)
_MARKDOWN = re.compile(r"[*_`#>]")
_SENTENCE = re.compile(r"(.+?[.!?])(\s|$)", re.S)


def parse_resumo(text: str) -> str | None:
    match = _RESUMO.search(_CODE_BLOCK.sub("", text))
    return _MARKDOWN.sub("", match.group(1)).strip() if match else None


def extract_summary(text: str) -> str:
    if (resumo := parse_resumo(text)) is not None:
        return resumo
    plain = _MARKDOWN.sub("", _CODE_BLOCK.sub("", text)).strip()
    match = _SENTENCE.match(plain)
    return (match.group(1) if match else plain).strip()
