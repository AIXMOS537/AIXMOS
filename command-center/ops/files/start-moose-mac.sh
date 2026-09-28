#!/bin/bash

# ═══════════════════════════════════════════════════════
# AIXMOS MOOSE — MAC LAUNCHER
# Double-click or run: bash start-moose-mac.sh
# ═══════════════════════════════════════════════════════

BLUE='\033[0;34m'
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BOLD='\033[1m'
RESET='\033[0m'

clear

echo ""
echo -e "${BLUE}${BOLD}  ╔══════════════════════════════════════╗${RESET}"
echo -e "${BLUE}${BOLD}  ║   AIXMOS · MOOSE AGENT               ║${RESET}"
echo -e "${BLUE}${BOLD}  ║   Relentless. Proactive. Executing.  ║${RESET}"
echo -e "${BLUE}${BOLD}  ╚══════════════════════════════════════╝${RESET}"
echo ""

# ── Check Node.js ──────────────────────────────────────
if ! command -v node &> /dev/null; then
  echo -e "${RED}  Node.js not found.${RESET}"
  echo ""
  echo "  Install it:"
  echo -e "  ${YELLOW}Option A:${RESET} https://nodejs.org"
  echo -e "  ${YELLOW}Option B:${RESET} brew install node"
  echo ""
  read -p "  Press Enter to exit..."
  exit 1
fi

echo -e "  ${GREEN}✓ Node.js:${RESET} $(node --version)"

# ── Check node_modules ─────────────────────────────────
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

if [ ! -d "node_modules" ]; then
  echo ""
  echo -e "  ${YELLOW}Installing dependencies...${RESET}"
  npm install --silent
  echo -e "  ${GREEN}✓ Ready${RESET}"
fi

# ── AI — Ollama first ──────────────────────────────────
export AI_PROVIDER="${AI_PROVIDER:-auto}"
export OLLAMA_BASE_URL="${OLLAMA_BASE_URL:-http://127.0.0.1:11434}"

if curl -sf "${OLLAMA_BASE_URL}/api/tags" &>/dev/null; then
  echo -e "  ${GREEN}✓ Ollama ready${RESET}"
elif [ -z "$ANTHROPIC_API_KEY" ]; then
  echo -e "  ${YELLOW}Start Ollama (ollama serve) or set ANTHROPIC_API_KEY${RESET}"
  read -p "  Paste Anthropic API key (or Enter to exit): " API_KEY
  [ -z "$API_KEY" ] && exit 1
  export ANTHROPIC_API_KEY="$API_KEY"
else
  echo -e "  ${GREEN}✓ Cloud fallback available${RESET}"
fi
echo ""
echo -e "  ${BLUE}Launching MOOSE...${RESET}"
echo ""
sleep 0.3

node "$SCRIPT_DIR/moose.js"
