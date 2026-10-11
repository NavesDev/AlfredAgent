# 0004 — Agente principal: leitura liberada + navegador, antes do gate de confirmação

- **Status:** Substituído por 0005
- **Data:** 2026-10-11

## Contexto

O agente principal abre o CLI do Claude Code, que carrega os MCPs do usuário (conectores do claude.ai como Gmail, Agenda e Drive, e plugins como o chrome-devtools). Sem regra explícita, o modo não interativo negava todas as chamadas, e o modelo ainda anunciava capacidades que não tinha. O gate de confirmação por voz/painel (fase 5) ainda não existe, então a regra de "turno contaminado" não tem como pedir confirmação.

## Decisão

Política em `server/infra/claude/permissions.py`, com `permission_mode="dontAsk"`:

- **Liberado sem confirmação:** WebSearch, WebFetch, leitura de Gmail e Agenda, e o servidor chrome-devtools inteiro (abrir páginas, clicar, ler, rodar JS).
- **Escondido e negado:** tudo que escreve no Gmail e na Agenda, `upload_file` do navegador, Drive, Claude Docs e outros MCPs conhecidos.
- Qualquer tool não listada é negada, inclusive MCPs instalados depois.
- Continua valendo o ADR 0003: nada de Bash, Edit ou Write.

## Consequências

- O Alfred passa a ler e-mail, agenda e web, e a abrir páginas no Chrome por voz.
- **Risco aceito:** no mesmo turno ele pode ler um e-mail ou página e agir no navegador logado. Uma instrução injetada poderia navegar para um site e vazar conteúdo pela URL. O prompt manda tratar e-mails e páginas como dados, mas isso mitiga, não impede.
- Quando o gate da fase 5 existir, o navegador passa a exigir confirmação em turnos contaminados, e este ADR é substituído.
