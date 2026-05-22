#!/usr/bin/env bash
# Create 60TB NAS folder tree on Mac-mounted NAS
set -euo pipefail
ROOT="${1:-${NAS_MOUNT_PATH:-$HOME/NAS/AI-OPS}}"

folders=(
  hot/knowledge hot/projects hot/voice-notes
  life/inbox life/inbox/processed life/tasks life/journal/recaps
  life/decisions life/meetings/transcripts life/meetings/actions
  life/comms/drafts life/relationships
  work/strategy work/tasks work/clients work/meetings work/projects
  knowledge/sops knowledge/policies knowledge/templates/comms knowledge/faq
  archive/life archive/work archive/media
  vault/exports backups/ai-ops models/ollama
  exports/open-webui exports/n8n
)

for f in "${folders[@]}"; do
  mkdir -p "$ROOT/$f"
  echo "[OK] $ROOT/$f"
done

cat > "$ROOT/README.md" <<'EOF'
# AI-OPS NAS (60TB)
System of record for Oracle, Operator, Counsel.
EOF
echo "NAS layout ready at $ROOT"
