#!/usr/bin/env bash
# AIXMOS — FREE lane for employees. Talks to the TMMT brain on your own hardware over Tailscale.
# $0 per use, private (never leaves your network). No gateway secret needed.
#
# Setup once (per employee device, after they're on the TMMT Tailscale network):
#   export AIXMOS_OLLAMA="http://<brain-pc-tailscale-ip>:11434"   # brain PC (brainiac-7) Tailscale IP
#   export AIXMOS_MODEL="tmmt-brain:latest"               # or llama3.1:8b
# Use:
#   bash aixmos-free.sh "summarize this customer message: ..."

OLLAMA="${AIXMOS_OLLAMA:?set AIXMOS_OLLAMA to your Ollama host, e.g. http://<brain-pc>:11434}"
MODEL="${AIXMOS_MODEL:-tmmt-brain:latest}"
[ -n "$*" ] || { echo 'Usage: bash aixmos-free.sh "your prompt"'; exit 1; }

BODY=$(node -e "process.stdout.write(JSON.stringify({model:process.argv[1],stream:false,messages:[{role:'user',content:process.argv[2]}]}))" "$MODEL" "$*")

curl -s --max-time 120 -X POST "$OLLAMA/api/chat" -H "content-type: application/json" -d "$BODY" \
| node -e "let d='';process.stdin.on('data',c=>d+=c).on('end',()=>{try{const j=JSON.parse(d);console.log((j.message&&j.message.content)||j.error||d)}catch(e){console.log('Could not reach the TMMT brain. Are you connected to the TMMT Tailscale network?')}})"
