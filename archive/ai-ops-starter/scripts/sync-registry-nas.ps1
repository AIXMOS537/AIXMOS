#Requires -Version 5.1
# Create NAS folders for each location/node in setup/operators/registry.yaml
param(
    [string]$RegistryPath = "C:\AI-OPS-STARTER\setup\operators\registry.yaml",
    [string]$NasRoot = ""
)

$ErrorActionPreference = "Stop"

if (-not $NasRoot) {
    if (Test-Path "W:\") { $NasRoot = "W:\" }
    elseif (Test-Path "Z:\") { $NasRoot = "Z:\" }
    else { throw "Map NAS to W: or Z: first, or pass -NasRoot" }
}

if (-not (Test-Path $RegistryPath)) {
    throw "Missing registry: $RegistryPath"
}

# Simple YAML parse for location codes (no PowerShell YAML module required)
$lines = Get-Content $RegistryPath
$codes = @()
foreach ($line in $lines) {
    if ($line -match '^\s+-\s+code:\s+(\S+)') { $codes += $Matches[1] }
}

$subfolders = @(
    "operators", "exports", "escalations",
    "operators\brainiac-7\inbox", "operators\brainiac-7\tasks"
)

foreach ($code in $codes) {
    foreach ($sub in $subfolders) {
        $p = Join-Path $NasRoot "locations\$code\$sub"
        New-Item -ItemType Directory -Force -Path $p | Out-Null
    }
    Write-Host "[OK] locations/$code"
}

# Supreme hot folder
New-Item -ItemType Directory -Force -Path (Join-Path $NasRoot "hot\brainiac-7\sessions") | Out-Null
New-Item -ItemType Directory -Force -Path (Join-Path $NasRoot "hot\brainiac-7\recaps") | Out-Null

Write-Host "`nNAS folders synced from registry ($($codes.Count) locations)."
