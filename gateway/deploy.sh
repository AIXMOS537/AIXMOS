#!/usr/bin/env bash
set -e
echo "== AIXMOS Gateway deploy =="

command -v node >/dev/null 2>&1 || { echo "Node.js required. Install from nodejs.org, then re-run."; exit 1; }

# Log in to Cloudflare if needed (opens a browser).
npx wrangler whoami >/dev/null 2>&1 || npx wrangler login

# Create the KV memory store and write its id into wrangler.toml automatically.
if grep -q "PASTE_KV_ID" wrangler.toml; then
  echo "Creating KV memory store..."
  OUT=$(npx wrangler kv namespace create AIXMOS_KV) || {
    echo "Older wrangler? Run: npx wrangler kv:namespace create AIXMOS_KV"
    echo "then paste the id into wrangler.toml (replace PASTE_KV_ID) and run: npx wrangler deploy"
    exit 1; }
  echo "$OUT"
  ID=$(echo "$OUT" | grep -oE '[a-f0-9]{32}' | head -n1)
  [ -n "$ID" ] || { echo "Couldn't read KV id automatically — paste it into wrangler.toml, then: npx wrangler deploy"; exit 1; }
  node -e "const fs=require('fs');let t=fs.readFileSync('wrangler.toml','utf8');fs.writeFileSync('wrangler.toml',t.replace('PASTE_KV_ID','$ID'))"
  echo "Wired KV id into wrangler.toml."
fi

# Set secrets (input is hidden and never written to a file).
echo
echo "Set your secrets now. Minimum to start: ANTHROPIC_KEY and SECRET_PERSONAL."
echo "(Skip the others for now — add SECRET_WORK/OP/VA/OFFICE when you add your work phone and team.)"
for S in ANTHROPIC_KEY SECRET_PERSONAL SECRET_WORK SECRET_OP SECRET_VA SECRET_OFFICE; do
  printf "Set %s now? [y/N] " "$S"; read yn
  case "$yn" in [Yy]*) npx wrangler secret put "$S";; esac
done

echo
echo "Deploying..."
npx wrangler deploy
echo
echo "== Done. Copy the URL printed above, then test with: =="
echo '   export AIXMOS_GATEWAY="<that url>"'
echo '   export AIXMOS_SECRET="<your SECRET_PERSONAL value>"'
echo '   bash aixmos.sh "AIXMOS online. Reply in one sentence."'
