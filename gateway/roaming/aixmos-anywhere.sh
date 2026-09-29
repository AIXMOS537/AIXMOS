#!/usr/bin/env bash
# AIXMOS — never-dark client for the road (macOS/Linux).
# Tries: cloud gateway -> home brain PC (Tailscale) -> LOCAL Ollama (offline). First to answer wins.
# Usage:  bash aixmos-anywhere.sh "draft a follow-up to a Turo guest"
# Config (env): AIXMOS_GATEWAY, AIXMOS_SECRET (carry), AIXMOS_BRAIN, AIXMOS_LOCAL, AIXMOS_LOCALMDL
set -u
TEXT="$*"; [ -n "$TEXT" ] || { echo 'Usage: aixmos-anywhere.sh "your prompt"'; exit 1; }
GATEWAY="${AIXMOS_GATEWAY:-}"; SECRET="${AIXMOS_SECRET:-}"
BRAIN="${AIXMOS_BRAIN:?set AIXMOS_BRAIN to your Ollama host, e.g. http://<brain-pc>:11434}"
LOCAL="${AIXMOS_LOCAL:-http://localhost:11434}"
LMODEL="${AIXMOS_LOCALMDL:-llama3.1:8b}"; BMODEL="${AIXMOS_BRAINMDL:-tmmt-brain:latest}"

gw_body(){ python3 -c "import json,sys; print(json.dumps({'prompt':sys.argv[1],'max_tokens':800}))" "$TEXT"; }
chat_body(){ python3 -c "import json,sys; print(json.dumps({'model':sys.argv[1],'stream':False,'messages':[{'role':'user','content':sys.argv[2]}]}))" "$1" "$TEXT"; }
gw_pick(){ python3 -c "import json,sys
try:
 j=json.load(sys.stdin)
 if j.get('error'): print('')
 elif j.get('content'): print(j['content'][0]['text'])
 else: print(j.get('text',''))
except: print('')"; }
chat_pick(){ python3 -c "import json,sys
try: print(json.load(sys.stdin).get('message',{}).get('content',''))
except: print('')"; }

# 1) cloud gateway
if [ -n "$GATEWAY" ] && [ -n "$SECRET" ]; then
  OUT=$(curl -s --max-time 25 -X POST "$GATEWAY" -H "x-aixmos-auth: $SECRET" -H "content-type: application/json" -d "$(gw_body)" | gw_pick)
  [ -n "$OUT" ] && { echo "[lane: cloud gateway]"; echo "$OUT"; exit 0; }
fi
# 2) home brain over Tailscale
OUT=$(curl -s --max-time 60 -X POST "$BRAIN/api/chat" -H "content-type: application/json" -d "$(chat_body "$BMODEL")" | chat_pick)
[ -n "$OUT" ] && { echo "[lane: home brain via Tailscale]"; echo "$OUT"; exit 0; }
# 3) LOCAL offline brain
OUT=$(curl -s --max-time 60 -X POST "$LOCAL/api/chat" -H "content-type: application/json" -d "$(chat_body "$LMODEL")" | chat_pick)
[ -n "$OUT" ] && { echo "[lane: LOCAL offline brain]"; echo "$OUT"; exit 0; }
echo "AIXMOS offline and no local model responding. Try: ollama serve  (and ollama pull $LMODEL)"; exit 1
