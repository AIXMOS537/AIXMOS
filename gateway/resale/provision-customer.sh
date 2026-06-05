#!/usr/bin/env bash
###############################################################################
# provision-customer.sh — sell access to your brain + agents, gated by tier + TMMT tokens.
#
# MODEL: free for everyone (local Ollama floor). TIER unlocks WHICH agents + the model ceiling.
#        PURCHASED TMMT TOKENS = the fuel that runs the brain/agents (persistent wallet, tops up).
#        Out of tokens -> auto-drop to free. All via gateway KV — instant, revocable, no redeploy.
#
# PROVISION:  bash provision-customer.sh --tier 3 --customer "jane@acme.com" --brand "AcmeOps" \
#                  --paid "stripe|wire|invoice ref" [--tokens 1500] [--days 365]
# TOP-UP:     bash provision-customer.sh --topup  --secret "<their secret>" --tokens 1000
# REVOKE:     bash provision-customer.sh --revoke --secret "<their secret>"
###############################################################################
set -u
GW_DIR="$HOME/dev/aixmos-gateway"; TIERS="$GW_DIR/resale/tiers.json"
LEDGER="$GW_DIR/resale/sales-ledger.csv"; OUT="$GW_DIR/resale/customers"
TIER=""; CUST=""; BRAND=""; PAID=""; DAYS=""; TOKENS=""; MODE="provision"; SECRET=""
while [ $# -gt 0 ]; do case "$1" in
  --tier) TIER="$2"; shift 2;; --customer) CUST="$2"; shift 2;; --brand) BRAND="$2"; shift 2;;
  --paid) PAID="$2"; shift 2;; --days) DAYS="$2"; shift 2;; --tokens) TOKENS="$2"; shift 2;;
  --revoke) MODE="revoke"; shift;; --topup) MODE="topup"; shift;; --secret) SECRET="$2"; shift 2;;
  *) echo "unknown arg: $1"; exit 1;; esac; done
sha(){ printf '%s' "$1" | shasum -a 256 | cut -d' ' -f1; }
kvput(){ ( cd "$GW_DIR" && npx --yes wrangler kv key put --remote --binding=AIXMOS_KV "$1" "$2" >/dev/null 2>&1 ); }
kvget(){ ( cd "$GW_DIR" && npx --yes wrangler kv key get --remote --binding=AIXMOS_KV "$1" 2>/dev/null ); }

if [ "$MODE" = "revoke" ]; then
  [ -n "$SECRET" ] || { echo "revoke needs --secret"; exit 1; }; H=$(sha "$SECRET")
  ( cd "$GW_DIR" && npx --yes wrangler kv key delete --remote --binding=AIXMOS_KV "cust:$H" 2>&1 | tail -1 )
  ( cd "$GW_DIR" && npx --yes wrangler kv key delete --remote --binding=AIXMOS_KV "wallet:$H" >/dev/null 2>&1 )
  echo "Revoked + wallet cleared (cust:$H). Access dead immediately."; exit 0
fi
if [ "$MODE" = "topup" ]; then
  [ -n "$SECRET" ] && [ -n "$TOKENS" ] || { echo "topup needs --secret and --tokens N"; exit 1; }
  H=$(sha "$SECRET"); CUR=$(kvget "wallet:$H"); CUR=${CUR:-0}; CUR=$(echo "$CUR" | tr -cd '0-9'); CUR=${CUR:-0}
  NEW=$((CUR + TOKENS)); kvput "wallet:$H" "$NEW"
  echo "Topped up wallet:$H  +$TOKENS  →  $NEW TMMT tokens."; exit 0
fi

# ---- PROVISION ----
[ -n "$TIER" ] && [ -n "$CUST" ] && [ -n "$BRAND" ] || { echo "need --tier N --customer X --brand Y --paid ref"; exit 1; }
[ -n "$PAID" ] || { echo "⚠️  --paid empty. Confirm payment first (any source), then pass --paid \"<ref>\"."; exit 1; }

