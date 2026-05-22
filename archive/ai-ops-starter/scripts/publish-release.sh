#!/usr/bin/env bash
# Mac admin: generate installers, build zip, sync flash (+ optional NAS path)
set -euo pipefail

SOURCE="$(cd "$(dirname "$0")/.." && pwd)"
FLASH="${FLASH_DRIVE:-/Volumes/AI-OPS}"
VERSION="$(head -1 "$SOURCE/VERSION" 2>/dev/null || echo 1.0.0)"

echo ""
echo "=== AI-OPS publish v${VERSION} ==="
echo "Channels: Flash (primary) -> NAS -> GitLab -> Google Drive"
echo ""

if command -v pwsh >/dev/null 2>&1; then
  pwsh "$SOURCE/scripts/generate-installers.ps1" -ProjectRoot "$SOURCE"
else
  "$SOURCE/scripts/generate-installers.sh"
fi

"$SOURCE/scripts/build-release-zip.sh"

if [[ -d "$FLASH" ]]; then
  "$SOURCE/scripts/sync-to-flash.sh" "$SOURCE"
  mkdir -p "$FLASH/AI-OPS-RELEASES"
  cp -f "$SOURCE/dist/AI-OPS-STARTER-v${VERSION}.zip" "$FLASH/AI-OPS-RELEASES/" 2>/dev/null || true
  cp -f "$SOURCE/dist/AI-OPS-STARTER-v${VERSION}.sha256" "$FLASH/AI-OPS-RELEASES/" 2>/dev/null || true
  echo "Release zip on flash: $FLASH/AI-OPS-RELEASES/"
else
  echo "[WARN] Flash not at $FLASH — plug in USB or set FLASH_DRIVE=/Volumes/YourName"
fi

echo ""
echo "Done. See docs/TEAM-SELF-INSTALL.md for NAS / GitLab / Drive steps."
