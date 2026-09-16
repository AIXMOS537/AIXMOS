#!/bin/bash
# Run the iMessage live poller. Cursor is not required.
# For Full Disk Access: this process must be /usr/local/bin/node with FDA,
# OR this script must be started from Terminal.app (Terminal already has FDA).
set -euo pipefail
export HOME="${HOME:-/Users/projectaixmos01}"
export PATH="/usr/local/bin:/opt/homebrew/bin:/usr/bin:/bin"
NODE="/usr/local/bin/node"
RELAY="$HOME/projects/AIXMOS-AGENTS/imessage-relay/assistant.js"
export IMESSAGE_AUTO_ASSISTANT=0  # CONTAINED 2026-09-16: auto-send OFF (owner charter P1-A)
export IMESSAGE_ALLOW_SEND=0  # CONTAINED 2026-09-16: send OFF
export RELAY_BIND=127.0.0.1
export RELAY_PORT=8790
exec "$NODE" "$RELAY" --live
