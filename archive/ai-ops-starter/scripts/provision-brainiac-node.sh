#!/usr/bin/env bash
# Mac admin: generate .env snippet for an operator node (copy to flash / send to site)
set -euo pipefail
TIER="${1:?Usage: $0 <tier 1-7> <location> <operator-id> [display-name]}"
LOCATION="${2:?location code}"
OPERATOR="${3:?operator id}"
DISPLAY="${4:-Brainiac $TIER — $LOCATION}"
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
UPSTREAM="${BRAINIAC_UPSTREAM:-brainiac-7}"

TIER_FILE="$ROOT/setup/tiers/brainiac-${TIER}.env.example"
[[ -f "$TIER_FILE" ]] || { echo "Missing $TIER_FILE"; exit 1; }

if [[ "$TIER" -eq 7 ]]; then HOST="brainiac-7"; else HOST="brainiac-${TIER}-${OPERATOR}"; fi
OUT="$ROOT/setup/operators/generated/${HOST}.env"

mkdir -p "$(dirname "$OUT")"
{
  echo "# Generated $(date -Iseconds) — deploy to operator PC"
  cat "$ROOT/.env.example"
  echo ""
  echo "# --- Tier $TIER ---"
  cat "$TIER_FILE"
  echo "BRAINIAC_TIER=$TIER"
  echo "BRAINIAC_NODE_ID=$HOST"
  echo "BRAINIAC_LOCATION_CODE=$LOCATION"
  echo "BRAINIAC_OPERATOR_ID=$OPERATOR"
  echo "AI_OPS_HOST_NAME=$HOST"
  echo "WEBUI_NAME=$DISPLAY"
  echo "NAS_LOCATION_PATH=locations/$LOCATION"
  echo "NAS_OPERATOR_PATH=locations/$LOCATION/operators/$OPERATOR"
  if [[ "$TIER" -lt 7 ]]; then
    echo "BRAINIAC_UPSTREAM_HOST=$UPSTREAM"
    echo "BRAINIAC_UPSTREAM_WEBUI_URL=http://${UPSTREAM}:3000"
  fi
} > "$OUT"

echo "Wrote $OUT"
echo "Copy to operator PC as C:\\AI-OPS-STARTER\\.env"
