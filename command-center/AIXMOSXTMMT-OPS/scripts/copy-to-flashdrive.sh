#!/usr/bin/env bash
# Mac: copy to volume named AIXMOS02
set -euo pipefail
LABEL="${1:-AIXMOS02}"
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
DEST="/Volumes/${LABEL}/AIXMOSXTMMT-OPS"

if [[ ! -d "/Volumes/${LABEL}" ]]; then
  echo "Volume /Volumes/${LABEL} not found. Available:"
  ls -1 /Volumes
  exit 1
fi

mkdir -p "$DEST"
rsync -av --progress \
  --exclude node_modules \
  --exclude 'apps/clock/node_modules' \
  --exclude 'apps/clock/dist' \
  --exclude .env \
  "$ROOT/" "$DEST/"

echo ""
echo "Done: $DEST"
echo "  cd $DEST && ./scripts/setup-mac.sh"
