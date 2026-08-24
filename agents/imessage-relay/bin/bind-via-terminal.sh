#!/bin/bash
# Silent keepalive for tmux rick-imessage. NEVER use `open` on a .command —
# that pops Terminal.app. Launchd must exec this .sh with /bin/bash.
set -euo pipefail
export HOME="${HOME:-/Users/projectaixmos01}"
export PATH="/usr/local/bin:/opt/homebrew/bin:/usr/bin:/bin"
NODE="/usr/local/bin/node"
RELAY="$HOME/projects/AIXMOS-AGENTS/imessage-relay/assistant.js"
LOCK="$HOME/.config/tmmt/imessage-assistant/live.lock"
LOG="/tmp/imessage-relay-term.log"
export IMESSAGE_AUTO_ASSISTANT=1
export IMESSAGE_ALLOW_SEND=1
export RELAY_BIND=127.0.0.1
export RELAY_PORT=8790

if [ -f "$LOCK" ]; then
  pid="$(tr -d '[:space:]' < "$LOCK" || true)"
  if [ -n "${pid:-}" ] && kill -0 "$pid" 2>/dev/null; then
    echo "Rick texts already running (pid $pid)."
    exit 0
  fi
fi
if command -v tmux >/dev/null 2>&1 && tmux has-session -t rick-imessage 2>/dev/null; then
  echo "tmux rick-imessage already up"
  exit 0
fi

if command -v tmux >/dev/null 2>&1; then
  tmux new-session -d -s rick-imessage "$NODE $RELAY --live"
  echo "Rick texts ON (tmux rick-imessage). Cursor not needed."
else
  nohup "$NODE" "$RELAY" --live >>"$LOG" 2>&1 &
  echo "Rick texts ON (pid $!). Cursor not needed. Log: $LOG"
fi
echo "Kill: me kill    Stop: me off"
