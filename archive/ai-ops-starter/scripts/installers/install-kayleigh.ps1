#Requires -Version 5.1
# AUTO-GENERATED — scripts/generate-installers.sh
# Operator: kayleigh
# *** PENDING — do not run until Muhammad Taha approves ***

param(
    [switch]$InstallPrerequisites,
    [switch]$Force
)

$ErrorActionPreference = "Stop"
$Root = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
Set-Location $Root

if (-not $Force) {
    Write-Host "Not active yet. Use -Force only when Taha approves." -ForegroundColor Red
    exit 1
}

if ($InstallPrerequisites) {
    & "$Root\scripts\install-prerequisites.ps1"
}

Write-Host "=== Kayleigh (pending hire) ===" -ForegroundColor Cyan
& "$Root\scripts\provision-brainiac-node.ps1" -Tier 5 -Location hq -Operator kayleigh -DisplayName "Brainiac 5 — Kayleigh Bristow"
& "$Root\install-windows.ps1" -ProjectRoot $Root
