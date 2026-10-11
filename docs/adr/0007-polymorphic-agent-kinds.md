# 0007 — Tipos de agente polimórficos e sessões gerenciadas por voz

- **Status:** Aceito
- **Data:** 2026-10-11

## Contexto

A ADR 0006 criou uma sessão fixa `sistema` e uma tool `delegar(tarefa)` presa a ela. O roadmap prevê outros tipos de agente (o próximo é o de implementação, preso a um projeto), e o usuário quer criar, limpar e apagar sessões por voz e ver cada uma na tela.

## Decisão

- Cada tipo de agente é uma subclasse de `AgentKind` (`infra/claude/agents.py`) que define as tools do Claude Code, o prompt e a própria tool de delegar do Alfred (`delegar_<tipo>`). O registro `KINDS` é a fonte única dos tipos.
- O primeiro tipo é `geral` (`GeneralAgent`), que herda tudo da sessão `sistema` da ADR 0006. `sistema` vira uma sessão desse tipo, criada no boot e protegida contra apagar.
- Tools de ciclo de vida são genéricas: `criar_sessao`, `limpar_sessao`, `apagar_sessao`, `listar_sessoes`. Limpar cancela a tarefa em andamento e zera o contexto; apagar também remove a sessão.
- Sessões ficam em memória e respeitam `limits.max_active_sessions`.
- O painel mostra um cartão por sessão e permite limpar e apagar pela API.

## Consequências

- Adicionar um tipo é criar uma subclasse e registrá-la; o Alfred ganha a tool sem mudar o controller.
- O Alfred continua sem Bash/Edit/Write (ADR 0003): as tools novas só mexem no registro de sessões.
- Um e-mail ou página ainda pode convencer o Alfred a criar ou apagar sessões. Apagar exige confirmação verbal e `sistema` é protegida; o pior caso é perder o contexto de uma sessão.
- Reiniciar o server perde as sessões criadas por voz até a F4 (SQLite + resume).
