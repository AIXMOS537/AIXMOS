#!/usr/bin/env bash
# AIXMOS Carry Device Bootstrap — carry Mac (Apple Silicon). Sets up the never-dark roaming
# brain: Tailscale + Ollama + a local model (offline) + the client + env. No secrets stored here.
# Run:  bash bootstrap-mac.sh
set -u
echo "== AIXMOS carry-Mac bootstrap =="

# 1) Homebrew (if missing)
command -v brew >/dev/null 2>&1 || { echo "Installing Homebrew..."; /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"; }

# 2) Tailscale (reach home hub + brain PC when online)
command -v tailscale >/dev/null 2>&1 || brew install --cask tailscale || brew install tailscale
echo "Then run 'tailscale up' once and sign into the AIXMOS537 tailnet."

# 3) Ollama + a local model (your OFFLINE brain). M-series can run 8B.
command -v ollama >/dev/null 2>&1 || brew install ollama
( ollama serve >/dev/null 2>&1 & ) ; sleep 2
echo "Pulling local model (offline-capable once done)..."
ollama pull llama3.1:8b   # carry Mac can handle 8B; use llama3.2:3b if you want it lighter

# 4) Lay down client + offline docs
AIX="$HOME/AIXMOS"; mkdir -p "$AIX/KnowledgeBase"
cp "$(dirname "$0")/aixmos-anywhere.sh" "$AIX/aixmos.sh"; chmod +x "$AIX/aixmos.sh"
echo "Put your TMMT_Knowledge_Base (SOPs) in $AIX/KnowledgeBase for OFFLINE reference."

# 5) Shell env — secret PROMPTED, kept out of plaintext rc where possible
RC="$HOME/.zshrc"
if ! grep -q "AIXMOS_GATEWAY" "$RC" 2>/dev/null; then
  read -r -s -p "Paste your CARRY gateway secret (from 1Password): " SEC; echo
  {
    echo ""; echo "# AIXMOS roaming (added by bootstrap-mac.sh)"
    echo 'export AIXMOS_GATEWAY="https://aixmos-gateway.aixmos.workers.dev"'
    echo "export AIXMOS_SECRET=\"$SEC\""
    echo 'export AIXMOS_BRAIN="http://<brain-pc-tailscale-ip>:11434"'
    echo 'export AIXMOS_LOCAL="http://localhost:11434"'
    echo 'export AIXMOS_LOCALMDL="llama3.1:8b"'
  } >> "$RC"
  echo "Added AIXMOS env to ~/.zshrc"
fi

echo ""
echo "DONE. Open a new terminal, then:"
echo '   tailscale up'
echo '   bash ~/AIXMOS/aixmos.sh "AIXMOS online?"   # works online OR fully offline'
echo "SECURITY: turn on FileVault (System Settings > Privacy & Security > FileVault)."
