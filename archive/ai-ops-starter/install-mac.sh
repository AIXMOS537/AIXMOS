#!/usr/bin/env bash
# AI-OPS-STARTER — MacBook admin/control machine setup
set -euo pipefail

PROJECT_ROOT="${1:-$HOME/AI-OPS-STARTER}"
FLASH_DRIVE="${FLASH_DRIVE:-/Volumes/AI-OPS}"

echo ""
echo "=== AI-OPS-STARTER Mac Install (admin/control) ==="
echo "Project root: $PROJECT_ROOT"
echo ""

command_exists() { command -v "$1" >/dev/null 2>&1; }

# Prerequisites (Mac does NOT run the main stack by default)
MISSING=0
for cmd in git rsync tailscale; do
  if command_exists "$cmd"; then
    echo "[OK] $cmd"
  else
    echo "[MISSING] $cmd — install via Homebrew: brew install $cmd"
    MISSING=1
  fi
done

if ! command_exists docker; then
  echo "[OPTIONAL] Docker Desktop — only needed if testing stack on Mac"
else
  echo "[OK] docker (optional on Mac)"
fi

if [[ $MISSING -eq 1 ]]; then
  echo "Install missing tools, then re-run."
  exit 1
fi

mkdir -p "$PROJECT_ROOT"
if [[ -d "$(dirname "$0")" && "$(cd "$(dirname "$0")" && pwd)" != "$PROJECT_ROOT" ]]; then
  echo "Syncing kit files to $PROJECT_ROOT ..."
  rsync -av --delete \
    --exclude '.env' \
    --exclude 'data/' \
    "$(cd "$(dirname "$0")" && pwd)/" "$PROJECT_ROOT/"
fi

# Flash drive prep — full kit including docs/DEPLOY-ORDER.md
if [[ -d "$FLASH_DRIVE" ]]; then
  echo ""
  echo "Flash drive detected — syncing full install kit..."
  FLASH_DRIVE="$FLASH_DRIVE" "$PROJECT_ROOT/scripts/sync-to-flash.sh" "$PROJECT_ROOT"
else
  echo ""
  echo "No flash drive at $FLASH_DRIVE (set FLASH_DRIVE=/Volumes/YourDisk then re-run)"
fi

chmod +x "$PROJECT_ROOT"/*.sh 2>/dev/null || true
chmod +x "$PROJECT_ROOT"/scripts/*.sh 2>/dev/null || true

echo ""
echo "=== Mac setup complete ==="
echo ""
echo "Next steps:"
echo "  1. Full Mac guide: $PROJECT_ROOT/setup/mac/MACBOOK-SETUP.md"
echo "  2. Edit kit (registry, docs) in $PROJECT_ROOT"
echo "  3. Sync flash: FLASH_DRIVE=/Volumes/AI-OPS ./scripts/sync-to-flash.sh"
echo "  4. Tailscale → http://brainiac-7:3000 (Brainiac 7 Windows)"
echo "  5. iPhone: setup/phone/IPHONE-SETUP.md"
echo ""