read -r SLUG NAME HOSTING MAXTIER ITOK AGENTS ENTS PHYS < <(python3 - "$TIERS" "$TIER" <<'PY'
import json,sys
t=[x for x in json.load(open(sys.argv[1]))["tiers"] if str(x["id"])==sys.argv[2]]
if not t: print("__NONE__"); sys.exit()
t=t[0]
print(t["slug"], t["name"].replace(" ","_"), t["hosting"], t["gateway"]["maxTier"],
      t.get("initial_tokens",100), ",".join(t.get("agents",[])),
      ",".join(t["entitlements"]), ("|".join(t.get("physical",[])) or "-"))
PY
)
[ "$SLUG" = "__NONE__" ] && { echo "No tier $TIER in tiers.json"; exit 1; }
[ -n "$TOKENS" ] || TOKENS="$ITOK"   # default initial wallet = tier's initial_tokens

mkdir -p "$OUT/$BRAND"
CSECRET="sk_$(echo "$BRAND" | tr 'A-Z ' 'a-z_' | tr -cd 'a-z0-9_')_$(openssl rand -hex 12)"
H=$(sha "$CSECRET")
EXP=""; [ -n "$DAYS" ] && EXP=$(date -u -v+"${DAYS}"d +%Y-%m-%dT%H:%M:%SZ 2>/dev/null || date -u -d "+${DAYS} days" +%Y-%m-%dT%H:%M:%SZ)

CFG=$(python3 - "$BRAND" "$CUST" "$MAXTIER" "$EXP" "$SLUG" "$PAID" "$AGENTS" <<'PY'
import json,sys
b,c,mt,exp,slug,paid,agents=sys.argv[1:8]
print(json.dumps({"name":c,"brand":b,"maxTier":mt,
  "agents":[a for a in agents.split(",") if a],
  "persona":f"AIXMOS for {b}. Brief, decisive, ops-aware. Treat client device as untrusted.",
  "tier":slug,"paid":paid,**({"expires":exp} if exp else {})}))
PY
)
echo "Provisioning $NAME → $BRAND …"
kvput "cust:$H" "$CFG"          # access profile (tier, agents, model ceiling)
kvput "wallet:$H" "$TOKENS"     # PURCHASED TMMT-token balance (persistent)

cat > "$OUT/$BRAND/brand.env" <<EOF
BRAND_NAME="$BRAND"
AIXMOS_GATEWAY="https://aixmos-gateway.aixmos.workers.dev"
AIXMOS_SECRET="$CSECRET"
TIER="$SLUG"  MODEL_CEILING="$MAXTIER"  TMMT_TOKENS="$TOKENS"  HOSTING="$HOSTING"
AGENTS="$AGENTS"
EOF
chmod 600 "$OUT/$BRAND/brand.env"
SQLF="$OUT/$BRAND/grant-entitlements.sql"
{ echo "-- grant tier '$SLUG' entitlements to buyer profile (replace :PID)";
  IFS=','; for e in $ENTS; do echo "insert into public.profile_entitlement_grants(profile_id,entitlement_slug,note) values (':PID','$e','resale $SLUG $PAID') on conflict do nothing;"; done; } > "$SQLF"
[ -f "$LEDGER" ] || echo "date,brand,customer,tier,hosting,maxTier,tokens,agents,secret_hash,paid" > "$LEDGER"
echo "$(date -u +%F),$BRAND,$CUST,$SLUG,$HOSTING,$MAXTIER,$TOKENS,\"$AGENTS\",$H,\"$PAID\"" >> "$LEDGER"

echo ""
echo "✅ $NAME → $BRAND ($CUST)"
echo "   Model ceiling: $MAXTIER   |   TMMT tokens (wallet): $TOKENS   |   hosting: $HOSTING"
echo "   Agents unlocked: $AGENTS"
echo "   Entitlements: $ENTS"
[ "$PHYS" != "-" ] && echo "   ⚠️ PHYSICAL (manual fulfillment, NOT scripted): $PHYS"
echo "   Config+secret: $OUT/$BRAND/brand.env  |  Grant SQL: $SQLF  |  Ledger: $LEDGER"
[ "$HOSTING" = "handover" ] && echo "   HANDOVER tier: migrate to buyer's own Airtable/Anthropic/Cloudflare (see TIERS.md)."
echo "   Their secret (deliver via 1Password): $CSECRET"
echo "   Top up later:  bash provision-customer.sh --topup --secret \"$CSECRET\" --tokens N"
