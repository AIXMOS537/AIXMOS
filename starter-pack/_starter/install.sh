#!/usr/bin/env bash
# AIXMOS Starter Pack — Mac/Linux installer
# - Verifies Ollama on the host (installs via brew if missing on Mac)
# - Copies model weights from USB to ~/.aixmos/models if present
# - Pulls/builds the tmmt-brain Ollama model
# - Records state to ~/.aixmos/state.json

set -euo pipefail

PACK_DIR="${AIXMOS_PACK_DIR:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"
HOST_DIR="$HOME/.aixmos"
LOG="$PACK_DIR/logs/install-$(date +%Y%m%d-%H%M%S).log"
mkdir -p "$HOST_DIR/models" "$PACK_DIR/logs"

log() { echo "[$(date +%H:%M:%S)] $*" | tee -a "$LOG"; }

log "=== AIXMOS Starter Pack — install ==="
log "Pack dir: $PACK_DIR"
log "Host dir: $HOST_DIR"

# ---- 1. RAM precheck -------------------------------------------------------
RAM_GB=$(sysctl -n hw.memsize 2>/dev/null | awk '{printf "%.0f", $1/1024/1024/1024}' || echo 0)
if [ "$RAM_GB" -lt 8 ]; then
  log "❌ Detected ${RAM_GB} GB RAM. AIXMOS needs 8 GB minimum."
  log "   Aborting."
  exit 1
fi
log "✅ RAM: ${RAM_GB} GB"

# ---- 2. Disk precheck ------------------------------------------------------
FREE_GB=$(df -g "$HOME" | awk 'NR==2 {print $4}')
if [ "$FREE_GB" -lt 10 ]; then
  log "❌ Detected ${FREE_GB} GB free in $HOME. Need at least 10 GB for models + workspace."
  exit 1
fi
log "✅ Disk free: ${FREE_GB} GB"

# ---- 3. Ollama ------------------------------------------------------------
if ! command -v ollama >/dev/null 2>&1; then
  log "Ollama not found on host."
  if command -v brew >/dev/null 2>&1; then
    log "Installing via Homebrew..."
    brew install ollama 2>&1 | tee -a "$LOG"
  else
    log "Homebrew not present. Please install Ollama from https://ollama.com/download"
    log "Then re-run this script."
    exit 1
  fi
else
  log "✅ Ollama present: $(ollama --version 2>&1 | head -1)"
fi

# Start Ollama service if not running
if ! curl -s --max-time 1 http://127.0.0.1:11434/api/tags >/dev/null 2>&1; then
  log "Starting Ollama service..."
  nohup ollama serve >"$PACK_DIR/logs/ollama.out" 2>&1 &
  sleep 3
fi

# ---- 4. Models ------------------------------------------------------------
if [ -d "$PACK_DIR/_models" ] && [ "$(ls -A "$PACK_DIR/_models" 2>/dev/null | grep -v MANIFEST | grep -v README || true)" ]; then
  log "Copying bundled model files from USB to host..."
  rsync -ah --progress "$PACK_DIR/_models/" "$HOST_DIR/models/" 2>&1 | tail -3 | tee -a "$LOG"
fi

# Always also ensure Ollama-pulled versions exist (registry-managed)
for tag in $(python3 -c "import json,sys; m=json.load(open('$PACK_DIR/_models/MANIFEST.json')); print(' '.join(x['ollama_tag'] for x in m['models']))" 2>/dev/null); do
  if ollama list 2>/dev/null | grep -q "^${tag}"; then
    log "✅ ${tag} already pulled"
  else
    log "Pulling ${tag} from Ollama registry..."
    ollama pull "$tag" 2>&1 | tail -3 | tee -a "$LOG" \
      || log "⚠  Pull failed for ${tag} — will retry on next install"
  fi
done

# ---- 5. Build tmmt-brain model from Modelfile -----------------------------
if [ -f "$PACK_DIR/_brain/Modelfile.tmmt-brain" ]; then
  log "Building tmmt-brain (Operations Brain persona)..."
  ollama create tmmt-brain -f "$PACK_DIR/_brain/Modelfile.tmmt-brain" 2>&1 | tail -5 | tee -a "$LOG" \
    || log "⚠  tmmt-brain build failed — generic models still work"
fi

# ---- 6. State file --------------------------------------------------------
cat > "$HOST_DIR/state.json" <<EOF
{
  "installed_at": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
  "pack_dir": "$PACK_DIR",
  "default_model": "tmmt-brain",
  "fallback_model": "qwen2.5:1.5b",
  "ports": { "ollama": 11434, "openwebui": 8080, "brain_dump": 7780 },
  "platform": "$(uname -s)",
  "ram_gb": $RAM_GB
}
EOF
log "✅ State written to $HOST_DIR/state.json"

log ""
log "=========================================="
log "✅ AIXMOS Starter Pack installed."
log "   Next: choose option 2 (Start AIXMOS) from the menu."
log "=========================================="
