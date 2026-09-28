#Requires -Version 5.1
# AUTO-GENERATED — scripts/generate-installers.sh
# Operator: tahir

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

Write-Host "=== Superman ===" -ForegroundColor Cyan
& "$Root\scripts\provision-brainiac-node.ps1" -Tier 5 -Location hq -Operator tahir -DisplayName "Brainiac 5 — Tahir Muhammad (Superman)"
& "$Root\install-windows.ps1" -ProjectRoot $Root
