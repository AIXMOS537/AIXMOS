#Requires -Version 5.1
# AUTO-GENERATED — scripts/generate-installers.sh
# Operator: taha-hq

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

Write-Host "=== HQ office (Brainiac 6) ===" -ForegroundColor Cyan
& "$Root\scripts\provision-brainiac-node.ps1" -Tier 6 -Location hq -Operator taha -DisplayName "Brainiac 6 — HQ (Muhammad Taha)"
& "$Root\install-windows.ps1" -ProjectRoot $Root
