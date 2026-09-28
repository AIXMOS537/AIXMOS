#Requires -Version 5.1
<#
.SYNOPSIS
  Copy release zip + install guides to UGREEN NAS (secondary channel after flash).
#>
param(
    [string]$ZipPath = "",
    [string]$NasRoot = "\\UGREEN-NAS\AI-OPS\releases",
    [string]$Version = ""
)

$ErrorActionPreference = "Stop"
$ProjectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path

if (-not $Version) {
    $Version = (Get-Content (Join-Path $ProjectRoot "VERSION") -ErrorAction SilentlyContinue | Select-Object -First 1).Trim()
}
if (-not $Version) { $Version = "1.0.0" }

if (-not $ZipPath) {
    $ZipPath = Join-Path $ProjectRoot "dist\AI-OPS-STARTER-v$Version.zip"
}

if (-not (Test-Path $ZipPath)) {
    Write-Host "Zip not found. Building..." -ForegroundColor Yellow
    & (Join-Path $ProjectRoot "scripts\build-release-zip.ps1")
}

$dest = Join-Path $NasRoot "v$Version"
if (-not (Test-Path $NasRoot)) {
    Write-Host "NAS not reachable at $NasRoot" -ForegroundColor Red
    Write-Host "Map drive first: net use W: \\UGREEN-NAS\AI-OPS"
    Write-Host "Or set -NasRoot to your share path."
    exit 1
}

New-Item -ItemType Directory -Force -Path $dest | Out-Null
Copy-Item $ZipPath $dest -Force
Copy-Item (Join-Path $ProjectRoot "dist\AI-OPS-STARTER-v$Version.txt") $dest -ErrorAction SilentlyContinue

$guides = Join-Path $ProjectRoot "docs\install-guides"
if (Test-Path $guides) {
    Copy-Item "$guides\INSTALL-*.md" $dest -Force
    Copy-Item "$guides\README.md" (Join-Path $dest "INSTALL-INDEX.md") -Force
}

Write-Host "Published to $dest" -ForegroundColor Green
Write-Host "LAN path: $dest\AI-OPS-STARTER-v$Version.zip"
