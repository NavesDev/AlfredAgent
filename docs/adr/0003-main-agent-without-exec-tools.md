# 0003 — Agente principal sem Bash nem Edit

- **Status:** Aceito
- **Data:** 2026-10-01

## Contexto

O agente principal lê conteúdo externo não confiável (e-mails, páginas web). Esse conteúdo pode carregar prompt injection.

## Decisão

O agente `alfred` não recebe Bash, Edit nem Write. Trabalho em repositório é sempre delegado a uma sessão nomeada via `delegar`. Além disso, um turno que leu e-mail ou web fica "contaminado": qualquer ação com efeito colateral nele exige confirmação pelo canal `tainted_turn`.

## Consequências

- Quem lê conteúdo externo nunca executa comando diretamente.
- `delegar` vira o ponto de controle: é uma ação com efeito colateral e passa pelo gate de turno contaminado.
- Fluxos simples ("cria um arquivo de notas") ficam um passo mais longos.
