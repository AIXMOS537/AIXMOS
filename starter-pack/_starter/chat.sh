#!/usr/bin/env bash
# AIXMOS — terminal chat (no browser needed)
set -uo pipefail

if ! curl -s --max-time 1 http://127.0.0.1:11434/api/tags >/dev/null 2>&1; then
  echo "Ollama isn't running. Starting it..."
  nohup ollama serve >/dev/null 2>&1 &
  sleep 2
fi

# Prefer tmmt-brain (Ops Brain persona); fall back to llama3.2:3b
MODEL="tmmt-brain"
if ! ollama list 2>/dev/null | grep -q "^${MODEL}"; then
  MODEL="llama3.2:3b"
  echo "  (tmmt-brain not built — using ${MODEL})"
fi

echo "Chat with: ${MODEL}"
echo "Type /bye to exit."
echo "---"
ollama run "$MODEL"
