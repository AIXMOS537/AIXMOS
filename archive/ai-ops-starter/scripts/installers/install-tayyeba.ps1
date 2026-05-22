#Requires -Version 5.1
# AUTO-GENERATED — scripts/generate-installers.sh
# Operator: tayyeba

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

Write-Host "=== Superwoman ===" -ForegroundColor Cyan
& "$Root\scripts\provision-brainiac-node.ps1" -Tier 5 -Location hq -Operator tayyeba -DisplayName "Brainiac 5 — Tayyeba Tahir (Superwoman)"
& "$Root\install-windows.ps1" -ProjectRoot $Root
