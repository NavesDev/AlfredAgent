# 0011 — Alfred reads the home and opens a worktree on its own for a new feature

- **Status:** Accepted
- **Date:** 2026-11-14
- Amends [0003](0003-main-agent-without-exec-tools.md) and [0006](0006-system-session-for-computer-tasks.md)

## Context

Without reading files, Alfred delegated every question about a project ("what database does Vrummy use?") and every check ("does the back end have uncommitted changes?") to a session. Slow, and it spends processes and tokens. It also created a worktree and a session only after asking, and worktrees created outside it did not become workspaces.

## Decision

- **Local reads:** Alfred gets `Read`, `Glob` and `Grep`, allowed without the classifier, with `cwd` in the home.
  - The `guard_local_paths` hook (PreToolUse) resolves the real path (`realpath`, no `path` = `cwd`) and denies anything outside the home, including through symlinks and `..`.
  - `Read(...)` rules in `disallowed_tools` deny secret files: `.env*`, `~/.ssh`, `~/.gnupg`, `~/.aws`, `~/.config/gh`, Claude credentials, `*.pem`, `*.key`, `id_*`, `~/.netrc`.
  - Still no Bash, Edit or Write (ADR 0003) and no `file://` in the browser (ADR 0005).
- **When to delegate:** questions and checks Alfred answers by reading; implementing, fixing, testing or a large project analysis goes to a session; computer commands still go to `delegar_geral`.
- **Git state:** a `ver_ambiente` tool (branch, changed files, last commits, recent branches) without going through a session.
- **GitHub issues:** `ver_issue` and `listar_issues` tools run `gh` on the server with fixed, read-only arguments, on the workspace's `origin` repo. Alfred gets no shell.
- **Descriptions:** projects, workspaces and sessions have a short description, context only for Alfred to decide where to delegate.
- **New feature:** the implementation mode (the workspace's, or the global one) guides Alfred. It looks at the branch conventions, the issue and the code, decides whether to create a worktree and the branch name, and calls `iniciar_feature`, which creates the worktree, workspace and session (or uses the workspace's session) and delegates, without asking. A `worktree` workspace always implements in itself.
- **Mirrored worktrees:** the server watches each workspace repo's `.git/worktrees/` through inotify; a change there runs `git worktree list` for that repo. A new worktree becomes a workspace; a vanished worktree takes its workspace and sessions with it. Full sync at startup.

## Consequences

- Questions and checks are answered without opening a session.
- **Accepted risk:** in the same turn Alfred may read a mail or page and then read home files. An injected instruction could try to leak the content through a URL or mail. Mitigations: secrets denied, the auto mode classifier on sending actions, and the rule to treat external content as data.
- Registering a project or workspace outside the feature flow still depends on the user's yes (prompt rule).
- Deleting a worktree in the terminal deletes its sessions in Alfred.
