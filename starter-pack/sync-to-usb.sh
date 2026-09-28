#!/usr/bin/env bash
# Sync this staging pack to a mounted USB drive (AIXMOS02 or CYBORG).
# Usage: bash sync-to-usb.sh [AIXMOS02|CYBORG|<other volume name>]

set -euo pipefail
PACK_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Choose target
TARGET_NAME="${1:-}"
if [ -z "$TARGET_NAME" ]; then
  echo "Detecting mounted USB volumes..."
  mapfile -t VOLS < <(ls /Volumes 2>/dev/null | grep -v "^Macintosh HD$" | grep -v "^\.")
  if [ ${#VOLS[@]} -eq 0 ]; then
    echo "❌ No USB drives mounted. Plug in AIXMOS02 or CYBORG and re-run."
    exit 1
  fi
  echo ""
  i=1
  for v in "${VOLS[@]}"; do
    echo "  $i) /Volumes/$v"
    i=$((i+1))
  done
  echo ""
  printf "Pick a volume (1-${#VOLS[@]}) or q: "
  read -r choice
  [[ "$choice" =~ ^[Qq]$ ]] && exit 0
  TARGET_NAME="${VOLS[$((choice-1))]}"
fi

TARGET="/Volumes/$TARGET_NAME/AIXMOS-STARTER-PACK"
if [ ! -d "/Volumes/$TARGET_NAME" ]; then
  echo "❌ /Volumes/$TARGET_NAME not mounted."
  exit 1
fi

echo ""
echo "  Source: $PACK_DIR"
echo "  Target: $TARGET"
echo ""
printf "Proceed with rsync? (y/N): "
read -r ans
[[ "$ans" =~ ^[Yy]$ ]] || { echo "Cancelled."; exit 0; }

mkdir -p "$TARGET"
rsync -ah --delete --info=progress2 \
  --exclude '.DS_Store' \
  --exclude '_models/*.gguf' \
  --exclude 'logs/' \
  "$PACK_DIR/" "$TARGET/"

# Restore executable bits (FAT/exFAT USBs strip them on copy from APFS)
chmod +x "$TARGET/LAUNCH.command" "$TARGET/_starter"/*.sh "$TARGET/sync-to-usb.sh" 2>/dev/null || true

echo ""
echo "✅ Synced to $TARGET"
echo ""
echo "On the target machine:"
echo "  Mac     → double-click $TARGET/LAUNCH.command"
echo "  Windows → double-click $TARGET/LAUNCH.cmd"
