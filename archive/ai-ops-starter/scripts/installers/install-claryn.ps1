#Requires -Version 5.1
# AUTO-GENERATED — scripts/generate-installers.sh
# Operator: claryn

param(
    [switch]$InstallPrerequisites,
    [switch]$Force
)

$ErrorActionPreference = "Stop"
$Root = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
Set-Location $Root

if ($InstallPrerequisites) {
    & "$Root\scripts\install-prerequisites.ps1"
}

Write-Host "=== Claryn (Ryn / Mystique) ===" -ForegroundColor Cyan
& "$Root\scripts\provision-brainiac-node.ps1" -Tier 4 -Location hq -Operator claryn -DisplayName "Brainiac 4 — Claryn Troup (Mystique / Ryn)"
& "$Root\install-windows.ps1" -ProjectRoot $Root
