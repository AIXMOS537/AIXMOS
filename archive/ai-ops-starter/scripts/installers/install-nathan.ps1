#Requires -Version 5.1
# AUTO-GENERATED — scripts/generate-installers.sh
# Operator: nathan

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

Write-Host "=== Nathan ===" -ForegroundColor Cyan
& "$Root\scripts\provision-brainiac-node.ps1" -Tier 3 -Location hq -Operator nathan -DisplayName "Brainiac 3 — Nathan West"
& "$Root\install-windows.ps1" -ProjectRoot $Root
