# Copy AIXMOSXTMMT-OPS to flash drive labeled AIXMOS02 (or path you pass)
param(
  [string]$DriveLabel = "AIXMOS02",
  [string]$DestPath = "D:\AIXMOSXTMMT-OPS"
)

$ErrorActionPreference = "Stop"
$Source = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path

Write-Host "Source: $Source"

if ($DestPath -and (Test-Path (Split-Path $DestPath -Parent))) {
  $Dest = $DestPath
} elseif ($DestPath -and $DestPath -match '^[A-Z]:\\') {
  $Dest = $DestPath
  New-Item -ItemType Directory -Force -Path $Dest | Out-Null
} else {
  $vol = Get-Volume | Where-Object { $_.FileSystemLabel -eq $DriveLabel -and $_.DriveLetter }
  if (-not $vol) {
    Write-Host "Drive label '$DriveLabel' not found. Plug in USB and try again."
    Write-Host "Available volumes:"
    Get-Volume | Where-Object DriveLetter | Format-Table DriveLetter, FileSystemLabel
    exit 1
  }
  $letter = $vol.DriveLetter
  $Dest = "${letter}:\AIXMOSXTMMT-OPS"
}

Write-Host "Destination: $Dest"
New-Item -ItemType Directory -Force -Path $Dest | Out-Null

$exclude = @(
  "node_modules",
  "apps\clock\node_modules",
  "apps\clock\dist",
  ".env"
)

robocopy $Source $Dest /E /XD node_modules dist /XF .env /NFL /NDL /NJH /NJS /nc /ns /np
if ($LASTEXITCODE -ge 8) {
  Write-Error "robocopy failed with code $LASTEXITCODE"
  exit $LASTEXITCODE
}

Copy-Item (Join-Path $Source ".env.example") (Join-Path $Dest ".env.example") -Force

Write-Host ""
Write-Host "Done. Copied to: $Dest"
Write-Host "Next on this PC:"
Write-Host "  cd $Dest"
Write-Host "  .\scripts\setup-windows.ps1"
