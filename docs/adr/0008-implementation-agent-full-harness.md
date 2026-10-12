# 0008 — Agente de implementação com o harness completo do Claude Code

- **Status:** Aceito
- **Data:** 2026-10-11

## Contexto

As sessões do tipo `geral` (ADR 0006, 0007) rodam isoladas. Elas não leem as configurações do usuário (`setting_sources=[]`), não carregam MCPs (`strict_mcp_config`) e usam uma lista fixa de tools. Para trabalhar no código de um projeto, isso é pouco: faltam o CLAUDE.md do repositório, as skills, os plugins, os hooks e os MCPs que o usuário usa no Claude Code do dia a dia (docs, navegador, design).

## Decisão

- Novo tipo `implementacao` (`ImplementationAgent` em `infra/claude/agents.py`), sempre preso a um workspace de um projeto.
- O tipo usa o prompt preset `claude_code` com um `append` (nome da sessão, projeto, linha `RESUMO:`) e carrega:
  - `setting_sources=["user", "project", "local"]`;
  - `skills="all"`;
  - todas as tools, sem lista fixa;
  - `permission_mode="auto"`.
- Todos os MCPs do usuário vêm ligados por padrão. A tela de configurações guarda uma lista de servidores desligados, que vira `disallowed_tools=["mcp__<nome>"]`.
- O prompt manda usar MCPs externos (e-mail, agenda, navegador) só quando a tarefa pedir isso explicitamente.

## Consequências

- A sessão de implementação se comporta como o Claude Code no terminal do usuário, com o mesmo contexto e as mesmas ferramentas.
- **Risco aceito:** essa sessão pode ler conteúdo externo (e-mail ou web, via MCP) e executar comandos no mesmo turno. É o cenário que as ADRs 0003 e 0006 evitam para o Alfred e para a `sistema`.
- **Mitigações:**
  - o classificador do auto mode;
  - a regra do prompt sobre MCPs externos;
  - a lista de MCPs desligados;
  - o Alfred continua sem Bash/Edit/Write e descreve as tarefas com as próprias palavras.
- As permissões configuráveis da F5 (denylist, confirmação por canal) vão valer para esse tipo também quando chegarem.
