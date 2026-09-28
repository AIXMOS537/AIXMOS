#!/bin/bash
# Portable mode — runs agents directly from the USB. Nothing installed to ~/AIXMOS.
cd "$(dirname "${BASH_SOURCE[0]}")"
USB_DIR="$(pwd)"

clear
echo ""
echo "  ============================================================"
echo "   AIXMOS AGENTS - PORTABLE MODE (Mac)"
echo "   Running directly from this USB. Nothing installed."
echo "  ============================================================"
echo ""

if ! command -v node >/dev/null 2>&1; then
  echo "  Node.js is not installed on this Mac."
  echo "  Install Homebrew + Node:"
  echo "    /bin/bash -c \"\$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)\""
  echo "    brew install node"
  echo ""
  read -p "  Press Enter to close..."
  exit 1
fi

if [ ! -d "$USB_DIR/node_modules/@anthropic-ai/sdk" ]; then
  echo "  node_modules missing on USB. Installing once (saves to USB)..."
  npm install --silent
fi

if [ -z "$ANTHROPIC_API_KEY" ]; then
  echo "  WARNING: ANTHROPIC_API_KEY not set in this shell."
  echo "  Either set it now (export ANTHROPIC_API_KEY=...) or use offline mode."
  echo ""
fi

echo "  What do you want to launch?"
echo ""
echo "    1.  Master orchestrator menu"
echo "    2.  CHUMMO       - customer comms"
echo "    3.  MOOSE        - ops execution"
echo "    4.  CAPTAIN      - command brief"
echo "    5.  WONDER WOMAN - trust defender"
echo "    6.  VISION       - go/no-go"
echo "    7.  JARVIS       - speaks for the owner"
echo "    8.  TANK         - infrastructure"
echo "    9.  FLY GUY      - comms support"
echo "   10.  BOB          - audit + docs"
echo "   11.  STICKS       - SLA monitor"
echo "   12.  MORNING BRIEF"
echo "   13.  AGENT SMOKE TESTS (--live)"
echo "   14.  CHUMMO-GHL WEBHOOK (for GHL integration)"
echo ""
read -p "  Pick 1-14: " CHOICE

case "$CHOICE" in
  1)  node orchestrator.js ;;
  2)  node orchestrator.js chummo ;;
  3)  node moose.js ;;
  4)  node captain.js ;;
  5)  node wonderwoman.js ;;
  6)  node vision.js ;;
  7)  node jarvis.js ;;
  8)  node tank.js ;;
  9)  node flyguy.js ;;
  10) node bob.js ;;
  11) node sticks.js ;;
  12) node briefing.js ;;
  13) node test-all-agents.js --live ;;
  14)
      if [ -z "$GHL_WEBHOOK_SHARED_SECRET" ]; then
        echo "  GHL_WEBHOOK_SHARED_SECRET is not set. Set it via:"
        echo "    export GHL_WEBHOOK_SHARED_SECRET='<your-long-random-secret>'"
        echo "  then re-run."
      else
        cd "$USB_DIR/membership/services/chummo-ghl-webhook"
        node server.js
      fi
      ;;
  *)  echo "  Invalid choice." ;;
esac

echo ""
read -p "  Press Enter to close..."
