#Requires -Version 5.1
<#
.SYNOPSIS
  One command: generate installers, build zip, sync flash, optional NAS publish.
.DESCRIPTION
  Distribution priority: 1 Flash  2 NAS  3 GitLab/GitHub  4 Google Drive (manual upload)
#>
param(
    [string]$FlashDrive = "E:",
    [string]$NasRoot = "",
    [switch]$SkipFlash,
    [switch]$SkipNas,
    [switch]$SkipZip
)

$ErrorActionPreference = "Stop"
$ProjectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$Version = (Get-Content (Join-Path $ProjectRoot "VERSION") | Select-Object -First 1).Trim()

Write-Host "`n=== AI-OPS publish v$Version ===" -ForegroundColor Cyan
Write-Host "Channels: Flash (primary) -> NAS -> GitLab/GitHub -> Google Drive`n"

& (Join-Path $ProjectRoot "scripts\generate-installers.ps1") -ProjectRoot $ProjectRoot

if (-not $SkipZip) {
    & (Join-Path $ProjectRoot "scripts\build-release-zip.ps1") -ProjectRoot $ProjectRoot
}

if (-not $SkipFlash) {
    & (Join-Path $ProjectRoot "scripts\sync-to-flash.ps1") -Source $ProjectRoot -FlashDrive $FlashDrive
    $releasesOnFlash = Join-Path $FlashDrive "AI-OPS-RELEASES"
    New-Item -ItemType Directory -Force -Path $releasesOnFlash | Out-Null
    $zip = Join-Path $ProjectRoot "dist\AI-OPS-STARTER-v$Version.zip"
    if (Test-Path $zip) {
        Copy-Item $zip $releasesOnFlash -Force
        Copy-Item "$ProjectRoot\dist\AI-OPS-STARTER-v$Version.txt" $releasesOnFlash -ErrorAction SilentlyContinue
        Write-Host "Release zip on flash: $releasesOnFlash" -ForegroundColor Green
    }
}

if (-not $SkipNas -and $NasRoot) {
    & (Join-Path $ProjectRoot "scripts\publish-to-nas.ps1") -NasRoot $NasRoot
}

Write-Host @"

=== Done ===
Flash:     $FlashDrive\AI-OPS-STARTER  (+ AI-OPS-RELEASES\ zip)
NAS:       $(if ($NasRoot) { "$NasRoot\v$Version" } else { "(skipped — pass -NasRoot)" })
GitLab:    Upload dist\AI-OPS-STARTER-v$Version.zip to Project -> Releases -> v$Version
Drive:     Same zip to Shared drive; link in docs\TEAM-SELF-INSTALL.md

Team message: see docs\TEAM-SELF-INSTALL.md#message-template
"@ -ForegroundColor Cyan
