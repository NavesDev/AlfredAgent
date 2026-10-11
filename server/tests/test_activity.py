import pytest

from infra.claude.activity import describe_tool


@pytest.mark.parametrize(
    ("name", "label"),
    [
        ("WebSearch", "Pesquisando na web"),
        ("mcp__claude_ai_Gmail__search_threads", "Analisando seus e-mails"),
        ("mcp__claude_ai_Gmail__get_thread", "Lendo um e-mail"),
        ("mcp__claude_ai_Gmail__send_message", "Enviando o e-mail"),
        ("mcp__claude_ai_Google_Calendar__list_events", "Consultando sua agenda"),
        ("mcp__plugin_chrome-devtools-mcp_chrome-devtools__new_page", "Abrindo no navegador"),
        ("Bash", "Executando um comando"),
        ("mcp__alfred__delegar", "Mandando para a sessão sistema"),
        ("mcp__other__do_thing", "Usando do thing"),
    ],
)
def test_describe_tool(name: str, label: str) -> None:
    assert describe_tool(name) == label
