#!/usr/bin/env bash
# Install Text-My-Mac so it runs at login. Cursor is not required.
# Remaining macOS tap: Full Disk Access → /usr/local/bin/node  (Cmd+Shift+G)
set -euo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
NODE="/usr/local/bin/node"
[ -x "$NODE" ] || NODE="$(command -v node)"
[ -n "$NODE" ] || { echo "Node not found."; exit 1; }

PLIST_DEST="$HOME/Library/LaunchAgents/com.tmmt.imessage-relay.plist"
mkdir -p "$HOME/Library/LaunchAgents"
cp "$HERE/com.tmmt.imessage-relay.plist" "$PLIST_DEST"
chmod 600 "$PLIST_DEST"

chmod +x "$HERE/bin/run-live.sh" "$HERE/bin/bind-via-terminal.command" 2>/dev/null || true

UIDN="$(id -u)"
launchctl bootout "gui/$UIDN/com.tmmt.imessage-relay" 2>/dev/null || true
launchctl bootstrap "gui/$UIDN" "$PLIST_DEST"
launchctl kickstart -k "gui/$UIDN/com.tmmt.imessage-relay" 2>/dev/null || true

echo "Loaded com.tmmt.imessage-relay"
echo "If logs say EPERM on chat.db:"
echo "  System Settings → Privacy → Full Disk Access → + → Cmd+Shift+G → /usr/local/bin/node"
echo "  Then: me on"
echo "Or open Terminal.app (not Cursor) and run:  me bind"
echo "Mock: $NODE $HERE/assistant.js --mock-test"
