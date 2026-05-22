#Requires -Version 5.1
<#
.SYNOPSIS
  Build versioned release zip for NAS, GitLab/GitHub, or Google Drive upload.
#>
param(
    [string]$ProjectRoot = "",
    [string]$OutputDir = "",
    [string]$Version = ""
)

$ErrorActionPreference = "Stop"
if (-not $ProjectRoot) {
    $ProjectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
}
$versionFile = Join-Path $ProjectRoot "VERSION"
if (-not $Version) {
    $Version = (Get-Content $versionFile -ErrorAction SilentlyContinue | Select-Object -First 1).Trim()
}
if (-not $Version) { $Version = "1.0.0" }

if (-not $OutputDir) {
    $OutputDir = Join-Path $ProjectRoot "dist"
}
New-Item -ItemType Directory -Force -Path $OutputDir | Out-Null

# Refresh installers before packaging
& (Join-Path $ProjectRoot "scripts\generate-installers.ps1") -ProjectRoot $ProjectRoot

$zipName = "AI-OPS-STARTER-v$Version.zip"
$zipPath = Join-Path $OutputDir $zipName
$staging = Join-Path $env:TEMP "ai-ops-staging-$Version"
if (Test-Path $staging) { Remove-Item $staging -Recurse -Force }
New-Item -ItemType Directory -Force -Path (Join-Path $staging "AI-OPS-STARTER") | Out-Null
$dest = Join-Path $staging "AI-OPS-STARTER"

Write-Host "Staging release v$Version ..." -ForegroundColor Cyan
robocopy $ProjectRoot $dest /MIR /XD data dist .git /XF .env /NFL /NDL /NJH /NJS | Out-Null
if ($LASTEXITCODE -ge 8) { throw "robocopy staging failed: $LASTEXITCODE" }

if (Test-Path $zipPath) { Remove-Item $zipPath -Force }
Compress-Archive -Path $dest -DestinationPath $zipPath -Force

$hash = (Get-FileHash $zipPath -Algorithm SHA256).Hash
$meta = @"
AI-OPS-STARTER release $Version
Built: $(Get-Date -Format o)
SHA256: $hash
Excludes: .env, data/
Upload to: flash releases\, NAS, GitLab Release, Google Drive
"@
Set-Content (Join-Path $OutputDir "AI-OPS-STARTER-v$Version.txt") $meta -Encoding UTF8

Write-Host "`nRelease ready:" -ForegroundColor Green
Write-Host "  $zipPath"
Write-Host "  $(Join-Path $OutputDir "AI-OPS-STARTER-v$Version.txt")"
Write-Host "`nNext: .\scripts\publish-to-nas.ps1 -ZipPath `"$zipPath`""
