#Requires -Version 5.1
# AUTO-GENERATED — scripts/generate-installers.sh
# Operator: dominique

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

Write-Host "=== Dominique ===" -ForegroundColor Cyan
& "$Root\scripts\provision-brainiac-node.ps1" -Tier 4 -Location hq -Operator dominique -DisplayName "Brainiac 4 — Dominique Bibbs"
& "$Root\install-windows.ps1" -ProjectRoot $Root
