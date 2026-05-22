#Requires -Version 5.1
# AUTO-GENERATED — scripts/generate-installers.sh
# Operator: brainiac-7

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

Write-Host "=== Brainiac 7 — Phase 1 ===" -ForegroundColor Cyan
& "$Root\scripts\phase1-windows-bootstrap.ps1"
Write-Host "Next: .\scripts\init-nas-layout.ps1 ; .\scripts\sync-registry-nas.ps1" -ForegroundColor Yellow
