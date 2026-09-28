#!/usr/bin/env bash
# load-customer.sh — credit a customer's AIXMOS wallet after they pay you
# by CashApp (000-000-0000), Zelle (payments@example.com), cash, or any rail.
#
# Usage:
#   ./load-customer.sh <email> <pack|amount>
#
# Examples:
#   ./load-customer.sh jane@email.com pro       # $100 pack  -> 3,000 tokens, Sonnet
#   ./load-customer.sh jane@email.com 25         # $25 pack   -> 600 tokens, Haiku
#   ./load-customer.sh jane@email.com 500        # $500 pack  -> 18,000 tokens, Opus
#
# Packs:  starter=$25/600  pro=$100/3000  scale=$500/18000
set -euo pipefail

GATEWAY="${AIXMOS_GATEWAY:-https://aixmos-gateway.aixmos.workers.dev}"
SECRETS="${AIXMOS_SECRETS:-$HOME/aixmos-KEYS-canonical/gateway-secrets.env}"

# --- find the pay secret ---
if [ -z "${PAY_WEBHOOK_SECRET:-}" ]; then
  if [ -f "$SECRETS" ]; then
    PAY_WEBHOOK_SECRET="$(grep -E '^PAY_WEBHOOK_SECRET=' "$SECRETS" | head -1 | cut -d= -f2-)"
  fi
fi
if [ -z "${PAY_WEBHOOK_SECRET:-}" ]; then
  echo "✗ No PAY_WEBHOOK_SECRET found. Set it in $SECRETS or export it." >&2
  exit 1
fi

# --- args ---
EMAIL="${1:-}"; PACK="${2:-}"
if [ -z "$EMAIL" ] || [ -z "$PACK" ]; then
  echo "Usage: $0 <email> <pack|amount>   e.g.  $0 jane@email.com pro" >&2
  exit 1
fi

# --- map pack name or dollar amount -> amount_usd ---
case "$PACK" in
  starter|25)  USD=25  ;;
  pro|100)     USD=100 ;;
  scale|500)   USD=500 ;;
  *)           USD="$PACK" ;;   # allow a raw dollar amount that matches a pack
esac

echo "→ Loading \$$USD for $EMAIL ..."
RESP="$(curl -s -X POST "$GATEWAY/pay/webhook" \
  -H "x-pay-secret: $PAY_WEBHOOK_SECRET" \
  -H "content-type: application/json" \
  -d "{\"email\":\"$EMAIL\",\"amount_usd\":$USD}")"

echo "$RESP"
if echo "$RESP" | grep -q '"ok":true'; then
  WALLET="$(echo "$RESP" | sed -E 's/.*"wallet":([0-9]+).*/\1/')"
  echo "✓ Done. $EMAIL wallet now: $WALLET TMMT tokens."
else
  echo "✗ Something went off — check the response above (email must have signed up first)." >&2
  exit 1
fi
