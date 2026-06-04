#!/bin/bash
# AIX Command Center — Mac launcher (Ollama-first)
set -euo pipefail

BLUE='\033[0;34m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BOLD='\033[1m'
RESET='\033[0m'

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
export AI_PROVIDER="${AI_PROVIDER:-auto}"
export OLLAMA_BASE_URL="${OLLAMA_BASE_URL:-http://127.0.0.1:11434}"

[ -t 1 ] && clear
echo ""
echo -e "${BLUE}${BOLD}  AIX Command Center — full stack (Ollama first)${RESET}"
echo ""

# ── Ollama ─────────────────────────────────────────────
if ! command -v ollama &>/dev/null; then
  echo -e "${YELLOW}  Ollama not installed. Install: brew install ollama${RESET}"
else
  if ! curl -sf "${OLLAMA_BASE_URL}/api/tags" &>/dev/null; then
    echo -e "${YELLOW}  Starting Ollama...${RESET}"
    (ollama serve >/dev/null 2>&1 &)
    sleep 2
  fi
  if curl -sf "${OLLAMA_BASE_URL}/api/tags" &>/dev/null; then
    MODEL=$(curl -s "${OLLAMA_BASE_URL}/api/tags" | node -e "let d='';process.stdin.on('data',c=>d+=c);process.stdin.on('end',()=>{try{const j=JSON.parse(d);console.log(j.models?.[0]?.name||'')}catch{}})" 2>/dev/null || true)
    echo -e "  ${GREEN}✓ Ollama${RESET} @ ${OLLAMA_BASE_URL}${MODEL:+ — model: $MODEL}"
  else
    echo -e "${YELLOW}  Ollama not reachable at ${OLLAMA_BASE_URL}${RESET}"
  fi
fi

# ── Node deps ──────────────────────────────────────────
for dir in "$ROOT/ops/chummo-stack" "$ROOT/ops/files"; do
  if [ -f "$dir/package.json" ] && [ ! -d "$dir/node_modules" ]; then
    echo -e "  Installing deps in $(basename "$dir")..."
    (cd "$dir" && npm install --silent)
  fi
done

# Also install llm-client deps in ops/files if needed
if [ ! -d "$ROOT/ops/files/node_modules/@anthropic-ai" ]; then
  (cd "$ROOT/ops/files" && npm install --silent 2>/dev/null || npm install @anthropic-ai/sdk --silent)
fi

# ── AI status ──────────────────────────────────────────
STATUS=$(cd "$ROOT/ops/files" && node -e "
  const { getAiStatus } = require('./llm-client');
  getAiStatus().then(s => {
    console.log(JSON.stringify(s));
  });
" 2>/dev/null || echo '{}')

ACTIVE=$(echo "$STATUS" | node -e "let d='';process.stdin.on('data',c=>d+=c);process.stdin.on('end',()=>{try{console.log(JSON.parse(d).active||'none')}catch{console.log('none')}})" 2>/dev/null || echo "none")
echo -e "  ${GREEN}✓ AI provider:${RESET} ${ACTIVE} (AI_PROVIDER=${AI_PROVIDER})"

# ── Web: CHUMMO portal (3000) ──────────────────────────
CHUMMO_PID=""
if lsof -i :3000 -sTCP:LISTEN -t &>/dev/null; then
  echo -e "  ${YELLOW}Port 3000 in use — skipping serve.js${RESET}"
else
  echo -e "  Starting portal → http://localhost:3000"
  (cd "$ROOT/ops/chummo-stack" && node serve.js >>"$ROOT/.logs/chummo-serve.log" 2>&1 &)
  CHUMMO_PID=$!
  sleep 1
fi

# ── Web: all-in-one platform (3001) ────────────────────
mkdir -p "$ROOT/.logs"
if lsof -i :3001 -sTCP:LISTEN -t &>/dev/null; then
  echo -e "  ${YELLOW}Port 3001 in use — skipping all_in_one_platform${RESET}"
elif [ -d "$ROOT/all_in_one_platform" ]; then
  if [ ! -d "$ROOT/all_in_one_platform/node_modules" ]; then
    echo "  Installing all_in_one_platform..."
    (cd "$ROOT/all_in_one_platform" && npm install --silent)
  fi
  echo -e "  Starting OS shells → http://localhost:3001"
  (cd "$ROOT/all_in_one_platform" && PORT=3001 npm run dev >>"$ROOT/.logs/all-in-one.log" 2>&1 &)
  sleep 2
fi

# ── AIXMOSXTMMT-OPS doctor (optional) ──────────────────
if [ -d "$ROOT/AIXMOSXTMMT-OPS" ] && [ -f "$ROOT/AIXMOSXTMMT-OPS/package.json" ]; then
  if [ -f "$ROOT/AIXMOSXTMMT-OPS/.env" ]; then
    (cd "$ROOT/AIXMOSXTMMT-OPS" && npm run doctor 2>/dev/null) || true
  else
    echo -e "  ${YELLOW}AIXMOSXTMMT-OPS: copy .env.example → .env for n8n/docker stack${RESET}"
  fi
fi

echo ""
echo -e "${BOLD}  Services${RESET}"
echo "  Portal + landing   http://localhost:3000"
echo "  All-in-one OS      http://localhost:3001"
echo ""
echo -e "${BOLD}  Terminal agents (Ollama first)${RESET}"
echo "  CHUMMO   cd \"$ROOT/ops/chummo-stack\" && node chummo.js"
echo "  MOOSE    cd \"$ROOT/ops/files\" && node moose.js"
echo "  BRAIN    cd \"$ROOT/ops/files\" && node brain.js"
echo ""
echo -e "${BOLD}  Logs${RESET}  $ROOT/.logs/"
echo ""
if [ -t 0 ]; then
  read -p "  Launch CHUMMO agent now? (y/n): " LAUNCH
  if [[ "$LAUNCH" =~ ^[Yy]$ ]]; then
    cd "$ROOT/ops/chummo-stack"
    exec node chummo.js
  fi
fi

echo ""
echo "  Background servers keep running. Stop with: lsof -ti :3000,:3001 | xargs kill"
echo ""
