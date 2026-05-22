#!/bin/bash
cd "$(dirname "${BASH_SOURCE[0]}")"
clear
echo ""
echo "  ============================================================"
echo "   AIXMOS - OFFLINE MODE SETUP (Mac)"
echo "   Installs Ollama + a local model so the agents work offline."
echo "  ============================================================"
echo ""
echo "  QUALITY NOTE:"
echo "    Local models are noticeably weaker than Claude for"
echo "    voice/brand work (CHUMMO drafts, customer messages)."
echo "    Analytical agents (BOB, STICKS, VISION) hold up better."
echo ""
read -p "  Press Enter to continue, Ctrl+C to abort..."

# Ollama install
echo ""
echo "  [1/5] Checking Ollama..."
if ! command -v ollama >/dev/null 2>&1; then
  if command -v brew >/dev/null 2>&1; then
    echo "  Installing Ollama via Homebrew..."
    brew install ollama
  else
    echo "  Install Homebrew first:"
    echo "    /bin/bash -c \"\$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)\""
    echo "  Or download Ollama directly: https://ollama.com/download/mac"
    exit 1
  fi
fi
echo "  Ollama detected."

echo ""
echo "  [2/5] Starting Ollama service..."
# Mac launchd-managed if installed via brew services
if brew services list 2>/dev/null | grep -q ollama; then
  brew services start ollama || true
else
  # Foreground process in background
  nohup ollama serve >/dev/null 2>&1 &
fi
sleep 3
echo "  Service kicked off."

echo ""
echo "  [3/5] Pulling Phi-3 Mini (~2.3 GB)..."
ollama pull phi3:mini
echo ""

echo "  [4/5] Optional: pull Llama 3.1 8B (~4.7 GB, better quality)"
read -p "  Pull Llama 3.1 8B now? (y/n): " PULL_LLAMA
MODEL="phi3:mini"
if [[ "$PULL_LLAMA" =~ ^[Yy]$ ]]; then
  if ollama pull llama3.1:8b; then
    MODEL="llama3.1:8b"
    echo "  Llama 3.1 8B ready."
  else
    echo "  Llama pull failed. Falling back to phi3:mini."
  fi
fi

echo ""
echo "  [5/5] Configuring AIXMOS environment..."
for profile in ~/.zshrc ~/.bash_profile ~/.bashrc; do
  if [ -f "$profile" ]; then
    grep -v "AIXMOS_LLM_BACKEND" "$profile" | grep -v "OLLAMA_MODEL" | grep -v "OLLAMA_HOST" > "$profile.tmp" && mv "$profile.tmp" "$profile"
    {
      echo "export AIXMOS_LLM_BACKEND=ollama"
      echo "export OLLAMA_HOST=http://localhost:11434"
      echo "export OLLAMA_MODEL=$MODEL"
    } >> "$profile"
  fi
done
echo "  AIXMOS_LLM_BACKEND=ollama"
echo "  OLLAMA_MODEL=$MODEL"
echo ""
echo "  ============================================================"
echo "   OFFLINE MODE READY."
echo "   Open a NEW terminal, then test with:"
echo "     cd ~/AIXMOS  (or this USB folder)"
echo "     node test-all-agents.js --live"
echo "   Switch back to Claude any time:"
echo "     export AIXMOS_LLM_BACKEND=claude"
echo "  ============================================================"
echo ""
read -p "  Press Enter to close..."
