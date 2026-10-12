import pytest

from infra.claude.activity import describe_tool, phase_of


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
        ("mcp__alfred__delegar_geral", "Mandando para uma sessão"),
        ("mcp__other__do_thing", "Usando do thing"),
    ],
)
def test_describe_tool(name: str, label: str) -> None:
    assert describe_tool(name) == label


@pytest.mark.parametrize(
    ("name", "phase"),
    [
        ("Read", "exploring"),
        ("Grep", "exploring"),
        ("Glob", "exploring"),
        ("WebFetch", "exploring"),
        ("Edit", "editing"),
        ("MultiEdit", "editing"),
        ("Write", "editing"),
        ("NotebookEdit", "editing"),
        ("Bash", "running"),
        ("BashOutput", "running"),
        ("TodoWrite", None),
        ("Skill", None),
        ("mcp__context7__query_docs", None),
    ],
)
def test_phase_of(name: str, phase: str | None) -> None:
    assert phase_of(name) == phase
