#Requires -Version 5.1
# AUTO-GENERATED — scripts/generate-installers.sh
# Operator: dyson

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

Write-Host "=== Dyson ===" -ForegroundColor Cyan
& "$Root\scripts\provision-brainiac-node.ps1" -Tier 3 -Location hq -Operator dyson -DisplayName "Brainiac 3 — Mr Dyson"
& "$Root\install-windows.ps1" -ProjectRoot $Root
