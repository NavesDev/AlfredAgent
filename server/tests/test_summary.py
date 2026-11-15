from infra.claude.summary import Presentation, extract_summary, parse_presentation, strip_control


def test_uses_resumo_line() -> None:
    text = (
        "JWT é stateless.\nSessão guarda.\nRESUMO: JWT carrega o estado; sessão guarda no server."
    )
    assert extract_summary(text) == "JWT carrega o estado; sessão guarda no server."


def test_resumo_is_case_insensitive_and_strips_markdown() -> None:
    assert (
        extract_summary("blá\n**Resumo:** Feito, `main` atualizada.") == "Feito, main atualizada."
    )


def test_without_resumo_falls_back_to_first_sentence() -> None:
    assert extract_summary("Python foi criado em 1991. Por Guido.") == "Python foi criado em 1991."


def test_fallback_skips_code_blocks() -> None:
    assert extract_summary("```py\nprint(1)\n```\nImprime um. Simples.") == "Imprime um."


def test_empty_reply_gives_empty_summary() -> None:
    assert extract_summary("   ") == ""


# --- presentation lines (ADR 0014) ---------------------------------------------------------

def test_apresentar_with_a_file_shows_it() -> None:
    text = "RESUMO: Gerei o retrato.\nAPRESENTAR: /home/u/retrato.png"
    assert parse_presentation(text) == Presentation(True, ["/home/u/retrato.png"], False)


def test_guardar_records_without_showing() -> None:
    assert parse_presentation("RESUMO: Feito.\nGUARDAR: relatório") == Presentation(
        False, [], True
    )


def test_items_split_by_semicolon_and_cleaned() -> None:
    text = "**Apresentar:** `/home/u/a.gif`; relatorio ; /home/u/b.png"
    assert parse_presentation(text) == Presentation(True, ["/home/u/a.gif", "/home/u/b.png"], True)


def test_without_control_lines_nothing_is_recorded() -> None:
    assert parse_presentation("RESUMO: Li o arquivo.\nNada demais.") is None


def test_empty_items_record_nothing() -> None:
    assert parse_presentation("APRESENTAR:   ;  ") is None


def test_lines_inside_code_blocks_are_ignored() -> None:
    assert parse_presentation("```\nAPRESENTAR: /home/u/x.png\n```") is None


def test_apresentar_wins_over_guardar_and_items_merge() -> None:
    text = "GUARDAR: relatório\nAPRESENTAR: /home/u/a.png"
    assert parse_presentation(text) == Presentation(True, ["/home/u/a.png"], True)


def test_strip_control_keeps_only_the_details() -> None:
    text = "RESUMO: Feito.\nMudei o login.\n\nAPRESENTAR: relatório\n"
    assert strip_control(text) == "Mudei o login."


def test_underscores_inside_a_path_survive() -> None:
    text = "APRESENTAR: __/home/u/my_file_v2.png__"
    assert parse_presentation(text) == Presentation(True, ["/home/u/my_file_v2.png"], False)
