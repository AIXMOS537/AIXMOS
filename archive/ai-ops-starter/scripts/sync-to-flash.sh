#!/usr/bin/env bash
# Sync full install kit to flash drive (includes DEPLOY-ORDER, registry, all docs)
set -euo pipefail

SOURCE="${1:-$(cd "$(dirname "$0")/.." && pwd)}"
FLASH="${FLASH_DRIVE:-/Volumes/AI-OPS}"
DEST="$FLASH/AI-OPS-STARTER"

if [[ ! -d "$FLASH" ]]; then
  echo "Flash not found at $FLASH"
  echo "Set FLASH_DRIVE=/Volumes/YourDiskName"
  exit 1
fi

if command -v pwsh >/dev/null 2>&1; then
  pwsh "$SOURCE/scripts/generate-installers.ps1" -ProjectRoot "$SOURCE"
else
  "$SOURCE/scripts/generate-installers.sh"
fi

echo "Syncing kit → $DEST"
rsync -av --delete \
  --exclude '.env' \
  --exclude 'data/' \
  --exclude 'setup/operators/generated/' \
  "$SOURCE/" "$DEST/"

chmod +x "$DEST"/*.sh 2>/dev/null || true
chmod +x "$DEST"/scripts/*.sh 2>/dev/null || true

"$SOURCE/scripts/verify-flash-drive.sh" "$DEST"
echo ""
echo "Flash ready. Open START-HERE-FLASH.md on the USB."
