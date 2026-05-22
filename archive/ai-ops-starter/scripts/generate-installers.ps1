#Requires -Version 5.1
<#
.SYNOPSIS
  Generate per-operator install scripts and one-page guides from registry.yaml.
#>
param(
    [string]$ProjectRoot = "",
    [string]$RegistryPath = ""
)

$ErrorActionPreference = "Stop"
if (-not $ProjectRoot) {
    $ProjectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
}
if (-not $RegistryPath) {
    $RegistryPath = Join-Path $ProjectRoot "setup\operators\registry.yaml"
}

$installersDir = Join-Path $ProjectRoot "scripts\installers"
$guidesDir = Join-Path $ProjectRoot "docs\install-guides"
New-Item -ItemType Directory -Force -Path $installersDir, $guidesDir | Out-Null

$registry = Get-Content $RegistryPath -Raw

# --- Parse location nodes (tier, slug, display, flags) ---
$nodes = @()
$currentLocation = "hq"
foreach ($line in (Get-Content $RegistryPath)) {
    if ($line -match '^\s+-\s+code:\s+(\S+)') { $currentLocation = $Matches[1]; continue }
    if ($line -match '^\s+-\s+id:\s+(\S+)') {
        if ($script:currentNode) { $nodes += $script:currentNode }
        $script:currentNode = @{
            id = $Matches[1]
            location = $currentLocation
            tier = $null
            display_name = ""
            mode = ""
            status = ""
            rollout_phase = ""
        }
        continue
    }
    if (-not $script:currentNode) { continue }
    if ($line -match '^\s+tier:\s+(\d+)') { $script:currentNode.tier = [int]$Matches[1] }
    if ($line -match '^\s+display_name:\s+(.+)') { $script:currentNode.display_name = $Matches[1].Trim() }
    if ($line -match '^\s+mode:\s+(\S+)') { $script:currentNode.mode = $Matches[1] }
    if ($line -match '^\s+status:\s+(\S+)') { $script:currentNode.status = $Matches[1] }
    if ($line -match '^\s+rollout_phase:\s+(\S+)') { $script:currentNode.rollout_phase = $Matches[1] }
}
if ($script:currentNode) { $nodes += $script:currentNode }

function Get-OperatorSlug($id) {
    if ($id -eq "brainiac-7") { return "brainiac-7" }
    $parts = $id -split '-'
    if ($parts.Count -ge 4) { return $parts[-1] }
    return $id
}

# --- Parse provisioning commands ---
$prov = @{}
$provPending = @{}
$inProvisioning = $false
foreach ($line in (Get-Content $RegistryPath)) {
    if ($line -match '^provisioning:') { $inProvisioning = $true; continue }
    if ($inProvisioning -and $line -match '^[a-z_]') { $inProvisioning = $false }
    if (-not $inProvisioning) { continue }
    if ($line -match '^\s+(\w+):\s*$') { $script:provKey = $Matches[1]; continue }
    if ($line -match '^\s+command:\s+(.+)') {
        $cmd = $Matches[1].Trim()
        $slug = ($script:provKey -replace '^phase_\d+_', '' -replace '_pending$', '' -replace '_mystique$', '' -replace '_superman$', '' -replace '_superwoman$', '')
        if ($script:provKey -eq 'phase_1_taha') { $slug = 'brainiac-7' }
        $prov[$slug] = $cmd
        if ($script:provKey -match 'pending|do_not') { $provPending[$slug] = $true }
    }
    if ($line -match 'do_not_run_until') { $provPending[$slug] = $true }
}

