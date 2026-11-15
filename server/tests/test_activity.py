import pytest

from infra.claude.activity import action_of, describe_tool, phase_of


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
        ("Read", "Lendo um arquivo"),
        ("Grep", "Buscando nos arquivos"),
        ("Glob", "Buscando nos arquivos"),
        ("mcp__alfred__ver_ambiente", "Vendo o git do ambiente"),
        ("mcp__alfred__iniciar_feature", "Preparando a feature"),
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


@pytest.mark.parametrize(
    ("name", "action"),
    [
        ("WebSearch", "web_search"),
        ("WebFetch", "web_page"),
        ("mcp__claude_ai_Gmail__search_threads", "email_read"),
        ("mcp__claude_ai_Gmail__reply", "email_send"),
        ("mcp__claude_ai_Google_Calendar__suggest_time", "calendar_read"),
        ("mcp__claude_ai_Google_Calendar__create_event", "calendar_write"),
        ("mcp__claude_ai_Google_Drive__search_files", "drive"),
        ("mcp__plugin_chrome-devtools-mcp_chrome-devtools__click", "browser"),
        ("mcp__alfred__delegar_geral", "delegate"),
        ("mcp__alfred__criar_sessao", "session"),
        ("mcp__alfred__criar_worktree", "project"),
        ("Bash", "command"),
        ("Grep", "files_read"),
        ("Write", "files_edit"),
        ("mcp__other__do_thing", "tool"),
    ],
)
def test_action_of(name: str, action: str) -> None:
    assert action_of(name) == action
