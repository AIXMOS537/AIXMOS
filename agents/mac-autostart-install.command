#!/bin/bash
# mac-autostart-install.command
# Makes the AIXMOS Agents of Chaos launch on Mac login (matches the Windows PC):
#   - agent-host (agent-server.js, port 7777)
#   - scheduler.js (daily CHUMMO/MOOSE jobs)
# Run this ONCE on the Mac after install-mac.sh has copied the tree to ~/AIXMOS.
# Double-click it in Finder (right-click -> Open if Gatekeeper blocks), or:
#   bash mac-autostart-install.command

set -e

# Where the agents live on the Mac (install-mac.sh copies here).
AGENTS="$HOME/AIXMOS"
if [ ! -f "$AGENTS/agent-server.js" ]; then
  # fall back to running straight from this folder (USB / no install)
  AGENTS="$(cd "$(dirname "$0")" && pwd)"
fi

NODE="$(command -v node || true)"
if [ -z "$NODE" ]; then
  echo "ERROR: node not found. Run install-mac.sh or OFFLINE-MODE-SETUP.command first."
  exit 1
fi

LA="$HOME/Library/LaunchAgents"
mkdir -p "$LA"
mkdir -p "$AGENTS/logs"

make_plist () {
  # $1 = label   $2 = script file
  local label="$1"; local script="$2"
  cat > "$LA/$label.plist" <<PLIST
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key><string>$label</string>
  <key>ProgramArguments</key>
  <array>
    <string>$NODE</string>
    <string>$AGENTS/$script</string>
  </array>
  <key>WorkingDirectory</key><string>$AGENTS</string>
  <key>RunAtLoad</key><true/>
  <key>KeepAlive</key><true/>
  <key>StandardOutPath</key><string>$AGENTS/logs/$label.out.log</string>
  <key>StandardErrorPath</key><string>$AGENTS/logs/$label.err.log</string>
</dict>
</plist>
PLIST
  # reload
  launchctl unload "$LA/$label.plist" 2>/dev/null || true
  launchctl load   "$LA/$label.plist" 2>/dev/null || true
  echo "  installed + loaded: $label"
}

echo "Installing AIXMOS autostart LaunchAgents (agents dir: $AGENTS)..."
make_plist "com.aixmos.agent-host" "agent-server.js"
make_plist "com.aixmos.scheduler"  "scheduler.js"

echo ""
echo "DONE. The Agents of Chaos will now start automatically every time you log in."
echo "Check health:  curl -s http://127.0.0.1:7777/healthz"
echo "Stop them:     launchctl unload ~/Library/LaunchAgents/com.aixmos.agent-host.plist"
