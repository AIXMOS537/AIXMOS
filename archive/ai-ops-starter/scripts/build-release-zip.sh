#!/usr/bin/env bash
# Build versioned release zip (Mac admin) — for NAS / GitLab / Google Drive
set -euo pipefail

SOURCE="$(cd "$(dirname "$0")/.." && pwd)"
VERSION="${VERSION:-$(head -1 "$SOURCE/VERSION" 2>/dev/null || echo 1.0.0)}"
OUT="${OUT:-$SOURCE/dist}"
STAGING="$(mktemp -d)"
ZIP="$OUT/AI-OPS-STARTER-v${VERSION}.zip"

mkdir -p "$OUT"

if command -v pwsh >/dev/null 2>&1; then
  pwsh "$SOURCE/scripts/generate-installers.ps1" -ProjectRoot "$SOURCE"
else
  "$SOURCE/scripts/generate-installers.sh"
fi

mkdir -p "$STAGING/AI-OPS-STARTER"
rsync -a --delete \
  --exclude '.env' \
  --exclude 'data/' \
  --exclude 'dist/' \
  --exclude '.git/' \
  "$SOURCE/" "$STAGING/AI-OPS-STARTER/"

rm -f "$ZIP"
(cd "$STAGING" && zip -r "$ZIP" AI-OPS-STARTER -x "*.DS_Store")
shasum -a 256 "$ZIP" | tee "$OUT/AI-OPS-STARTER-v${VERSION}.sha256"
rm -rf "$STAGING"

echo ""
echo "Release: $ZIP"
echo "Upload: flash releases/, NAS, GitLab, or Google Drive (see docs/TEAM-SELF-INSTALL.md)"
