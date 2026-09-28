#!/usr/bin/env bash
# Mac: sync kit to flash / open docs — does not start Windows brain stack
set -euo pipefail

PROJECT_ROOT="${1:-$HOME/AI-OPS-STARTER}"
FLASH_DRIVE="${FLASH_DRIVE:-}"

echo "=== AI-OPS-STARTER Mac (control) ==="

if [[ -n "$FLASH_DRIVE" && -d "$FLASH_DRIVE" ]]; then
  FLASH_DRIVE="$FLASH_DRIVE" "$PROJECT_ROOT/scripts/sync-to-flash.sh" "$PROJECT_ROOT"
fi

if command -v tailscale >/dev/null 2>&1; then
  echo ""
  echo "Tailscale status:"
  tailscale status || true
  WIN_IP=$(tailscale status 2>/dev/null | grep -i 'windows' | awk '{print $1}' | head -1 || true)
  if [[ -n "${WIN_IP:-}" ]]; then
    echo ""
    echo "Windows AI machine (via Tailscale):"
    echo "  Open WebUI: http://${WIN_IP}:3000"
    echo "  n8n:        http://${WIN_IP}:5678"
  fi
fi

echo ""
echo "Mac is admin/control. Start the stack on the Windows AI machine:"
echo "  .\\start-windows.ps1"
