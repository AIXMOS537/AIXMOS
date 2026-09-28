#!/usr/bin/env bash
# AIXMOS Starter Pack — clean shutdown (Mac/Linux)
set -uo pipefail

echo "Stopping AIXMOS services..."

# Open WebUI
pkill -f "open-webui serve" 2>/dev/null && echo "✅ Open WebUI stopped" || echo "  (Open WebUI not running)"

# Brain-dump agent
pkill -f "brain-dump-agent" 2>/dev/null && echo "✅ Brain-dump agent stopped" || echo "  (brain-dump not running)"

# Ollama serve (only stop if WE started it — we leave any pre-existing user Ollama alone)
if pgrep -f "ollama serve" >/dev/null; then
  echo "  Ollama is still running. Stop it manually with: pkill -f 'ollama serve'"
fi

echo "Done. Safe to unplug USB."
