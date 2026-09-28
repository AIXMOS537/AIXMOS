#!/bin/bash
cd "$(dirname "${BASH_SOURCE[0]}")"

if [ -z "$GHL_WEBHOOK_SHARED_SECRET" ]; then
  echo ""
  echo "  GHL_WEBHOOK_SHARED_SECRET is not set."
  echo "  Set it once via:"
  echo "    echo 'export GHL_WEBHOOK_SHARED_SECRET=\"<long random secret>\"' >> ~/.zshrc"
  echo "    source ~/.zshrc"
  echo "  Then re-run this file."
  echo ""
  read -p "  Press Enter to close..."
  exit 1
fi

: "${PORT:=4099}"

echo ""
echo "  ============================================================"
echo "   CHUMMO-GHL Webhook (Mac)"
echo "   Port:       $PORT"
echo "   Health URL: http://localhost:$PORT/health"
echo "   Endpoints:  POST /draft, /draft/sms, /draft/email, /draft/dm"
echo "   Backend:    ${AIXMOS_LLM_BACKEND:-claude}"
echo "  ============================================================"
echo ""

node server.js
echo ""
read -p "  Server stopped. Press Enter to close..."
