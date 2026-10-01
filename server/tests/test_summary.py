from infra.claude.summary import extract_summary


def test_uses_resumo_line() -> None:
    text = "JWT é stateless.\nSessão guarda estado.\nRESUMO: JWT carrega o estado; sessão guarda no server."
    assert extract_summary(text) == "JWT carrega o estado; sessão guarda no server."


def test_resumo_is_case_insensitive_and_strips_markdown() -> None:
    assert extract_summary("blá\n**Resumo:** Feito, `main` atualizada.") == "Feito, main atualizada."


def test_without_resumo_falls_back_to_first_sentence() -> None:
    assert extract_summary("Python foi criado em 1991. Por Guido.") == "Python foi criado em 1991."


def test_fallback_skips_code_blocks() -> None:
    assert extract_summary("```py\nprint(1)\n```\nImprime um. Simples.") == "Imprime um."


def test_empty_reply_gives_empty_summary() -> None:
    assert extract_summary("   ") == ""
