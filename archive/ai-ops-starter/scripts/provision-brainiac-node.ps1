#Requires -Version 5.1
<#
.SYNOPSIS
  Provision a Brainiac node at tier 1-7 (7 = supreme owner only on your PC).
.PARAMETER Tier
  Intellect tier 1-7. Use 7 only on owner machine.
.PARAMETER Location
  Location code for NAS paths (e.g. hq, wh-east).
.PARAMETER Operator
  Operator/node id (hostname suffix).
.PARAMETER DisplayName
  Open WebUI display name.
#>
param(
    [Parameter(Mandatory)][ValidateRange(1,7)][int]$Tier,
    [Parameter(Mandatory)][string]$Location,
    [Parameter(Mandatory)][string]$Operator,
    [string]$DisplayName = "",
    [string]$ProjectRoot = "C:\AI-OPS-STARTER",
    [string]$Upstream = "brainiac-7"
)

$ErrorActionPreference = "Stop"
Set-Location $ProjectRoot

$tierFile = Join-Path $ProjectRoot "setup\tiers\brainiac-$Tier.env.example"
if (-not (Test-Path $tierFile)) { throw "Missing tier template: $tierFile" }

$hostName = if ($Tier -eq 7) { "brainiac-7" } else { "brainiac-$Tier-$Operator" }
if (-not $DisplayName) {
    $DisplayName = if ($Tier -eq 7) { "Brainiac 7" } else { "Brainiac $Tier — $Location" }
}

# Base .env.example + tier overlay
$base = Get-Content (Join-Path $ProjectRoot ".env.example") -Raw
$tier = Get-Content $tierFile -Raw

$overlay = @"

# --- Provisioned $(Get-Date -Format o) ---
BRAINIAC_TIER=$Tier
BRAINIAC_NODE_ID=$hostName
BRAINIAC_LOCATION_CODE=$Location
BRAINIAC_OPERATOR_ID=$Operator
AI_OPS_HOST_NAME=$hostName
WEBUI_NAME=$DisplayName
NAS_LOCATION_PATH=locations\$Location
NAS_OPERATOR_PATH=locations\$Location\operators\$Operator
"@

if ($Tier -lt 7) {
    $overlay += @"

BRAINIAC_UPSTREAM_HOST=$Upstream
BRAINIAC_UPSTREAM_TIER=7
BRAINIAC_UPSTREAM_WEBUI_URL=http://${Upstream}:3000
"@
}

# Merge: start from .env.example, append tier file keys, then overlay
$envPath = Join-Path $ProjectRoot ".env"
Copy-Item (Join-Path $ProjectRoot ".env.example") $envPath -Force
Add-Content $envPath "`n# --- Tier $Tier ---`n$tier`n$overlay"

# Patch common keys in .env
(Get-Content $envPath) `
    -replace '(?m)^AI_OPS_HOST_NAME=.*', "AI_OPS_HOST_NAME=$hostName" `
    -replace '(?m)^WEBUI_NAME=.*', "WEBUI_NAME=$DisplayName" | Set-Content $envPath

Write-Host "Provisioned Brainiac tier $Tier" -ForegroundColor Cyan
Write-Host "  Hostname:  $hostName"
Write-Host "  WebUI:     $DisplayName"
Write-Host "  Location:  $Location"
Write-Host "  Operator:  $Operator"
if ($Tier -lt 7) { Write-Host "  Upstream:  $Upstream (Brainiac 7)" -ForegroundColor Yellow }
if ($Tier -eq 7) { Write-Host "  SUPREME node — no upstream" -ForegroundColor Green }
Write-Host "`nNext: rename Windows PC to '$hostName', run .\install-windows.ps1"
