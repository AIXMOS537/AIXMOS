#!/usr/bin/env bash
# Install Open WebUI into the USB pack's _runtime/open-webui/.venv
# Requires: python3.11+ and ~500 MB free on the USB
# Run this ONCE on your control Mac, then the USB is portable.

set -euo pipefail
PACK_DIR="${AIXMOS_PACK_DIR:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"
OWUI_DIR="$PACK_DIR/_runtime/open-webui"

mkdir -p "$OWUI_DIR"
cd "$OWUI_DIR"

if ! command -v python3 >/dev/null 2>&1; then
  echo "❌ python3 missing. Install Python 3.11+ first."
  exit 1
fi

PYV=$(python3 -c 'import sys; print(f"{sys.version_info[0]}.{sys.version_info[1]}")')
echo "Python: $PYV"

python3 -m venv .venv
. .venv/bin/activate
pip install --upgrade pip
pip install open-webui

echo ""
echo "✅ Open WebUI installed at $OWUI_DIR/.venv/"
echo "   Size: $(du -sh "$OWUI_DIR/.venv" | awk '{print $1}')"
echo "   Start: bash $PACK_DIR/_starter/start.sh"
