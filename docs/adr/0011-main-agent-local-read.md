# 0011 — Alfred lê a home e abre worktree sozinho para feature nova

- **Status:** Aceito
- **Data:** 2026-11-14
- Emenda o [0003](0003-main-agent-without-exec-tools.md) e o [0006](0006-system-session-for-computer-tasks.md)

## Contexto

Sem ler arquivos, o Alfred delegava toda pergunta sobre projeto ("o que o Vrummy usa de banco?") e toda verificação ("o back tem mudança não commitada?") para uma sessão. Lento, gasta processo e tokens. Também criava worktree e sessão só depois de perguntar, e worktrees criados fora dele não viravam ambientes.

## Decisão

- **Leitura local:** o Alfred ganha `Read`, `Glob` e `Grep`, liberados sem classificador, com `cwd` na home.
  - Hook `guard_local_paths` (PreToolUse) resolve o caminho real (`realpath`, sem `path` = `cwd`) e nega o que sai da home, inclusive por symlink e `..`.
  - Regras `Read(...)` em `disallowed_tools` negam arquivos secretos: `.env*`, `~/.ssh`, `~/.gnupg`, `~/.aws`, `~/.config/gh`, credenciais do Claude, `*.pem`, `*.key`, `id_*`, `~/.netrc`.
  - Continua sem Bash, Edit e Write (ADR 0003) e sem `file://` no navegador (ADR 0005).
- **Quando delegar:** pergunta e verificação o Alfred responde lendo; implementar, corrigir, testar ou análise grande de projeto vai para sessão; comando no computador continua em `delegar_geral`.
- **Estado git:** tool `ver_ambiente` (branch, alterados, últimos commits, branches recentes) sem passar por sessão.
- **Issues do GitHub:** tools `ver_issue` e `listar_issues` rodam no servidor o `gh` com argumentos fixos e só de leitura, no repo do `origin` do ambiente. O Alfred não ganha shell.
- **Descrições:** projeto, ambiente e sessão têm descrição curta, contexto só do Alfred para decidir onde delegar.
- **Feature nova:** o modo de implementação (do ambiente, ou o global) orienta o Alfred. Ele olha os padrões de branch, a issue e o código, decide se cria worktree e o nome da branch, e chama `iniciar_feature`, que cria worktree, ambiente e sessão (ou usa a sessão do ambiente) e delega, sem perguntar. Ambiente `worktree` sempre implementa nele mesmo.
- **Worktrees espelhados:** o servidor observa por inotify o `.git/worktrees/` de cada repo dos ambientes; mudança ali roda `git worktree list` daquele repo. Worktree novo vira ambiente; worktree que sumiu leva o ambiente e as sessões dele. Sincronia completa ao iniciar.

## Consequências

- Perguntas e verificações respondem sem abrir sessão.
- **Risco aceito:** no mesmo turno o Alfred pode ler um e-mail ou página e depois ler arquivos da home. Uma instrução injetada poderia tentar vazar o conteúdo por URL ou e-mail. Mitigações: secretos negados, o classificador do auto mode em ações de envio, e a regra de tratar conteúdo externo como dado.
- Cadastrar projeto ou ambiente fora do fluxo de feature continua dependendo do sim do usuário (regra de prompt).
- Apagar um worktree no terminal apaga as sessões dele no Alfred.
