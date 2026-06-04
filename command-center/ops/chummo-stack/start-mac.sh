#!/bin/bash

# ═══════════════════════════════════════════════════════
# AIXMOS CHUMMO — MAC LAUNCHER
# Double-click this file or run: bash start-mac.sh
# ═══════════════════════════════════════════════════════

# Colors
BLUE='\033[0;34m'
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BOLD='\033[1m'
RESET='\033[0m'

clear

echo ""
echo -e "${BLUE}${BOLD}  ╔══════════════════════════════════════╗${RESET}"
echo -e "${BLUE}${BOLD}  ║   AIXMOS · CHUMMO AGENT              ║${RESET}"
echo -e "${BLUE}${BOLD}  ║   For the people. By the people.     ║${RESET}"
echo -e "${BLUE}${BOLD}  ╚══════════════════════════════════════╝${RESET}"
echo ""

# ── STEP 1: Check Node.js ──────────────────────────────
if ! command -v node &> /dev/null; then
  echo -e "${RED}  Node.js not found.${RESET}"
  echo ""
  echo "  Install it two ways:"
  echo -e "  ${YELLOW}Option A:${RESET} Go to https://nodejs.org and download"
  echo -e "  ${YELLOW}Option B:${RESET} Run: brew install node"
  echo ""
  echo "  Then run this launcher again."
  echo ""
  read -p "  Press Enter to exit..."
  exit 1
fi

NODE_VERSION=$(node --version)
echo -e "  ${GREEN}✓ Node.js found:${RESET} $NODE_VERSION"

# ── STEP 2: Check node_modules ─────────────────────────
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

if [ ! -d "node_modules" ]; then
  echo ""
  echo -e "  ${YELLOW}First time setup — installing dependencies...${RESET}"
  npm install --silent
  echo -e "  ${GREEN}✓ Dependencies installed${RESET}"
fi

# ── STEP 3: AI — Ollama first, Anthropic optional ─────
export AI_PROVIDER="${AI_PROVIDER:-auto}"
export OLLAMA_BASE_URL="${OLLAMA_BASE_URL:-http://127.0.0.1:11434}"

if curl -sf "${OLLAMA_BASE_URL}/api/tags" &>/dev/null; then
  echo -e "  ${GREEN}✓ Ollama ready${RESET} (${OLLAMA_BASE_URL})"
else
  echo -e "  ${YELLOW}Ollama not running.${RESET} Start with: ollama serve"
fi

if [ -z "$ANTHROPIC_API_KEY" ]; then
  if ! curl -sf "${OLLAMA_BASE_URL}/api/tags" &>/dev/null; then
    echo ""
    echo -e "  ${YELLOW}No local Ollama and no Anthropic key.${RESET}"
    echo "  Option A: brew install ollama && ollama pull qwen2.5-coder:14b"
    echo "  Option B: paste Anthropic key at https://console.anthropic.com"
    echo ""
    read -p "  Paste Anthropic API key (or Enter to exit): " API_KEY
    if [ -z "$API_KEY" ]; then exit 1; fi
    export ANTHROPIC_API_KEY="$API_KEY"
  fi
else
  echo -e "  ${GREEN}✓ Anthropic key available (cloud fallback)${RESET}"
fi

# ── STEP 4: Launch CHUMMO ──────────────────────────────
echo ""
echo -e "  ${BLUE}Launching CHUMMO...${RESET}"
echo ""
sleep 0.5

node "$SCRIPT_DIR/chummo.js"
