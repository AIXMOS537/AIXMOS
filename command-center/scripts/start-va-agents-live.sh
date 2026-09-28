#!/usr/bin/env bash
# Start AIXMOS agents for VA support: Ollama, lead drafts, MOOSE/BRAIN/CHUMMO terminals, optional GHL webhook.
set -euo pipefail

BLUE='\033[0;34m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BOLD='\033[1m'
RESET='\033[0m'

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
export AI_PROVIDER="${AI_PROVIDER:-auto}"
export OLLAMA_BASE_URL="${OLLAMA_BASE_URL:-http://127.0.0.1:11434}"
LIMIT="${1:-15}"

echo ""
echo -e "${BLUE}${BOLD}  VA Agents — live stack${RESET}"
echo ""

# Ollama
if command -v ollama &>/dev/null; then
  if ! curl -sf "${OLLAMA_BASE_URL}/api/tags" &>/dev/null; then
    echo -e "  ${YELLOW}Starting Ollama…${RESET}"
    (ollama serve >/dev/null 2>&1 &)
    sleep 2
  fi
  echo -e "  ${GREEN}✓ Ollama${RESET}"
else
  echo -e "  ${YELLOW}! Ollama not installed — use Anthropic key or brew install ollama${RESET}"
fi

# Node deps
for dir in "$ROOT/ops/chummo-stack" "$ROOT/ops/files"; do
  if [ -f "$dir/package.json" ] && [ ! -d "$dir/node_modules" ]; then
    (cd "$dir" && npm install --silent)
  fi
done

# 1) CHUMMO drafts + MOOSE client pathway (Maria-style action plans)
echo ""
echo -e "${BOLD}  1. CHUMMO + MOOSE — message + full client pathway per lead${RESET}"
cd "$ROOT/ops/chummo-stack"
node chummo-draft-leads.js --limit "$LIMIT" || {
  echo -e "  ${YELLOW}Lead batch failed — check TMMT MANAGEMENT/tmmt-os/.env.local Supabase keys${RESET}"
}

DRAFT_DIR="$ROOT/TMMT MANAGEMENT/OPERATIONS/VA_LEAD_DRAFTS/$(date +%Y-%m-%d)"
if [ -d "$DRAFT_DIR" ]; then
  echo -e "  ${GREEN}✓ Drafts:${RESET} $DRAFT_DIR"
  open "$DRAFT_DIR" 2>/dev/null || true
fi

# 2) GHL webhook (optional — LEXAR USB copy)
WEBHOOK_ROOT="$HOME/FlashDrive-Sync/LEXAR-AIX-HOME-PC/AIXMOS-AGENTS/membership/services/chummo-ghl-webhook"
if [ -f "$WEBHOOK_ROOT/server.js" ]; then
  if lsof -i :4099 -sTCP:LISTEN -t &>/dev/null; then
    echo -e "  ${GREEN}✓ CHUMMO GHL webhook already on :4099${RESET}"
  elif [ -n "${GHL_WEBHOOK_SHARED_SECRET:-}" ]; then
    echo -e "  Starting GHL webhook on :4099…"
    (cd "$WEBHOOK_ROOT" && PORT=4099 node server.js >>"$ROOT/.logs/chummo-ghl-webhook.log" 2>&1 &)
  else
    echo -e "  ${YELLOW}GHL webhook: set GHL_WEBHOOK_SHARED_SECRET in environment to auto-start${RESET}"
  fi
fi

# 3) Open interactive agents in Terminal (VA owner can paste drafts from folder)
open_agent_terminal() {
  local title="$1"
  local cmd="$2"
  local escaped
  escaped=$(printf '%s' "$cmd" | sed 's/\\/\\\\/g; s/"/\\"/g')
  osascript -e "tell application \"Terminal\" to do script \"${escaped}\"" 2>/dev/null || true
}

echo ""
echo -e "${BOLD}  2. Live terminal agents (for managers)${RESET}"
ENV_EXPORT="export AI_PROVIDER=${AI_PROVIDER} OLLAMA_BASE_URL=${OLLAMA_BASE_URL}"
open_agent_terminal "CHUMMO" "${ENV_EXPORT}; cd \"$ROOT/ops/chummo-stack\" && node chummo.js"
open_agent_terminal "MOOSE" "${ENV_EXPORT}; cd \"$ROOT/ops/files\" && node moose.js"
open_agent_terminal "BRAIN" "${ENV_EXPORT}; cd \"$ROOT/ops/files\" && node brain.js"

# 4) TMMT dev / portal if not running
if ! lsof -i :3000 -sTCP:LISTEN -t &>/dev/null; then
  (cd "$ROOT/ops/chummo-stack" && node serve.js >>"$ROOT/.logs/chummo-serve.log" 2>&1 &)
fi

echo ""
echo -e "${BOLD}  VA handoff${RESET}"
echo "  • Pipeline & Sales VA → VA_LEAD_DRAFTS/$(date +%Y-%m-%d)/INDEX.md"
echo "  • Fleet VA → TMMT OS cases + TANK checklists"
echo "  • Data VA → weekly KPIs in /team/performance"
echo "  • Full runbook → TMMT MANAGEMENT/OPERATIONS/VA_AGENT_RUNBOOK.md"
echo ""
osascript -e "tell application \"Cursor\" to open POSIX file \"$ROOT/TMMT MANAGEMENT/OPERATIONS/VA_AGENT_RUNBOOK.md\"" 2>/dev/null || true
echo ""
