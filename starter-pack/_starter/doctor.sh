#!/usr/bin/env bash
# AIXMOS Starter Pack — health check (Mac/Linux)
# Run when something feels off. Prints what's wrong + how to fix it.

PACK_DIR="${AIXMOS_PACK_DIR:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"
HOST_DIR="$HOME/.aixmos"

pass() { echo "  ✅ $*"; }
fail() { echo "  ❌ $*"; }
warn() { echo "  ⚠  $*"; }

echo ""
echo "=== AIXMOS Doctor ==="
echo ""

# 1. Install state
if [ -f "$HOST_DIR/state.json" ]; then
  pass "Install state present at $HOST_DIR/state.json"
else
  fail "Not installed. Run LAUNCH option 1."
fi

# 2. RAM
RAM_GB=$(sysctl -n hw.memsize 2>/dev/null | awk '{printf "%.0f", $1/1024/1024/1024}' || echo 0)
[ "$RAM_GB" -ge 8 ] && pass "RAM: ${RAM_GB} GB" || fail "RAM ${RAM_GB} GB (need 8+)"

# 3. Disk
FREE_GB=$(df -g "$HOME" | awk 'NR==2 {print $4}')
[ "$FREE_GB" -ge 5 ] && pass "Disk free: ${FREE_GB} GB" || fail "Disk free ${FREE_GB} GB (need 5+)"

# 4. Ollama binary
if command -v ollama >/dev/null 2>&1; then
  pass "Ollama installed: $(ollama --version 2>&1 | head -1)"
else
  fail "Ollama missing. Install: brew install ollama"
fi

# 5. Ollama service
if curl -s --max-time 1 http://127.0.0.1:11434/api/tags >/dev/null 2>&1; then
  pass "Ollama service running on :11434"
  TAGS=$(curl -s http://127.0.0.1:11434/api/tags | python3 -c "import json,sys; print(', '.join(m['name'] for m in json.load(sys.stdin)['models']))" 2>/dev/null || echo "?")
  echo "      Models: $TAGS"
else
  warn "Ollama not running. Start with: ollama serve &"
fi

# 6. tmmt-brain model
if ollama list 2>/dev/null | grep -q "^tmmt-brain"; then
  pass "tmmt-brain model present"
else
  warn "tmmt-brain not built. Run LAUNCH option 1 again."
fi

# 7. Ports
for port in 11434 8080 7780; do
  if lsof -i ":${port}" -sTCP:LISTEN >/dev/null 2>&1; then
    pass "Port ${port} listening"
  else
    warn "Port ${port} not in use"
  fi
done

# 8. Open WebUI
if [ -f "$PACK_DIR/_runtime/open-webui/.venv/bin/open-webui" ]; then
  pass "Open WebUI bundled"
else
  warn "Open WebUI NOT bundled on this drive (chat works in terminal via option 5)"
fi

# 9. USB drive write check
if [ -w "$PACK_DIR" ]; then
  pass "Pack directory writable (logs will save)"
else
  warn "Pack dir read-only (USB filesystem) — logs saving to $HOME/.aixmos/logs/ instead"
fi

echo ""
echo "Done. Copy this output if asking for help."
