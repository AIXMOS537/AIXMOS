#!/usr/bin/env bash
# Sync Desktop TMMT + AIXMODE → Lexar (run from Terminal.app on Mac)
set -euo pipefail

LEXAR="${LEXAR:-/Volumes/LEXAR}"
SRC_TMMT="${SRC_TMMT:-$HOME/Desktop/TMMT MANAGEMENT}"
SRC_AIX="${SRC_AIX:-$HOME/Desktop/AIXMODE}"

if [[ ! -d "$LEXAR" ]]; then
  echo "Lexar not mounted at $LEXAR"
  exit 1
fi

RSYNC_OPTS=(
  -rltDv
  --exclude=node_modules
  --exclude=.git
  --exclude=__pycache__
  --exclude=.DS_Store
  --exclude='._*'
  --exclude=.env
  --exclude=.env.local
  --no-perms
  --no-owner
  --no-group
  --no-times
)

echo "Syncing TMMT → $LEXAR/TMMT MANAGEMENT"
rsync "${RSYNC_OPTS[@]}" "$SRC_TMMT/" "$LEXAR/TMMT MANAGEMENT/"

if [[ -d "$SRC_AIX" ]]; then
  echo "Syncing AIXMODE → $LEXAR/AIXMODE"
  mkdir -p "$LEXAR/AIXMODE"
  rsync "${RSYNC_OPTS[@]}" "$SRC_AIX/" "$LEXAR/AIXMODE/"
fi

echo "Done. TMMT files: $(find "$LEXAR/TMMT MANAGEMENT" -type f ! -name '._*' | wc -l | tr -d ' ')"
