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

# ── Check API Key ──────────────────────────────────────
if [ -z "$ANTHROPIC_API_KEY" ]; then
  echo ""
  echo -e "  ${YELLOW}No API key found.${RESET}"
  echo "  Get yours at: https://console.anthropic.com"
  echo ""
  read -p "  Paste your Anthropic API key: " API_KEY
  if [ -z "$API_KEY" ]; then
    echo -e "\n  ${RED}No key entered. Exiting.${RESET}\n"
    exit 1
  fi
  export ANTHROPIC_API_KEY="$API_KEY"
  read -p "  Save permanently to this Mac? (y/n): " SAVE
  if [[ "$SAVE" =~ ^[Yy]$ ]]; then
    echo "export ANTHROPIC_API_KEY=$API_KEY" >> ~/.zshrc
    echo -e "  ${GREEN}✓ Saved${RESET}"
  fi
fi

echo -e "  ${GREEN}✓ API key ready${RESET}"
echo ""
echo -e "  ${BLUE}Launching MOOSE...${RESET}"
echo ""
sleep 0.3

node "$SCRIPT_DIR/moose.js"
