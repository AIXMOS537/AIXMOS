#!/usr/bin/env bash
# Talk to AIXMOS from any Mac/PC terminal.
# Setup once:   export AIXMOS_GATEWAY="https://your.workers.dev"
#               export AIXMOS_SECRET="your role secret"
# Use:          bash aixmos.sh "draft a follow-up to a Turo customer"

: "${AIXMOS_GATEWAY:?Set AIXMOS_GATEWAY first:  export AIXMOS_GATEWAY=...}"
: "${AIXMOS_SECRET:?Set AIXMOS_SECRET first:  export AIXMOS_SECRET=...}"
[ -n "$*" ] || { echo 'Usage: bash aixmos.sh "your prompt"'; exit 1; }

BODY=$(node -e "process.stdout.write(JSON.stringify({messages:[{role:'user',content:process.argv[1]}]}))" "$*")

curl -s -X POST "$AIXMOS_GATEWAY" \
  -H "x-aixmos-auth: $AIXMOS_SECRET" \
  -H "content-type: application/json" \
  -d "$BODY" \
| node -e "let d='';process.stdin.on('data',c=>d+=c).on('end',()=>{try{const j=JSON.parse(d);console.log((j.content&&j.content[0]&&j.content[0].text)||j.error||d)}catch(e){console.log(d)}})"
