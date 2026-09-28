#!/usr/bin/env bash
# AIXMOS Starter Pack — start daily session (Mac/Linux)
# Starts Ollama service (if not running) and opens chat UI in browser.

set -euo pipefail
PACK_DIR="${AIXMOS_PACK_DIR:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"
HOST_DIR="$HOME/.aixmos"

if [ ! -f "$HOST_DIR/state.json" ]; then
  echo "❌ AIXMOS isn't installed yet. Run option 1 first."
  exit 1
fi

# Start Ollama if not up
if ! curl -s --max-time 1 http://127.0.0.1:11434/api/tags >/dev/null 2>&1; then
  echo "Starting Ollama..."
  nohup ollama serve >"$PACK_DIR/logs/ollama.out" 2>&1 &
  for i in {1..10}; do
    sleep 1
    curl -s --max-time 1 http://127.0.0.1:11434/api/tags >/dev/null 2>&1 && break
  done
fi
echo "✅ Ollama on :11434"

# Try Open WebUI if installed; otherwise fall back to native ollama chat
OWUI_DIR="$PACK_DIR/_runtime/open-webui"
if [ -f "$OWUI_DIR/.venv/bin/open-webui" ]; then
  echo "Starting Open WebUI on :8080..."
  nohup "$OWUI_DIR/.venv/bin/open-webui" serve --host 127.0.0.1 --port 8080 \
    >"$PACK_DIR/logs/owui.out" 2>&1 &
  sleep 3
  open "http://127.0.0.1:8080" 2>/dev/null || true
  echo "✅ Open WebUI: http://127.0.0.1:8080"
else
  echo "⚠  Open WebUI not bundled on this drive. Use option 5 (Chat in terminal)."
  echo "   To install OWUI later: bash $PACK_DIR/_starter/install-openwebui.sh"
fi

echo ""
echo "AIXMOS is running. To stop: choose option 3 from the menu."
