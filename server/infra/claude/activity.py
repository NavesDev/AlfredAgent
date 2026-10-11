"""Turns tool names into what Alfred is doing, in pt-BR, for the panel and for speech."""

import re

_RULES: list[tuple[re.Pattern[str], str]] = [
    (re.compile(p), label)
    for p, label in [
        (r"^mcp__alfred__delegar_", "Mandando para uma sessão"),
        (r"^mcp__alfred__criar_sessao$", "Criando uma sessão"),
        (r"^mcp__alfred__limpar_sessao$", "Limpando uma sessão"),
        (r"^mcp__alfred__apagar_sessao$", "Apagando uma sessão"),
        (r"^mcp__alfred__listar_sessoes$", "Vendo as sessões"),
        (r"^Bash$", "Executando um comando"),
        (r"^(Read|Glob|Grep)$", "Lendo arquivos"),
        (r"^(Edit|Write)$", "Editando arquivos"),
        (r"^WebSearch$", "Pesquisando na web"),
        (r"^WebFetch$", "Lendo uma página"),
        (r"Gmail__(search_threads|list_)", "Analisando seus e-mails"),
        (r"Gmail__(send_message|reply|forward)", "Enviando o e-mail"),
        (r"Gmail__", "Lendo um e-mail"),
        (r"Calendar__suggest_time", "Procurando um horário livre"),
        (r"Calendar__(create|update|delete|respond)", "Mexendo na sua agenda"),
        (r"Calendar__", "Consultando sua agenda"),
        (r"Google_Drive__", "Procurando no seu Drive"),
        (r"chrome-devtools__(new_page|navigate_page)$", "Abrindo no navegador"),
        (r"chrome-devtools__(take_snapshot|take_screenshot|wait_for)$", "Olhando a página"),
        (
            r"chrome-devtools__(click|fill|fill_form|type_text|press_key|hover|drag)$",
            "Mexendo na página",
        ),
        (r"chrome-devtools__", "Usando o navegador"),
    ]
]


def describe_tool(name: str) -> str:
    for pattern, label in _RULES:
        if pattern.search(name):
            return label
    return "Usando " + name.split("__")[-1].replace("_", " ")
