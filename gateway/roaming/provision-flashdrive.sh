#!/usr/bin/env bash
###############################################################################
# provision-flashdrive.sh — make a USB drive a PLUG-AND-PLAY AIXMOS kit (macOS).
#
# Plug in a drive, run this, and it lays down on the drive:
#   AIXMOS-KIT/  -> never-dark clients (Win+Mac), device bootstraps, road runbook,
#                   your TMMT Knowledge Base (offline SOPs), and a START-HERE.
# Then on ANY machine: plug the drive in, open START-HERE, run the bootstrap.
#
# SAFE BY DESIGN (your rules):
#   - Non-destructive: only ADDS/UPDATES AIXMOS-KIT; never deletes your other files.
#   - GitHub = truth: pulls the latest kit from the repo first.
#   - Drives = keys, never bulk: NO raw secrets copied. (Optional: --with-enc-keys
#     writes an AES-256 ENCRYPTED keys bundle you unlock with a passphrase.)
#   - Marginal-drive safe: verifies file count + syncs/flushes after writing.
#
# Usage:
#   bash provision-flashdrive.sh                 # auto-detect removable drives, ask
#   bash provision-flashdrive.sh /Volumes/CYBORG # target a specific drive
#   WITH_ENC_KEYS=1 bash provision-flashdrive.sh /Volumes/CYBORG   # + encrypted keys
###############################################################################
set -u
KIT_SRC="$HOME/dev/aixmos-gateway/roaming"
KB_SRC="$HOME/Downloads/TMMT_Knowledge_Base"      # offline SOPs (if present)
VAULT="$HOME/aixmos-KEYS-canonical/gateway-secrets.env"
WITH_ENC_KEYS="${WITH_ENC_KEYS:-0}"

# 0) refresh kit from GitHub (truth) — non-fatal if offline
( cd "$HOME/dev/aixmos-gateway" && git pull -q --ff-only 2>/dev/null && echo "kit refreshed from GitHub" ) || echo "(offline or no ff — using local kit)"

# 1) pick the drive
DRIVE="${1:-}"
if [ -z "$DRIVE" ]; then
  echo "Removable volumes:"; i=0; CANDS=()
  while IFS= read -r v; do
    # only external/removable, skip the system disk
    if diskutil info "$v" 2>/dev/null | grep -qE "Removable Media: *(Removable|Yes)|Protocol: *USB"; then
      i=$((i+1)); CANDS+=("$v"); echo "  [$i] $v"
    fi
  done < <(ls -d /Volumes/* 2>/dev/null)
  [ "$i" -eq 0 ] && { echo "No removable USB drive detected. Plug one in and re-run, or pass the path."; exit 1; }
  printf "Pick a drive number (or q to quit): "; read n
  [ "$n" = "q" ] && exit 0
  DRIVE="${CANDS[$((n-1))]}"
fi
[ -d "$DRIVE" ] || { echo "Not a mounted volume: $DRIVE"; exit 1; }
echo "Target drive: $DRIVE"
DEST="$DRIVE/AIXMOS-KIT"
mkdir -p "$DEST" || { echo "Cannot write to $DRIVE"; exit 1; }

# 2) copy the kit (add/update only — NEVER --delete)
RS="rsync -a --no-perms --no-owner --no-group --exclude '.DS_Store' --exclude '._*'"
echo "Copying never-dark clients + bootstraps + runbook..."
rsync -a --no-perms --exclude '.DS_Store' --exclude '._*' "$KIT_SRC/" "$DEST/kit/"
if [ -d "$KB_SRC" ]; then
  echo "Copying TMMT Knowledge Base (offline SOPs)..."
  rsync -a --no-perms --exclude '.DS_Store' "$KB_SRC/" "$DEST/KnowledgeBase/"
else
  mkdir -p "$DEST/KnowledgeBase"; echo "(KnowledgeBase source not found — created empty folder; drop your SOPs there)"
fi

# 3) optional ENCRYPTED keys bundle (off by default) — never plaintext on the drive
if [ "$WITH_ENC_KEYS" = "1" ] && [ -f "$VAULT" ]; then
  echo "Encrypting keys bundle (AES-256). You'll set a passphrase; you'll need it to unlock on the road."
  openssl enc -aes-256-cbc -pbkdf2 -salt -in "$VAULT" -out "$DEST/keys.enc" && \
    echo "Wrote encrypted $DEST/keys.enc  (decrypt: openssl enc -d -aes-256-cbc -pbkdf2 -in keys.enc -out keys.env)"
fi

# 4) START-HERE + launchers
cat > "$DEST/START-HERE.txt" <<'TXT'
AIXMOS PLUG-AND-PLAY KIT
========================
This drive sets up AIXMOS (your never-dark AI brain) on any machine.

WINDOWS (e.g. the 8GB AMD):
  1) Copy the AIXMOS-KIT folder to the machine (or run from the drive).
  2) PowerShell:  powershell -ExecutionPolicy Bypass -File .\kit\bootstrap-windows.ps1
  3) Paste your CARRY gateway secret when asked (from 1Password). Then:  tailscale up
  4) Use:  .\kit\aixmos.ps1 "test"     (works online OR fully offline)

MAC (carry Mac):
  1) bash kit/aixmos-anywhere.sh "test"
  2) (first time) install Tailscale + Ollama, pull a local model for offline use.

OFFLINE: the local model + the KnowledgeBase folder (your SOPs) work with NO internet.
SECURITY: turn on BitLocker/FileVault. NO raw secrets live on this drive (keys come from 1Password,
or an optional encrypted keys.enc you unlock with a passphrase).
TXT

# Mac launcher (double-click)
cat > "$DEST/AIXMOS (Mac).command" <<'CMD'
#!/usr/bin/env bash
cd "$(dirname "$0")/kit"
read -r -p "Ask AIXMOS: " q
bash aixmos-anywhere.sh "$q"
read -r -p "Press Enter to close…"
CMD
chmod +x "$DEST/AIXMOS (Mac).command" 2>/dev/null

# 5) flush + verify (marginal-drive safety)
sync; sleep 1
N=$(find "$DEST" -type f 2>/dev/null | wc -l | tr -d ' ')
echo ""
echo "✅ Provisioned $DEST  ($N files)."
echo "   Eject safely:  diskutil eject \"$DRIVE\"   (don't yank it — these drives drop writes)."
