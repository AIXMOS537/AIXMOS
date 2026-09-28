#!/bin/bash
# ============================================================
#  Setup-Mac.sh  —  RUN THIS ON A MAC (one time)
#  Mounts the NAS, clones the shared AIXMOS brain locally,
#  and wires it for two-way git sync + Obsidian.
#  Run in Terminal:  bash Setup-Mac.sh
# ============================================================
set -e

NAS_IP="192.168.1.236"                                   # NAS on the Verizon LAN
NAS_USER="MUHAMMAD TAHA"                                  # NAS SMB username (with the space)
NAS_USER_ENC="MUHAMMAD%20TAHA"                            # URL-encoded for smb://
SHARE="personal_folder"
MOUNT="/Volumes/$SHARE"
VAULT="$MOUNT/AIXMOS/AIXMOS-Brain"                        # the brain repo on the NAS
DEST="$HOME/AIXMOS-Brain"                                 # local copy on this Mac

echo "== AIXMOS Brain setup for Mac =="

# 1) Can this Mac reach the NAS?
if ! ping -c 2 -t 3 "$NAS_IP" >/dev/null 2>&1; then
  echo "NAS $NAS_IP is not reachable from here."
  echo "Either join the same WiFi as the NAS (Verizon), OR enable the Tailscale app in UGOS"
  echo "and re-run using the NAS's Tailscale name/IP instead of $NAS_IP."
  exit 1
fi

# 2) Mount the NAS share (prompts for the NAS password)
if [ ! -d "$MOUNT" ]; then mkdir -p "$MOUNT"; fi
if ! mount | grep -q "$MOUNT"; then
  echo "Mounting the NAS (enter the NAS password for '$NAS_USER' when asked)..."
  mount_smbfs "//$NAS_USER_ENC@$NAS_IP/$SHARE" "$MOUNT"
fi

# 3) Make git trust the path, then clone or update
git config --global --add safe.directory "$VAULT" 2>/dev/null || true
if [ -d "$DEST/.git" ]; then
  echo "Brain already here -- pulling latest..."
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
open "$DEST" 2>/dev/null || true
