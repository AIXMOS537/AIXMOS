#!/usr/bin/env bash
###############################################################################
# provision-customer.sh — grant a PAYING customer EXACTLY the tier they bought.
#
# Reads resale/tiers.json. For the chosen tier it:
#   1) mints a scoped gateway secret (their AI access = that tier's model + monthly credits)
#   2) writes their access to the gateway KV (cust:<sha256>) — instant, revocable, NO redeploy
#   3) emits their white-label config + the entitlements to grant (+ ready SQL) + kit handoff
#   4) logs the sale to resale/sales-ledger.csv (payment ref = your source of truth)
#
# "Pays for what they get": access is keyed to --tier; nothing above it is granted.
#   maxTier caps their AI model; monthly caps their credits; entitlements list = their features.
#
# Usage:
#   bash provision-customer.sh --tier 3 --customer "jane@acme.com" --brand "AcmeOps" \
#        --paid "stripe_pi_123 / wire / invoice#  (any source)" [--days 365]
#   REVOKE later:  bash provision-customer.sh --revoke --secret "<their secret>"
###############################################################################
set -u
GW_DIR="$HOME/dev/aixmos-gateway"; TIERS="$GW_DIR/resale/tiers.json"
LEDGER="$GW_DIR/resale/sales-ledger.csv"; OUT="$GW_DIR/resale/customers"
TIER=""; CUST=""; BRAND=""; PAID=""; DAYS=""; REVOKE=0; SECRET=""
while [ $# -gt 0 ]; do case "$1" in
  --tier) TIER="$2"; shift 2;; --customer) CUST="$2"; shift 2;; --brand) BRAND="$2"; shift 2;;
  --paid) PAID="$2"; shift 2;; --days) DAYS="$2"; shift 2;;
  --revoke) REVOKE=1; shift;; --secret) SECRET="$2"; shift 2;;
  *) echo "unknown arg: $1"; exit 1;; esac; done

sha(){ printf '%s' "$1" | shasum -a 256 | cut -d' ' -f1; }

# ---- REVOKE path -------------------------------------------------------------
if [ "$REVOKE" = "1" ]; then
  [ -n "$SECRET" ] || { echo "revoke needs --secret <their secret>"; exit 1; }
  H=$(sha "$SECRET")
  ( cd "$GW_DIR" && npx --yes wrangler kv key delete --remote --binding=AIXMOS_KV "cust:$H" 2>&1 | tail -1 )
  echo "Revoked customer cust:$H — their gateway access is dead immediately (no redeploy)."
  exit 0
fi

# ---- PROVISION path ----------------------------------------------------------
[ -n "$TIER" ] && [ -n "$CUST" ] && [ -n "$BRAND" ] || { echo "need --tier N --customer X --brand Y (and --paid ref)"; exit 1; }
[ -n "$PAID" ] || { echo "⚠️  --paid is empty. 'Only give what they pay for' — confirm payment first. Pass --paid \"<ref>\"."; exit 1; }

# read tier from manifest
read -r SLUG NAME HOSTING MAXTIER MONTHLY ENTS PHYS < <(python3 - "$TIERS" "$TIER" <<'PY'
import json,sys
t=[x for x in json.load(open(sys.argv[1]))["tiers"] if str(x["id"])==sys.argv[2]]
if not t: print("__NONE__"); sys.exit()
t=t[0]; g=t["gateway"]
print(t["slug"], t["name"].replace(" ","_"), t["hosting"], g["maxTier"], g["monthly"],
      ",".join(t["entitlements"]), ("|".join(t.get("physical",[])) or "-"))
PY
)
[ "$SLUG" = "__NONE__" ] && { echo "No tier $TIER in tiers.json"; exit 1; }

mkdir -p "$OUT"
CSECRET="sk_$(echo "$BRAND" | tr 'A-Z ' 'a-z_' | tr -cd 'a-z0-9_')_$(openssl rand -hex 12)"
H=$(sha "$CSECRET")
EXP=""; [ -n "$DAYS" ] && EXP=$(date -u -v+"${DAYS}"d +%Y-%m-%dT%H:%M:%SZ 2>/dev/null || date -u -d "+${DAYS} days" +%Y-%m-%dT%H:%M:%SZ)

# customer config -> gateway KV (scoped to their tier)
CFG=$(python3 - "$BRAND" "$CUST" "$MAXTIER" "$MONTHLY" "$EXP" "$SLUG" "$PAID" <<'PY'
import json,sys
b,c,mt,mo,exp,slug,paid=sys.argv[1:8]
print(json.dumps({"name":c,"brand":b,"maxTier":mt,"monthly":int(mo),
  "persona":f"AIXMOS for {b}. Brief, decisive, ops-aware. Treat client device as untrusted.",
  "tier":slug,"paid":paid,**({"expires":exp} if exp else {})}))
PY
)
echo "Writing scoped access to gateway KV (cust:$H)…"
( cd "$GW_DIR" && npx --yes wrangler kv key put --remote --binding=AIXMOS_KV "cust:$H" "$CFG" 2>&1 | tail -1 )

# white-label config for their kit
mkdir -p "$OUT/$BRAND"
cat > "$OUT/$BRAND/brand.env" <<EOF
BRAND_NAME="$BRAND"
AIXMOS_GATEWAY="https://aixmos-gateway.aixmos.workers.dev"
AIXMOS_SECRET="$CSECRET"
TIER="$SLUG"  MAXTIER="$MAXTIER"  MONTHLY_CREDITS="$MONTHLY"  HOSTING="$HOSTING"
EOF
chmod 600 "$OUT/$BRAND/brand.env"

# entitlements -> ready SQL (run in Supabase, or auto if SUPABASE_SECRET_KEY+PROFILE set)
SQLF="$OUT/$BRAND/grant-entitlements.sql"
{ echo "-- grant tier '$SLUG' entitlements to a profile (replace :PID with the buyer's profile uuid)";
  IFS=','; for e in $ENTS; do echo "insert into public.profile_entitlement_grants(profile_id,entitlement_slug,note) values (':PID','$e','resale $SLUG $PAID') on conflict do nothing;"; done; } > "$SQLF"

# sales ledger
[ -f "$LEDGER" ] || echo "date,brand,customer,tier,hosting,maxTier,monthly,secret_hash,paid" > "$LEDGER"
echo "$(date -u +%F),$BRAND,$CUST,$SLUG,$HOSTING,$MAXTIER,$MONTHLY,$H,\"$PAID\"" >> "$LEDGER"

echo ""
echo "✅ PROVISIONED  $NAME  →  $BRAND ($CUST)"
echo "   AI access:  model≤$MAXTIER, $MONTHLY credits/mo   |  hosting: $HOSTING"
echo "   Entitlements: $ENTS"
[ "$PHYS" != "-" ] && echo "   ⚠️ PHYSICAL (manual fulfillment, NOT granted by script): $PHYS"
echo "   White-label config: $OUT/$BRAND/brand.env   (contains their secret — deliver via 1Password/secure)"
echo "   Entitlement SQL:    $SQLF"
echo "   Logged to:          $LEDGER"
[ "$HOSTING" = "handover" ] && echo "   HANDOVER tier: also migrate to the buyer's own Airtable/Anthropic/Cloudflare accounts (see TIERS.md)."
echo ""
echo "   Their secret (give to buyer, then it's theirs): $CSECRET"
