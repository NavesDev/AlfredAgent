#!/usr/bin/env bash
# Self-update (ADR 0013): stops Alfred, fast-forwards main to a release tag, reinstalls,
# rebuilds the desktop binary when it changed and starts Alfred again. Any failure while
# updating rolls back to the previous commit. The server starts it detached
# (POST /api/update/apply); it can also run by hand.
# Usage: alfred-update.sh vX.Y.Z
set -uo pipefail

TAG="${1:?usage: $0 vX.Y.Z}"
ROOT="$(cd "$(dirname "$(readlink -f "$0")")/.." && pwd)"
STATE="${XDG_STATE_HOME:-$HOME/.local/state}/alfred"
RESULT="$STATE/update.json"
DESKTOP="apps/desktop/src-tauri/target/release/alfred-desktop"
read -ra PORTS <<<"${ALFRED_PORTS:-8000 5173}" # server (config.yaml api.port), panel (Vite)
export PATH="$HOME/.local/bin:$HOME/.cargo/bin:$PATH"
mkdir -p "$STATE"
exec >>"$STATE/update.log" 2>&1
cd "$ROOT" || exit 1

log() { echo "$(date '+%F %T') $*"; }
notify() { command -v notify-send >/dev/null && notify-send -i "$ROOT/apps/web/public/favicon.svg" Alfred "$1" || true; }
json() { [[ -n "$1" ]] && printf '"%s"' "${1//\"/\'}" || printf null; }
result() { # ok error
  printf '{"from": %s, "to": "%s", "ok": %s, "error": %s, "at": %s}\n' \
    "$(json "$FROM")" "$TAG" "$1" "$(json "$2")" "$(date +%s)" >"$RESULT"
}

FROM="$(git describe --tags --abbrev=0 --match 'v*' 2>/dev/null || true)"
PREV="$(git rev-parse HEAD)"
log "update $FROM -> $TAG (at $PREV)"

# Same checks as the server, in case the tree changed since the click.
if [[ "$(git branch --show-current)" != main ]]; then
  result false "o Alfred não está na branch main"; exit 1
fi
if [[ -n "$(git status --porcelain)" ]]; then
  result false "o repositório tem mudanças não commitadas"; exit 1
fi

stop_alfred() {
  scripts/alfred-launch.sh stop || true
  pkill -f "[t]arget/debug/alfred-desktop" || true
  for port in "${PORTS[@]}"; do
    for pid in $(ss -ltnpH "sport = :$port" | grep -o 'pid=[0-9]*' | cut -d= -f2 | sort -u); do
      kill -INT "$pid" 2>/dev/null || true
    done
  done
  for _ in $(seq 1 15); do
    busy=0
    for port in "${PORTS[@]}"; do ss -ltnH "sport = :$port" | grep -q . && busy=1; done
    ((busy)) || return 0
    sleep 1
  done
  for port in "${PORTS[@]}"; do
    for pid in $(ss -ltnpH "sport = :$port" | grep -o 'pid=[0-9]*' | cut -d= -f2 | sort -u); do
      kill -KILL "$pid" 2>/dev/null || true
    done
  done
}

install() {
  (cd server && uv sync) &&
    (cd apps/web && pnpm install --frozen-lockfile) &&
    (cd apps/desktop && pnpm install --frozen-lockfile)
}

update() {
  git fetch --quiet origin tag "$TAG" --no-tags &&
    git merge --ff-only --quiet "$TAG" &&
    install &&
    if [[ -x "$DESKTOP" ]] && ! git diff --quiet "$PREV" HEAD -- apps/desktop; then
      make build-desktop
    fi
}

sleep 1 # let the API answer the click before the server goes down
notify "Atualizando o Alfred para $TAG…"
stop_alfred
if update; then
  log "updated to $TAG"
  result true ""
  notify "Alfred atualizado para $TAG."
else
  log "update to $TAG failed, rolling back to $PREV"
  git reset --hard --quiet "$PREV"
  install || log "reinstalling $PREV failed too"
  result false "a atualização para $TAG falhou e voltei para ${FROM:-a versão anterior}; veja $STATE/update.log"
  notify "A atualização falhou; o Alfred voltou para ${FROM:-a versão anterior}."
fi
scripts/alfred-launch.sh start
