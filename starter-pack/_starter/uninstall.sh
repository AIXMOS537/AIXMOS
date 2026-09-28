#!/usr/bin/env bash
# AIXMOS — remove host footprint (models + state). USB stays untouched.
set -uo pipefail

HOST_DIR="$HOME/.aixmos"

echo "This will remove:"
echo "  - $HOST_DIR (models + state, ~5 GB)"
echo "  - tmmt-brain Ollama model"
echo ""
echo "It will NOT remove:"
echo "  - Ollama itself (uninstall with: brew uninstall ollama)"
echo "  - The USB drive (you can keep using it)"
echo ""
printf "Proceed? (y/N): "
read -r ans
[[ "$ans" =~ ^[Yy]$ ]] || { echo "Cancelled."; exit 0; }

if command -v ollama >/dev/null 2>&1; then
  ollama rm tmmt-brain 2>/dev/null && echo "✅ Removed tmmt-brain model" || true
fi

if [ -d "$HOST_DIR" ]; then
  rm -rf "$HOST_DIR"
  echo "✅ Removed $HOST_DIR"
fi

echo "Done."
