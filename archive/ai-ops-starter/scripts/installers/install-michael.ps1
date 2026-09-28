#Requires -Version 5.1
# AUTO-GENERATED — scripts/generate-installers.sh
# Operator: michael

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

Write-Host "=== Michael ===" -ForegroundColor Cyan
& "$Root\scripts\provision-brainiac-node.ps1" -Tier 4 -Location hq -Operator michael -DisplayName "Brainiac 4 — Mr Michael"
& "$Root\install-windows.ps1" -ProjectRoot $Root
