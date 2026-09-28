#!/usr/bin/env bash
# AIXMOS Starter Pack — macOS launcher
# Double-click this file from Finder to open the menu.

cd "$(dirname "${BASH_SOURCE[0]}")"
PACK_DIR="$(pwd)"
export AIXMOS_PACK_DIR="$PACK_DIR"

clear
cat <<'BANNER'
================================================================
   █████  ██ ██   ██ ███    ███  ██████  ███████
  ██   ██ ██  ██ ██  ████  ████ ██    ██ ██
  ███████ ██   ███   ██ ████ ██ ██    ██ ███████
  ██   ██ ██  ██ ██  ██  ██  ██ ██    ██      ██
  ██   ██ ██ ██   ██ ██      ██  ██████  ███████

                  STARTER PACK — v1
================================================================
BANNER

while true; do
  # Detect install state
  if [ -d "$HOME/.aixmos/models" ] && [ "$(ls -A "$HOME/.aixmos/models" 2>/dev/null)" ]; then
    INSTALL_STATE="✅ installed"
  else
    INSTALL_STATE="⚠  not installed (run option 1)"
  fi

  # Detect running
  if curl -s --max-time 1 http://127.0.0.1:11434/api/tags >/dev/null 2>&1; then
    RUN_STATE="✅ Ollama running"
  else
    RUN_STATE="⏸  Ollama stopped"
  fi

  echo ""
  echo "  📍 Pack:    $PACK_DIR"
  echo "  📦 Status:  $INSTALL_STATE   |   $RUN_STATE"
  echo ""
  echo "  WHAT DO YOU WANT TO DO?"
  echo "  ─────────────────────────────────────────────────────"
  echo "   1) ⚙️   Install AIXMOS (first time, ~3 min)"
  echo "   2) ▶️   Start AIXMOS (open chat in browser)"
  echo "   3) ⏹   Stop AIXMOS"
  echo "   4) 🩺  Doctor (run health check)"
  echo "   5) 💬  Chat in terminal (no browser)"
  echo "   6) 📖  Open OPERATIONS_BRAIN docs"
  echo "   7) 📋  Copy system prompt to clipboard (for Claude/Cursor)"
  echo "   8) ⬇   Download/refresh model weights (~5 GB, internet)"
  echo "   9) 🔓  Unlock PRO pack (Agents of Chaos)"
  echo "  10) 🗑   Uninstall (remove ~/.aixmos models from this host)"
  echo "   q) Quit"
  echo "  ─────────────────────────────────────────────────────"
  printf "  Choice: "
  read -r choice

  case "$choice" in
    1) bash "$PACK_DIR/_starter/install.sh" ;;
    2) bash "$PACK_DIR/_starter/start.sh" ;;
    3) bash "$PACK_DIR/_starter/stop.sh" ;;
    4) bash "$PACK_DIR/_starter/doctor.sh" ;;
    5) bash "$PACK_DIR/_starter/chat.sh" ;;
    6) open "$PACK_DIR/_brain/docs/OPERATIONS_BRAIN.pdf" 2>/dev/null \
         || open "$PACK_DIR/_brain/docs/OPERATIONS_BRAIN.md" ;;
    7) cat "$PACK_DIR/_brain/system-prompts/default.md" | pbcopy \
         && echo "  ✅ System prompt copied. Paste into Claude.ai → Projects, or Cursor → Rules." ;;
    8) bash "$PACK_DIR/_starter/download-models.sh" ;;
    9) bash "$PACK_DIR/_pro/unlock.sh" 2>/dev/null \
         || echo "  PRO pack not present on this drive." ;;
    10) bash "$PACK_DIR/_starter/uninstall.sh" ;;
    q|Q) echo "  Bye."; exit 0 ;;
    *)  echo "  Unknown choice: $choice" ;;
  esac

  echo ""
  printf "  Press Enter to return to menu... "
  read -r _
done
