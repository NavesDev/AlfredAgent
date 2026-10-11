# 0005 — Agente principal no auto mode do Claude Code

- **Status:** Aceito
- **Data:** 2026-10-11
- Substitui o [0004](0004-main-agent-read-only-plus-browser.md)

## Contexto

Com a lista fixa do ADR 0004, o Alfred não conseguia agir (enviar e-mail, criar evento, usar o Drive) e o gate de confirmação da fase 5 ainda não existe. Também apareceu um furo: pelo navegador ele lia arquivos locais com `file://`.

## Decisão

- `permission_mode="auto"`: leituras de Gmail/Agenda, web e navegador rodam direto (`ALLOWED`); qualquer outra tool vai para o classificador do auto mode, que aprova ou nega cada chamada.
- Limites fixos, fora do classificador:
  - sem Bash, Edit ou Write (ADR 0003);
  - hook `PreToolUse` (`block_local_urls`) nega qualquer `url` que não seja http/https, em qualquer tool;
  - `upload_file` do navegador escondido.
- O auto mode exige Sonnet ou Opus; com Haiku o CLI cai para o modo padrão e nega tudo fora de `ALLOWED`.

## Consequências

- O Alfred pode enviar e-mail, mexer na agenda e no Drive se o classificador aprovar, sem confirmação sua.
- Prompt injection em e-mail ou página continua sendo o risco principal; a defesa passa a ser o classificador mais a instrução de tratar conteúdo externo como dado.
- Quando o gate da fase 5 existir, ações sensíveis (`send_email` etc.) devem voltar a pedir confirmação por canal configurado.
