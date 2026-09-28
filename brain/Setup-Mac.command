#!/bin/bash
# ============================================================
#  Setup-Mac.command  —  RUN THIS ON YOUR MAC (one time)
#  Connects to the NAS, clones the shared AIXMOS brain locally,
#  and wires it for two-way git sync + Obsidian.
#  If double-click is blocked, open Terminal and run:
#     bash "/Volumes/personal_folder/AIXMOS/Setup-Mac.command"
# ============================================================
set -e

NAS_IP="192.168.1.236"          # NAS on the Verizon LAN
NAS_USER="MUHAMMAD TAHA"        # NAS SMB username (with the space)
SHARE="personal_folder"
VAULT="/Volumes/${SHARE}/AIXMOS/AIXMOS-Brain"
DEST="$HOME/AIXMOS-Brain"

echo "== AIXMOS Brain setup for Mac =="

# 1) Reachable?
if ! ping -c 2 -t 3 "$NAS_IP" >/dev/null 2>&1; then
  echo "NAS $NAS_IP is not reachable from here."
  echo "Join the NAS's WiFi (Verizon), OR enable the Tailscale app in UGOS and re-run"
  echo "using the NAS's Tailscale name instead of $NAS_IP."
  exit 1
fi

# 2) Mount the share (prompts for the NAS password, then caches in Keychain)
echo "Mounting smb://$NAS_IP/$SHARE  (enter the NAS password for '$NAS_USER' if asked)..."
osascript -e "mount volume \"smb://$NAS_IP/$SHARE\" as user name \"$NAS_USER\"" || true
for i in $(seq 1 10); do [ -d "/Volumes/$SHARE" ] && break; sleep 1; done

# 3) Clone or update the brain
git config --global --add safe.directory "$VAULT" 2>/dev/null || true
if [ -d "$DEST/.git" ]; then
  echo "Brain already here — pulling latest..."
  git -C "$DEST" pull nas main
else
  echo "Cloning the brain to $DEST ..."
  git clone "$VAULT" "$DEST"
  git -C "$DEST" remote rename origin nas 2>/dev/null || true
fi

echo ""
echo "DONE. Your brain is at: $DEST"
echo "Open that folder as a Vault in Obsidian (Open folder as vault)."
echo "Sync later:  git -C \"$DEST\" pull nas main   (get updates)"
echo "             git -C \"$DEST\" push nas main   (send your edits)"
open "$DEST"
