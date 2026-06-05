#!/usr/bin/env bash
# Run ON THE MAC, from inside the copied imessage-relay folder:
#     bash install-mac.sh
# Installs the relay as a launchd service that auto-starts and stays up.
set -e

HERE="$(cd "$(dirname "$0")" && pwd)"
NODE="$(command -v node || true)"
[ -z "$NODE" ] && { echo "Node not found. Install it: brew install node"; exit 1; }

# Relay must live at ~/imessage-relay (the plist points there). Copy if needed.
DEST="$HOME/imessage-relay"
if [ "$HERE" != "$DEST" ]; then
  mkdir -p "$DEST"
  cp "$HERE/relay.js" "$DEST/relay.js"
  cp "$HERE/com.tmmt.imessage-relay.plist" "$DEST/com.tmmt.imessage-relay.plist"
fi

PLIST_SRC="$DEST/com.tmmt.imessage-relay.plist"
PLIST_DEST="$HOME/Library/LaunchAgents/com.tmmt.imessage-relay.plist"
mkdir -p "$HOME/Library/LaunchAgents"

# Fill in this machine's node path + home, then install.
sed -e "s|__NODE__|$NODE|g" -e "s|__HOME__|$HOME|g" "$PLIST_SRC" > "$PLIST_DEST"

launchctl unload "$PLIST_DEST" 2>/dev/null || true
launchctl load "$PLIST_DEST"

echo "Installed + loaded. Testing health..."
sleep 1
curl -s localhost:8787/health && echo "" || echo "(no response yet — check /tmp/imessage-relay.err)"
echo ""
echo "NOTE: macOS will ask to let node control 'Messages' the first time it sends."
echo "Approve it: System Settings > Privacy & Security > Automation."
