# 0006 — Tarefas no computador vão para a sessão "sistema"

- **Status:** Aceito
- **Data:** 2026-10-11

## Contexto

O Alfred não tem Bash (ADR 0003), então não conseguia fazer nada no computador (girar a tela, contar projetos, mexer em arquivos) e chegou a ler arquivos por `file://` no navegador. Dar Bash a ele juntaria no mesmo agente quem lê e-mail/web e quem executa comandos.

## Decisão

- Antecipa parte da fase 3: uma sessão nomeada `sistema` (`infra/claude/session.py`), um Claude Code persistente com `Bash`, `Read`, `Edit`, `Write`, `Glob`, `Grep`, `cwd` na home e `permission_mode="auto"`.
- A sessão não carrega MCPs (`strict_mcp_config`) nem configurações do usuário (`setting_sources=[]`), e não tem WebSearch/WebFetch: conteúdo externo não chega direto a ela.
- O Alfred ganha a tool in-process `delegar(tarefa)` (`infra/claude/tools.py`). Ela enfileira a tarefa em `controllers/sessions.py` e volta na hora; a sessão roda em segundo plano, uma tarefa por vez, e o resumo é falado quando termina.
- O prompt do Alfred manda descrever a tarefa com as próprias palavras, nunca colando texto de e-mails ou páginas.

## Consequências

- O Alfred passa a fazer tarefas no computador por voz, sem travar a conversa.
- Risco que sobra: um e-mail ou página pode convencer o Alfred a delegar algo ruim. Mitigações: a regra de não colar conteúdo externo e o classificador do auto mode na sessão.
- Uma sessão só por enquanto; sessões por projeto, worktrees e o limite `max_active_sessions` continuam na fase 3.