function New-InstallScript($slug, $body, $pending) {
    $file = Join-Path $installersDir "install-$slug.ps1"
    $banner = @"
#Requires -Version 5.1
# AUTO-GENERATED — run: .\scripts\generate-installers.ps1 to refresh
# Operator: $slug | Source: setup\operators\registry.yaml
"@
    if ($pending) {
        $banner += @"

# *** PENDING — do not run until Muhammad Taha enables your rollout phase ***
"@
    }
    $header = @"

param(
    [switch]`$InstallPrerequisites,
    [switch]`$Force
)

`$ErrorActionPreference = "Stop"
`$Root = (Resolve-Path (Join-Path `$PSScriptRoot "..\..")).Path
Set-Location `$Root

"@
    if ($pending) {
        $header += @"
if (-not `$Force) {
    Write-Host "This operator is not active yet (pending hire / phase). Use -Force only when Taha approves." -ForegroundColor Red
    exit 1
}

"@
    }
    $header += @"
if (`$InstallPrerequisites) {
    & "`$Root\scripts\install-prerequisites.ps1"
}

"@
    Set-Content -Path $file -Value ($banner + $header + $body + "`n") -Encoding UTF8
    Write-Host "  install-$slug.ps1"
}

# Supreme node (Phase 1)
New-InstallScript "brainiac-7" @"
Write-Host "=== Brainiac 7 — Phase 1 (Muhammad Taha) ===" -ForegroundColor Cyan
& "`$Root\scripts\phase1-windows-bootstrap.ps1"
Write-Host "`nNext (on Brainiac 7):" -ForegroundColor Yellow
Write-Host "  .\scripts\init-nas-layout.ps1"
Write-Host "  .\scripts\sync-registry-nas.ps1"
Write-Host "  docs\brainiac-7.md"
"@ $false

# From provisioning commands
foreach ($entry in $prov.GetEnumerator()) {
    $slug = $entry.Key
    if ($slug -eq 'brainiac-7') { continue }
    $cmd = $entry.Value
    $pending = $provPending.ContainsKey($slug)
    $body = @"
Write-Host "=== Provisioning $slug ===" -ForegroundColor Cyan
& "`$Root\$($cmd.TrimStart('.\'))"
& "`$Root\install-windows.ps1" -ProjectRoot `$Root
Write-Host "`nOpen WebUI: http://127.0.0.1:3000" -ForegroundColor Green
Write-Host "Paste prompts\tier-preamble.md (set N = tier) + your executive from agents\"
"@
    New-InstallScript $slug $body $pending
}

# Optional / thin-client nodes from registry
foreach ($n in $nodes) {
    $slug = Get-OperatorSlug $n.id
    if ($n.mode -eq 'thin_client') {
        $file = Join-Path $installersDir "install-$slug-thin.ps1"
        @"
#Requires -Version 5.1
# AUTO-GENERATED thin client — browser only, no local Docker/Ollama
`$ErrorActionPreference = "Stop"
Write-Host "=== Thin client: $($n.display_name) ===" -ForegroundColor Cyan
Write-Host "1. Install Tailscale: https://tailscale.com/download"
Write-Host "2. Open: http://brainiac-7:3000"
Write-Host "3. Paste prompts\tier-preamble.md in Open WebUI (tier 2)"
Write-Host "See docs\TEAM-SELF-INSTALL.md section Thin client"
"@ | Set-Content $file -Encoding UTF8
        Write-Host "  install-$slug-thin.ps1"
    }
    # brainiac-6 optional office node
    if ($n.id -eq 'brainiac-6-hq-taha' -and -not $prov.ContainsKey('taha')) {
        $body = @"
Write-Host "=== HQ office node (Brainiac 6) ===" -ForegroundColor Cyan
& "`$Root\scripts\provision-brainiac-node.ps1" -Tier 6 -Location hq -Operator taha -DisplayName "Brainiac 6 — HQ (Muhammad Taha)"
& "`$Root\install-windows.ps1" -ProjectRoot `$Root
"@
        New-InstallScript "taha-hq" $body $false
    }
}

# --- Per-person markdown guides ---
$version = (Get-Content (Join-Path $ProjectRoot "VERSION") -ErrorAction SilentlyContinue) -join ""
if (-not $version) { $version = "1.0.0" }

$index = @("# Install guides (v$version)`n`n| Operator | Script |`n|----------|--------|`n"
foreach ($n in $nodes) {
    if ($n.tier -ge 3 -and $n.mode -ne 'thin_client') {
        $slug = Get-OperatorSlug $n.id
        if ($n.id -eq 'brainiac-7') { $slug = 'brainiac-7' }
        $scriptName = "install-$slug.ps1"
        if (-not (Test-Path (Join-Path $installersDir $scriptName))) { continue }
        $pending = if ($n.status -eq 'pending_hire') { ' **PENDING**' } else { '' }
        $guide = @"
# Install — $($n.display_name)

**Kit version:** $version  
**Your script:** ``scripts\installers\$scriptName``

## Before you start

1. Copy kit from **flash drive** (or NAS / GitLab zip) to ``C:\AI-OPS-STARTER``
2. Optional (Admin PowerShell): ``.\scripts\install-prerequisites.ps1``
3. Run **your** installer (normal user; Admin only if Docker asks):

``````powershell
cd C:\AI-OPS-STARTER
.\scripts\installers\$scriptName
``````

Or with prereqs in one step:

``````powershell
.\scripts\installers\$scriptName -InstallPrerequisites
``````

4. Open http://127.0.0.1:3000 when finished  
5. **Never** copy ``.env`` from USB, email, or Drive — the script creates it locally

## Need help?

- Full team guide: ``docs\TEAM-SELF-INSTALL.md``
- Deploy order: ``docs\DEPLOY-ORDER.md``
"@
        $guideFile = Join-Path $guidesDir "INSTALL-$slug.md"
        Set-Content $guideFile $guide -Encoding UTF8
        $index += "| $($n.display_name) | ``$scriptName`` |$pending`n"
    }
}
Set-Content (Join-Path $guidesDir "README.md") $index -Encoding UTF8

# Manifest for verify script
$manifest = Get-ChildItem $installersDir -Filter "install-*.ps1" | ForEach-Object { $_.Name }
Set-Content (Join-Path $installersDir "manifest.txt") ($manifest -join "`n") -Encoding UTF8

Write-Host "`nGenerated $($manifest.Count) installers + guides in docs\install-guides\" -ForegroundColor Green
