#!/usr/bin/env bash
# Auto-sync the AIXMOS starter pack to a freshly-mounted USB.
# Fires from launchd (WatchPaths=/Volumes) AND can be run manually as `aixsync`.
#
# Strategy:
# - ESSENTIALS (skills, memory, brain, pro, launchers) — small, fast, ALWAYS synced
# - RUNTIME (Open WebUI as a single tarball) — only synced if tarball exists and
#   USB doesn't already have a current copy. Single file = FAT32-friendly.
# - Real rsync (/opt/homebrew/bin/rsync) with FAT-safe flags (no perms/owners/xattrs)
# - Detects launchd TCC permission failure and posts a manual-fallback notification.

set -u
PACK_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOG="$PACK_DIR/logs/auto-sync.log"
LOCKDIR="$PACK_DIR/logs/.auto-sync.lockdir"
mkdir -p "$PACK_DIR/logs"

# Pick real rsync if available; fall back to system openrsync
RSYNC="/opt/homebrew/bin/rsync"
[ -x "$RSYNC" ] || RSYNC="/usr/bin/rsync"

# Atomic re-entrancy lock (mkdir works on macOS; flock does not)
if ! mkdir "$LOCKDIR" 2>/dev/null; then
  if [ -d "$LOCKDIR" ]; then
    AGE=$(( $(date +%s) - $(stat -f %m "$LOCKDIR" 2>/dev/null || echo 0) ))
    [ "$AGE" -gt 300 ] && rm -rf "$LOCKDIR" && mkdir "$LOCKDIR" 2>/dev/null || exit 0
  fi
fi
trap 'rm -rf "$LOCKDIR"' EXIT

ts()    { date "+%Y-%m-%d %H:%M:%S"; }
log()   { echo "[$(ts)] $*" >> "$LOG"; }
notify() { osascript -e "display notification \"$2\" with title \"$1\" sound name \"${3:-Glass}\"" 2>/dev/null || true; }

# Refresh staging bundles from ~/.claude/ first (so USB gets the latest skills/memory)
"$RSYNC" -rlt --delete --no-perms --no-owner --no-group \
  ~/.claude/skills/ "$PACK_DIR/_starter/skills/" >> "$LOG" 2>&1 || true
"$RSYNC" -rlt --delete --no-perms --no-owner --no-group \
  ~/.claude/projects/-Users-ceo-moe/memory/ "$PACK_DIR/_brain/memory/" >> "$LOG" 2>&1 || true
cp ~/.claude/plugins/known_marketplaces.json "$PACK_DIR/_starter/plugins/" 2>/dev/null || true
cp ~/.claude/plugins/installed_plugins.json  "$PACK_DIR/_starter/plugins/" 2>/dev/null || true

ESSENTIALS=(_starter _brain _pro _models docs LAUNCH.command LAUNCH.cmd README.md sync-to-usb.sh auto-sync-on-mount.sh)
RSYNC_FLAGS=(-rlt -h --delete --partial --no-perms --no-owner --no-group --no-xattrs
             --exclude=.DS_Store --exclude=._* --exclude=.Spotlight-V100
             --exclude=.Trashes --exclude=.fseventsd)

SYNCED_ANY=0
PERM_BLOCKED=0

for NAME in AIXMOS02 CYBORG; do
  VOL="/Volumes/$NAME"
  [ -d "$VOL" ] || continue

  TARGET="$VOL/AIXMOS-STARTER-PACK"
  log "Detected $VOL — sync target: $TARGET"

  # Probe write permission FIRST. If launchd is firing without FDA, we'll fail
  # here cleanly and emit a manual-fallback notification instead of looping.
  if ! mkdir -p "$TARGET" 2>>"$LOG"; then
    log "❌ $NAME — cannot create target dir (TCC/permission?). Skipping."
    PERM_BLOCKED=1
    continue
  fi
  if ! touch "$TARGET/.write_probe" 2>>"$LOG"; then
    log "❌ $NAME — write probe failed (TCC?). Skipping."
    PERM_BLOCKED=1
    continue
  fi
  rm -f "$TARGET/.write_probe"

  START=$(date +%s)

  # Essentials (always)
  for ITEM in "${ESSENTIALS[@]}"; do
    SRC="$PACK_DIR/$ITEM"
    [ ! -e "$SRC" ] && continue
    if [ -d "$SRC" ]; then
      mkdir -p "$TARGET/$ITEM/"
      "$RSYNC" "${RSYNC_FLAGS[@]}" "$SRC/" "$TARGET/$ITEM/" >> "$LOG" 2>&1 || true
    else
      "$RSYNC" -lth --no-perms --no-owner --no-group --no-xattrs "$SRC" "$TARGET/" >> "$LOG" 2>&1 || true
    fi
  done

  # Runtime tarball (only if source tarball exists AND USB copy is stale or missing)
  TARBALL_SRC="$PACK_DIR/_runtime/runtime.tar.gz"
  TARBALL_DST="$TARGET/_runtime/runtime.tar.gz"
  if [ -f "$TARBALL_SRC" ]; then
    mkdir -p "$TARGET/_runtime"
    SRC_MTIME=$(stat -f %m "$TARBALL_SRC" 2>/dev/null || echo 0)
    DST_MTIME=$(stat -f %m "$TARBALL_DST" 2>/dev/null || echo 0)
    if [ "$SRC_MTIME" -gt "$DST_MTIME" ]; then
      log "  syncing runtime tarball ($(du -sh "$TARBALL_SRC" | awk '{print $1}'))"
      "$RSYNC" -lth --no-perms --no-owner --no-group --no-xattrs \
        "$TARBALL_SRC" "$TARGET/_runtime/" >> "$LOG" 2>&1 || true
    fi
  fi

  END=$(date +%s)
  ELAPSED=$((END - START))

  SK=$(ls "$TARGET/_starter/skills" 2>/dev/null | wc -l | tr -d ' ')
  MEM=$(ls "$TARGET/_brain/memory" 2>/dev/null | wc -l | tr -d ' ')
  SZ=$(du -sh "$TARGET" 2>/dev/null | awk '{print $1}')

  log "✅ $NAME synced in ${ELAPSED}s — skills=$SK / memory=$MEM / size=$SZ"
  notify "AIXMOS sync ✅" "$NAME ($SK skills, $MEM mem, $SZ, ${ELAPSED}s)" "Glass"
  SYNCED_ANY=1
done

if [ "$SYNCED_ANY" -eq 0 ] && [ "$PERM_BLOCKED" -eq 1 ]; then
  notify "AIXMOS sync ⚠️" "USB plugged in but launchd lacks Removable-Volumes access. Run: aixsync" "Funk"
fi
