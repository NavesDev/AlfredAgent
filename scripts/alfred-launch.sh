#!/usr/bin/env bash
# Desktop launcher: starts server + web (make dev) if not running, then opens the panel
# in the desktop app (make build-desktop) or, without it, in the browser.
# Usage: alfred-launch.sh [start|stop]
set -euo pipefail

ROOT="$(cd "$(dirname "$(readlink -f "$0")")/.." && pwd)"
STATE="${XDG_STATE_HOME:-$HOME/.local/state}/alfred"
PIDFILE="$STATE/alfred.pid"
LOG="$STATE/alfred.log"
URL="http://localhost:5173"
DESKTOP="$ROOT/apps/desktop/src-tauri/target/release/alfred-desktop"
export PATH="$HOME/.local/bin:$PATH"
mkdir -p "$STATE"

running() { [[ -f "$PIDFILE" ]] && kill -0 "$(cat "$PIDFILE")" 2>/dev/null; }
notify() { command -v notify-send >/dev/null && notify-send -i "$ROOT/apps/web/public/favicon.svg" Alfred "$1" || true; }

case "${1:-start}" in
  stop)
    pkill -f "$DESKTOP" 2>/dev/null || true
    if running; then
      # SIGINT like Ctrl+C: the server only shuts down cleanly on it.
      pgid="$(cat "$PIDFILE")"
      kill -INT -- "-$pgid" 2>/dev/null || true
      for _ in $(seq 1 10); do pgrep -g "$pgid" >/dev/null || break; sleep 1; done
      kill -KILL -- "-$pgid" 2>/dev/null || true
      rm -f "$PIDFILE"
      notify "Alfred parado."
    else
      notify "Alfred não está rodando."
    fi
    ;;
  start)
    if ! running; then
      notify "Iniciando Alfred..."
      cd "$ROOT"
      setsid make dev >"$LOG" 2>&1 < /dev/null &
      echo $! >"$PIDFILE"
      for _ in $(seq 1 60); do
        curl -fs -o /dev/null "$URL" && break
        running || { notify "Alfred falhou ao iniciar. Log: $LOG"; exit 1; }
        sleep 1
      done
    fi
    if [[ -x "$DESKTOP" ]]; then
      setsid "$DESKTOP" >>"$LOG" 2>&1 < /dev/null &
    else
      xdg-open "$URL" >/dev/null 2>&1 &
    fi
    ;;
  *) echo "usage: $0 [start|stop]" >&2; exit 2 ;;
esac
