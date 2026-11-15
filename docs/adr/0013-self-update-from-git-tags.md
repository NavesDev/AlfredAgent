# 0013 — Self-update from the repo's release tags

- **Status:** Accepted
- **Date:** 2026-11-15

## Context

Releases are cut by release-please as `vX.Y.Z` tags with a GitHub release (CONTRIBUTING). Alfred runs from a git checkout: a Python server with a ~7.5 GB venv (torch, CUDA), the web panel and a locally built Tauri shell. The user wants Alfred to update itself when a release comes out.

A packaged updater (Tauri updater, a bundled server) would download the whole venv on every version, and rewriting the voice models outside Python only to package them is out of proportion.

## Decision

- **Check:** the server compares the newest local tag (`git tag`) with the newest remote one (`git ls-remote --tags origin 'v*'`) at boot and every 6 hours, or on request. The repo is private; the machine's SSH key already reads it. The notes are the release's CHANGELOG section, read with `git show <tag>:CHANGELOG.md` after fetching the tag.
- **Show:** an `update_status` event and `GET /api/update`. The panel shows a pill on the control bar and an "Atualizações" settings section with the notes and an "Atualizar" button.
- **Apply:** `POST /api/update/apply` refuses unless the checkout is on `main` and clean, then starts `scripts/alfred-update.sh <tag>` in its own session (it outlives the server). The script:
  1. stops Alfred (the launcher's process group, then whatever still listens on the server and panel ports);
  2. fetches the tag and fast-forwards `main` to it;
  3. runs `uv sync` and `pnpm install --frozen-lockfile` (only changed packages download; models stay in the Hugging Face cache);
  4. rebuilds the desktop binary when it exists and `apps/desktop` changed;
  5. starts Alfred again through the launcher.
- **Rollback:** if any step from 2 to 4 fails, the script resets `main` to the previous commit, reinstalls and starts the old version.
- **Result:** the script writes `update.json` (from, to, ok, error) in the launcher's state folder; the server reads it at boot and the settings section shows the last update.

## Consequences

- Updating takes seconds, or a few minutes when the desktop binary is rebuilt; nothing heavy is downloaded again.
- Works only for a git checkout on `main` with SSH access to the repo: it is a personal install, not a distribution channel.
- Local changes block the update instead of being stashed: nothing of the user's is touched.
- A release that breaks `uv sync` or the build rolls back by itself; a release that installs but misbehaves at runtime needs a manual `git checkout` of the previous tag.
