#!/usr/bin/env bash
# Generate install-*.ps1 when pwsh is not available (Mac admin)
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
DIR="$ROOT/scripts/installers"
GUIDES="$ROOT/docs/install-guides"
VERSION="$(head -1 "$ROOT/VERSION" 2>/dev/null || echo 1.0.0)"
mkdir -p "$DIR" "$GUIDES"

write_install() {
  local slug="$1" pending="$2" body="$3"
  local file="$DIR/install-${slug}.ps1"
  {
    echo "#Requires -Version 5.1"
    echo "# AUTO-GENERATED — scripts/generate-installers.sh"
    echo "# Operator: $slug"
    if [[ "$pending" == "1" ]]; then
      echo "# *** PENDING — do not run until Muhammad Taha approves ***"
    fi
    cat <<'HDR'

param(
    [switch]$InstallPrerequisites,
    [switch]$Force
)

$ErrorActionPreference = "Stop"
$Root = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
Set-Location $Root

HDR
    if [[ "$pending" == "1" ]]; then
      cat <<'PEND'
if (-not $Force) {
    Write-Host "Not active yet. Use -Force only when Taha approves." -ForegroundColor Red
    exit 1
}

PEND
    fi
    cat <<'PRE'
if ($InstallPrerequisites) {
    & "$Root\scripts\install-prerequisites.ps1"
}

PRE
    echo "$body"
  } > "$file"
  echo "  install-${slug}.ps1"
}

write_install "brainiac-7" 0 'Write-Host "=== Brainiac 7 — Phase 1 ===" -ForegroundColor Cyan
& "$Root\scripts\phase1-windows-bootstrap.ps1"
Write-Host "Next: .\scripts\init-nas-layout.ps1 ; .\scripts\sync-registry-nas.ps1" -ForegroundColor Yellow'

write_install "dominique" 0 'Write-Host "=== Dominique ===" -ForegroundColor Cyan
& "$Root\scripts\provision-brainiac-node.ps1" -Tier 4 -Location hq -Operator dominique -DisplayName "Brainiac 4 — Dominique Bibbs"
& "$Root\install-windows.ps1" -ProjectRoot $Root'

write_install "michael" 0 'Write-Host "=== Michael ===" -ForegroundColor Cyan
& "$Root\scripts\provision-brainiac-node.ps1" -Tier 4 -Location hq -Operator michael -DisplayName "Brainiac 4 — Mr Michael"
& "$Root\install-windows.ps1" -ProjectRoot $Root'

write_install "dyson" 0 'Write-Host "=== Dyson ===" -ForegroundColor Cyan
& "$Root\scripts\provision-brainiac-node.ps1" -Tier 3 -Location hq -Operator dyson -DisplayName "Brainiac 3 — Mr Dyson"
& "$Root\install-windows.ps1" -ProjectRoot $Root'

write_install "nathan" 0 'Write-Host "=== Nathan ===" -ForegroundColor Cyan
& "$Root\scripts\provision-brainiac-node.ps1" -Tier 3 -Location hq -Operator nathan -DisplayName "Brainiac 3 — Nathan West"
& "$Root\install-windows.ps1" -ProjectRoot $Root'

write_install "claryn" 0 'Write-Host "=== Claryn (Ryn / Mystique) ===" -ForegroundColor Cyan
& "$Root\scripts\provision-brainiac-node.ps1" -Tier 4 -Location hq -Operator claryn -DisplayName "Brainiac 4 — Claryn Troup (Mystique / Ryn)"
& "$Root\install-windows.ps1" -ProjectRoot $Root'

write_install "kayleigh" 1 'Write-Host "=== Kayleigh (pending hire) ===" -ForegroundColor Cyan
& "$Root\scripts\provision-brainiac-node.ps1" -Tier 5 -Location hq -Operator kayleigh -DisplayName "Brainiac 5 — Kayleigh Bristow"
& "$Root\install-windows.ps1" -ProjectRoot $Root'

write_install "tahir" 0 'Write-Host "=== Superman ===" -ForegroundColor Cyan
& "$Root\scripts\provision-brainiac-node.ps1" -Tier 5 -Location hq -Operator tahir -DisplayName "Brainiac 5 — Tahir Muhammad (Superman)"
& "$Root\install-windows.ps1" -ProjectRoot $Root'

write_install "tayyeba" 0 'Write-Host "=== Superwoman ===" -ForegroundColor Cyan
& "$Root\scripts\provision-brainiac-node.ps1" -Tier 5 -Location hq -Operator tayyeba -DisplayName "Brainiac 5 — Tayyeba Tahir (Superwoman)"
& "$Root\install-windows.ps1" -ProjectRoot $Root'

write_install "taha-hq" 0 'Write-Host "=== HQ office (Brainiac 6) ===" -ForegroundColor Cyan
& "$Root\scripts\provision-brainiac-node.ps1" -Tier 6 -Location hq -Operator taha -DisplayName "Brainiac 6 — HQ (Muhammad Taha)"
& "$Root\install-windows.ps1" -ProjectRoot $Root'

cat > "$DIR/install-shared-thin.ps1" <<'THIN'
#Requires -Version 5.1
# Thin client — no local Docker/Ollama
Write-Host "=== Thin client (HQ Shared) ===" -ForegroundColor Cyan
Write-Host "1. Install Tailscale: https://tailscale.com/download"
Write-Host "2. Open: http://brainiac-7:3000"
Write-Host "3. Paste prompts\tier-preamble.md in Open WebUI (tier 2)"
THIN
echo "  install-shared-thin.ps1"

find "$DIR" -maxdepth 1 -name 'install-*.ps1' -exec basename {} \; | sort > "$DIR/manifest.txt"

# Minimal guides
for pair in \
  "dominique|Brainiac 4 — Dominique Bibbs" \
  "michael|Brainiac 4 — Mr Michael" \
  "dyson|Brainiac 3 — Mr Dyson" \
  "nathan|Brainiac 3 — Nathan West" \
  "claryn|Brainiac 4 — Claryn Troup (Mystique / Ryn)" \
  "brainiac-7|Brainiac 7 — Muhammad Taha"; do
  slug="${pair%%|*}"
  name="${pair##*|}"
  cat > "$GUIDES/INSTALL-${slug}.md" <<EOF
# Install — $name

**Version:** $VERSION  
**Script:** \`scripts\\installers\\install-${slug}.ps1\`

\`\`\`powershell
cd C:\\AI-OPS-STARTER
.\\scripts\\installers\\install-${slug}.ps1
\`\`\`

See \`docs\\TEAM-SELF-INSTALL.md\`.
EOF
done

echo ""
echo "Generated installers in scripts/installers/ (bash fallback)"
