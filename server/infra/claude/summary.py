"""Pick the spoken line from an agent reply: RESUMO line, else first sentence."""

import re

_CODE_BLOCK = re.compile(r"```.*?```", re.S)
_RESUMO = re.compile(r"^\W*resumo\W*:\W*(.+)$", re.I | re.M)
_MARKDOWN = re.compile(r"[*_`#>]")
_SENTENCE = re.compile(r"(.+?[.!?])(\s|$)", re.S)


def extract_summary(text: str) -> str:
    text = _CODE_BLOCK.sub("", text)
    if match := _RESUMO.search(text):
        return _MARKDOWN.sub("", match.group(1)).strip()
    plain = _MARKDOWN.sub("", text).strip()
    match = _SENTENCE.match(plain)
    return (match.group(1) if match else plain).strip()
