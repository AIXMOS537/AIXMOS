#!/bin/bash
# Double-click on Mac to start. If macOS blocks it, right-click → Open.
# If still blocked: open Terminal and run:  bash /path/to/this/file
cd "$(dirname "${BASH_SOURCE[0]}")"
clear
echo ""
echo "  ============================================================"
echo "   AIXMOS AGENT NETWORK - START HERE (Mac)"
echo "   10 agents: CHUMMO * MOOSE * CAPTAIN * WONDER WOMAN * VISION"
echo "              JARVIS * TANK * FLY GUY * BOB * STICKS"
echo "  ============================================================"
echo ""
echo "  What do you want to do?"
echo ""
echo "    1. INSTALL agents to this Mac (recommended for daily use)"
echo "       Mirrors the tree to ~/AIXMOS, creates shell aliases,"
echo "       can schedule the 7am brief via launchd."
echo ""
echo "    2. RUN agents from this USB (no install, fully portable)"
echo "       Useful for trying it out or borrowed Macs."
echo ""
echo "    3. SET UP OFFLINE MODE (install Ollama + local model)"
echo "       Lets the agents work without internet."
echo ""
echo "    4. OPEN THE USER GUIDE (PDF)"
echo ""
echo "    5. EXIT"
echo ""
read -p "  Pick 1-5: " CHOICE

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

case "$CHOICE" in
  1)
    bash "$HERE/install-mac.sh"
    ;;
  2)
    bash "$HERE/RUN-FROM-USB.command"
    ;;
  3)
    bash "$HERE/OFFLINE-MODE-SETUP.command"
    ;;
  4)
    if [ -f "$HERE/AIXMOS-GUIDE.pdf" ]; then
      open "$HERE/AIXMOS-GUIDE.pdf"
    elif [ -f "$HERE/AIXMOS-GUIDE.html" ]; then
      open "$HERE/AIXMOS-GUIDE.html"
    else
      echo "  Guide PDF not found. Run lib/build-guide.js to regenerate."
    fi
    ;;
  5)
    echo "  bye."
    ;;
  *)
    echo "  Invalid choice."
    ;;
esac
echo ""
read -p "  Press Enter to close..."
