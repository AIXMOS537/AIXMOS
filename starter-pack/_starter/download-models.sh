#!/usr/bin/env bash
# Download/refresh all models from the Ollama registry.
# Run this ONCE on a machine with internet to populate the host's Ollama store.
# After that, the USB ships and the customer doesn't need internet.

set -euo pipefail
PACK_DIR="${AIXMOS_PACK_DIR:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"

if ! command -v ollama >/dev/null 2>&1; then
  echo "❌ Ollama not installed. Install first: brew install ollama"
  exit 1
fi

# Start Ollama if not running
if ! curl -s --max-time 1 http://127.0.0.1:11434/api/tags >/dev/null 2>&1; then
  nohup ollama serve >/dev/null 2>&1 &
  sleep 3
fi

echo "=== Downloading AIXMOS model set ==="
TAGS=$(python3 -c "import json; m=json.load(open('$PACK_DIR/_models/MANIFEST.json')); print(' '.join(x['ollama_tag'] for x in m['models']))")
for tag in $TAGS; do
  echo ""
  echo "→ ollama pull $tag"
  ollama pull "$tag"
done

# Build the tmmt-brain persona on top of llama3.2:3b
if [ -f "$PACK_DIR/_brain/Modelfile.tmmt-brain" ]; then
  echo ""
  echo "→ Building tmmt-brain (Operations Brain persona)..."
  ollama create tmmt-brain -f "$PACK_DIR/_brain/Modelfile.tmmt-brain"
fi

echo ""
echo "✅ Done. All models present on host."
echo ""
echo "Optional next step: export the model weights to the USB drive for offline distribution:"
echo "  bash $PACK_DIR/_starter/export-models-to-usb.sh"
