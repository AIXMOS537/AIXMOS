#!/usr/bin/env bash
set -euo pipefail
KIT="${1:-$HOME/AI-OPS-STARTER}"
STAMP=$(date +%Y-%m-%d)
DEST="${HOME}/AI-OPS-BACKUPS/${STAMP}"
mkdir -p "$DEST"
rsync -av --exclude .env --exclude .git "$KIT/" "$DEST/kit/"
echo "Mac kit backup: $DEST"
