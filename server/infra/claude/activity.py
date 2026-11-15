"""Turns tool names into what Alfred is doing, in pt-BR, for the panel and for speech."""

import re
from typing import Literal

Phase = Literal["exploring", "editing", "running"]

Action = Literal[
    "delegate",
    "session",
    "project",
    "command",
    "files_read",
    "files_edit",
    "web_search",
    "web_page",
    "email_read",
    "email_send",
    "calendar_read",
    "calendar_write",
    "drive",
    "browser",
    "tool",
]

# (pattern, label, action): the label is said and shown; the action picks the panel's card.
_TABLE: list[tuple[str, str, Action]] = [
    (r"^mcp__alfred__delegar_", "Mandando para uma sessão", "delegate"),
    (r"^mcp__alfred__criar_sessao$", "Criando uma sessão", "session"),
    (r"^mcp__alfred__limpar_sessao$", "Limpando uma sessão", "session"),
    (r"^mcp__alfred__apagar_sessao$", "Apagando uma sessão", "session"),
    (r"^mcp__alfred__listar_sessoes$", "Vendo as sessões", "session"),
    (r"^mcp__alfred__criar_projeto$", "Criando um projeto", "project"),
    (r"^mcp__alfred__listar_projetos$", "Vendo os projetos", "project"),
    (r"^mcp__alfred__criar_ambiente$", "Criando um ambiente", "project"),
    (r"^mcp__alfred__criar_worktree$", "Criando um worktree", "project"),
    (r"^mcp__alfred__apagar_ambiente$", "Apagando um ambiente", "project"),
    (r"^mcp__alfred__definir_apelidos$", "Ajustando apelidos", "session"),
    (r"^mcp__alfred__definir_descricao$", "Ajustando uma descrição", "project"),
    (r"^mcp__alfred__ver_ambiente$", "Vendo o git do ambiente", "project"),
    (r"^mcp__alfred__iniciar_feature$", "Preparando a feature", "project"),
    (r"^mcp__alfred__definir_ambiente_padrao$", "Ajustando o ambiente padrão", "project"),
    (r"^Bash$", "Executando um comando", "command"),
    (r"^Read$", "Lendo um arquivo", "files_read"),
    (r"^(Glob|Grep)$", "Buscando nos arquivos", "files_read"),
    (r"^(Edit|Write)$", "Editando arquivos", "files_edit"),
    (r"^WebSearch$", "Pesquisando na web", "web_search"),
    (r"^WebFetch$", "Lendo uma página", "web_page"),
    (r"Gmail__(search_threads|list_)", "Analisando seus e-mails", "email_read"),
    (r"Gmail__(send_message|reply|forward)", "Enviando o e-mail", "email_send"),
    (r"Gmail__", "Lendo um e-mail", "email_read"),
    (r"Calendar__suggest_time", "Procurando um horário livre", "calendar_read"),
    (r"Calendar__(create|update|delete|respond)", "Mexendo na sua agenda", "calendar_write"),
    (r"Calendar__", "Consultando sua agenda", "calendar_read"),
    (r"Google_Drive__", "Procurando no seu Drive", "drive"),
    (r"chrome-devtools__(new_page|navigate_page)$", "Abrindo no navegador", "browser"),
    (
        r"chrome-devtools__(take_snapshot|take_screenshot|wait_for)$",
        "Olhando a página",
        "browser",
    ),
    (
        r"chrome-devtools__(click|fill|fill_form|type_text|press_key|hover|drag)$",
        "Mexendo na página",
        "browser",
    ),
    (r"chrome-devtools__", "Usando o navegador", "browser"),
]
_RULES = [(re.compile(p), label, action) for p, label, action in _TABLE]


def _rule(name: str) -> tuple[str, Action] | None:
    for pattern, label, action in _RULES:
        if pattern.search(name):
            return label, action
    return None


def describe_tool(name: str) -> str:
    rule = _rule(name)
    return rule[0] if rule else "Usando " + name.split("__")[-1].replace("_", " ")


def action_of(name: str) -> Action:
    """The kind of step, so the panel can draw a card for it; unknown tools are "tool"."""
    rule = _rule(name)
    return rule[1] if rule else "tool"


_PHASES: dict[str, Phase] = {
    **dict.fromkeys(
        ("Read", "Grep", "Glob", "LS", "WebSearch", "WebFetch", "NotebookRead"), "exploring"
    ),
    **dict.fromkeys(("Edit", "Write", "MultiEdit", "NotebookEdit"), "editing"),
    **dict.fromkeys(("Bash", "BashOutput"), "running"),
}


def phase_of(name: str) -> Phase | None:
    """What a coding session is doing, for the butler on the panel. Other tools keep the phase."""
    return _PHASES.get(name)
