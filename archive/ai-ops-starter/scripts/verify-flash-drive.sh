#!/usr/bin/env bash
# Verify flash drive contains full install kit (deploy order, registry, executives)
set -euo pipefail

KIT="${1:-/Volumes/AI-OPS/AI-OPS-STARTER}"
REQUIRED=(
  START-HERE-FLASH.md
  README.md
  docker-compose.yml
  .env.example
  install-windows.ps1
  install-mac.sh
  docs/DEPLOY-ORDER.md
  docs/team-roster.md
  docs/brainiac-7.md
  docs/brainiac-hierarchy.md
  docs/flash-drive-guide.md
  setup/operators/registry.yaml
  setup/tiers/brainiac-7.env.example
  agents/oracle.md
  agents/operator.md
  agents/counsel.md
  prompts/tier-preamble.md
  scripts/phase1-windows-bootstrap.ps1
  scripts/provision-brainiac-node.ps1
  scripts/provision-brainiac-node.sh
  scripts/init-nas-layout.ps1
  scripts/sync-registry-nas.ps1
  scripts/sync-to-flash.sh
  scripts/sync-to-flash.ps1
  n8n/team-question-sop-answer.json
  n8n/voice-memo-to-task.json
  n8n/inbound-message-draft-response.json
  docs/mobile-voice-command-center.md
  docs/auto-response-playbook.md
  setup/mac/MACBOOK-SETUP.md
  setup/phone/IPHONE-SETUP.md
  setup/phone/ios-voice-to-brainiac.md
  docs/TEAM-SELF-INSTALL.md
  VERSION
  scripts/installers/manifest.txt
)

echo "Verifying flash kit: $KIT"
MISS=0
for f in "${REQUIRED[@]}"; do
  if [[ -f "$KIT/$f" ]]; then
    echo "[OK] $f"
  else
    echo "[MISSING] $f"
    MISS=1
  fi
done

if [[ -d "$KIT/.git" ]]; then
  echo "[OK] .git/ (offline history)"
else
  echo "[WARN] .git missing — run sync from a machine with git repo"
fi

if [[ -f "$KIT/.env" ]]; then
  echo "[WARN] .env on flash — delete before distributing USB"
fi

cat > "$KIT/README-FLASH.txt" <<'EOF'
AI-OPS-STARTER — Flash Install Kit
==================================
OPEN FIRST: START-HERE-FLASH.md

Brainiac 7 (Taha):     docs\DEPLOY-ORDER.md  Phase 1
Dominique:             Phase 2
Michael + Dyson:       Phase 3
Nathan + Claryn (Ryn): Phase 4
Kayleigh:              Phase 5 (pending hire)
Superman / Superwoman: After Phase 4

Team registry: setup\operators\registry.yaml

1. Copy this folder to C:\AI-OPS-STARTER
2. Do NOT use .env from USB — copy .env.example to .env on each PC
3. Run commands in docs\DEPLOY-ORDER.md
4. Offline history: git log  (see docs\offline-git-history.md)
EOF

# Windows-visible autorun-style pointer (optional)
cat > "$KIT/OPEN-ME-FIRST.txt" <<'EOF'
Read START-HERE-FLASH.md
Deploy steps: docs\DEPLOY-ORDER.md
EOF

if [[ $MISS -eq 0 ]]; then
  echo ""
  echo "Flash drive kit COMPLETE (deploy order + registry included)"
  exit 0
else
  echo ""
  echo "Flash drive kit INCOMPLETE — re-run scripts/sync-to-flash.sh"
  exit 1
fi
