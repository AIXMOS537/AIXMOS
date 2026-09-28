#Requires -Version 5.1
# Sync full install kit to flash drive (Windows)
param(
    [string]$Source = "C:\AI-OPS-STARTER",
    [string]$FlashDrive = "E:"
)

$Dest = Join-Path $FlashDrive "AI-OPS-STARTER"
if (-not (Test-Path $FlashDrive)) { throw "Flash drive not found: $FlashDrive" }

& (Join-Path $Source "scripts\generate-installers.ps1") -ProjectRoot $Source

Write-Host "Syncing $Source -> $Dest"
robocopy $Source $Dest /MIR /XD data dist "setup\operators\generated" /XF .env /NFL /NDL /NJH /NJS
if ($LASTEXITCODE -ge 8) { throw "robocopy failed: $LASTEXITCODE" }

Write-Host "Flash synced. Open START-HERE-FLASH.md on the USB."
Write-Host "Deploy order: docs\DEPLOY-ORDER.md"
