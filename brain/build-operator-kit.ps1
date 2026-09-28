<#
  Build the Operator Kit — the shippable half of the business brain.

      .\build-operator-kit.ps1              build to .\dist\operator-kit
      .\build-operator-kit.ps1 -ToDrives    build, then copy to every stick
      .\build-operator-kit.ps1 -List        show what would ship, write nothing

  This is what a dealership or an individual operator receives on a bootable
  stick: how to run the business, not how TMMT runs its own.

  GENERATED, NEVER HAND-MAINTAINED. That is the whole point. A hand-kept copy
  drifts, and the day it drifts is the day something private rides along. The
  kit is rebuilt from the brain every time and the output folder is disposable.

  Three gates, all of which must pass before a file ships:

    1. ALLOWLIST, not blocklist. Only paths named in $SHIP go out. A new file in
       the brain ships when someone deliberately adds it here — never by
       default. A blocklist fails open, and failing open is how a family file
       reaches a customer.
    2. DOMAIN CHECK. Any file whose frontmatter says domain: family or
       domain: personal is refused even if listed.
    3. PII SCAN. Any file carrying an email address or phone number is refused.
       The brain is full of real people; the kit must not be.

  A refusal is a build failure, not a warning. Shipping is the risky direction.
#>

param(
  [Parameter(Position = 0)][string]$Mode = '',
  [switch]$ToDrives,
  [switch]$List
)

if ($Mode -match '^(list|dry|preview)$')  { $List = $true }
if ($Mode -match '^(drives|usb|sticks)$') { $ToDrives = $true }

$ErrorActionPreference = 'Stop'
$Root = $PSScriptRoot
$Out  = Join-Path $Root 'dist\operator-kit'

function Hd($t)  { Write-Host ''; Write-Host "  $t" -ForegroundColor Cyan; Write-Host "  $('-' * $t.Length)" -ForegroundColor DarkGray }
function Ok($t)  { Write-Host "  [ ship ] " -ForegroundColor Green  -NoNewline; Write-Host $t }
function No($t)  { Write-Host "  [ HELD ] " -ForegroundColor Red    -NoNewline; Write-Host $t }
function Note($t){ Write-Host "           $t" -ForegroundColor DarkGray }

# The kit. Everything here teaches an operator to run their own business.
# Anything about running TMMT specifically stays home.
$SHIP = @(
  'OPERATOR-OS-BLUEPRINT.md',
  'operator-os.md',
  'go-kit.md',
  'onboarding-offboarding.md',
  'closed-loop-ops.md',
  'local-ai-ollama.md',
  'device-architecture.md',
  'tablet-desktop-setup.md',
  'aixmos-kit-windows-bootstrap.md',
  'free-ram-atboot.md',
  'playbooks/README.md',
  'playbooks/rentals.md',
  'playbooks/sales-leasing.md',
  'playbooks/dispatch-fleet.md',
  'playbooks/detailing.md',
  'scorecards/operator-scorecard-template.md',
  'onboarding/README.md',
  'onboarding/overseas-assistant-template.md',
  'gokit/MAKE-A-DRIVE.md',
  'gokit/START-HERE.txt',
  'gokit/GO.html',
  'guides/NAS-Tailscale-clicks.md'
)

# Reads the domain: field out of YAML frontmatter, if there is any.
function Get-Domain([string]$path) {
  $inFm = $false
  foreach ($line in (Get-Content -LiteralPath $path -ErrorAction SilentlyContinue)) {
    if ($line -match '^---\s*$') { if ($inFm) { break } else { $inFm = $true; continue } }
    if ($inFm -and $line -match '^\s*domain:\s*(\S+)') { return $Matches[1] }
  }
  return ''
}

function Find-Pii([string]$path) {
  $hits = @()
  $text = Get-Content -LiteralPath $path -Raw -ErrorAction SilentlyContinue
  if (-not $text) { return $hits }
  # Deliberately not matching example.com or the aixmos/tmmt domains used in
  # templates — those are illustrative, and refusing them would make the gate
  # so noisy nobody would trust it.
  if ($text -match '[A-Za-z0-9._%+-]+@(?!example\.)(gmail|icloud|yahoo|outlook|hotmail)\.com') { $hits += 'email address' }
  if ($text -match '(?<!\d)(\+?1[-. ]?)?\(?\d{3}\)?[-. ]\d{3}[-. ]\d{4}(?!\d)')                 { $hits += 'phone number' }
  return $hits
}

Hd 'BUILD OPERATOR KIT'
Write-Host "  source: $Root" -ForegroundColor DarkGray
Write-Host "  output: $Out"  -ForegroundColor DarkGray

$shipped = 0; $held = 0; $missing = 0

if (-not $List) {
  if (Test-Path $Out) { Remove-Item $Out -Recurse -Force }
  New-Item -ItemType Directory -Path $Out -Force | Out-Null
}

Write-Host ''
foreach ($rel in $SHIP) {
  $src = Join-Path $Root $rel
  if (-not (Test-Path $src)) { No "$rel"; Note 'not in the brain - listed but missing'; $missing++; continue }

  $domain = Get-Domain $src
  if ($domain -in @('family', 'personal')) {
    No "$rel"; Note "frontmatter says domain: $domain"; $held++; continue
  }

  $pii = Find-Pii $src
  if ($pii.Count -gt 0) {
    No "$rel"; Note "contains $($pii -join ' and ') - strip it or drop it from the list"; $held++; continue
  }

  if (-not $List) {
    $dest = Join-Path $Out $rel
    New-Item -ItemType Directory -Path (Split-Path $dest -Parent) -Force | Out-Null
    Copy-Item $src $dest -Force
  }
  Ok $rel
  $shipped++
}

if (-not $List -and $shipped -gt 0) {
  $readme = @"
# Operator Kit

Everything you need to run your fleet as a business, on one stick.

Built $(Get-Date -Format 'yyyy-MM-dd') from the AIXMOS business brain. This
folder is generated - edits here are overwritten on the next build. Change the
brain instead.

## Start here

1. ``gokit/START-HERE.txt`` - plug in and go
2. ``OPERATOR-OS-BLUEPRINT.md`` - what the system is and how the pieces fit
3. ``playbooks/`` - the day-to-day for your line: rentals, sales and leasing,
   dispatch and fleet, detailing
4. ``scorecards/`` - how performance is measured, so you can see yourself improve

## If you are not eligible yet

Bring your own car or your own dealership and you can start earning now. If a
credit profile or a missing LLC is in the way, that is the other half of the
business: All In One Management Solutions works on the LLC, the personal credit
profile, and business credit, and you come back when the profile is ready.

## What is not in here

Anything specific to running TMMT itself, and anything about anyone's private
life. The build refuses to copy a file whose frontmatter marks it personal, or
that carries someone's email or phone number, and a refusal fails the build
rather than warning about it.
"@
  Set-Content -Path (Join-Path $Out 'README.md') -Value $readme -Encoding UTF8
}

Hd 'RESULT'
Write-Host "  shipped: $shipped   held: $held   missing: $missing"

if ($held -gt 0) {
  Write-Host ''
  Write-Host '  BUILD FAILED - a listed file was refused by a safety gate.' -ForegroundColor Red
  Write-Host '  Fix the file or remove it from $SHIP. Do not weaken the gate.' -ForegroundColor DarkGray
  Write-Host ''
  exit 1
}

if ($List) { Write-Host ''; Write-Host '  Nothing written. Drop -List to build.' -ForegroundColor DarkGray; Write-Host ''; return }

if ($ToDrives) {
  Hd 'COPY TO STICKS'
  $targets = Get-Volume |
    Where-Object { $_.DriveLetter -and "$($_.DriveLetter)" -ne 'C' } |
    Where-Object { Test-Path "$($_.DriveLetter):\TMMT-WORK" }
  if (-not $targets) { Write-Host '  No sticks attached.' -ForegroundColor Yellow }
  foreach ($t in $targets) {
    $dest = "$($t.DriveLetter):\OPERATOR-KIT"
    & robocopy $Out $dest /MIR /R:1 /W:1 /NFL /NDL /NJH /NJS | Out-Null
    if ($LASTEXITCODE -ge 8) { Write-Host "  [warn] $($t.DriveLetter): robocopy code $LASTEXITCODE" -ForegroundColor Yellow }
    else { Ok "$($t.DriveLetter): $($t.FileSystemLabel)  ->  $dest" }
  }
  # /MIR is right HERE and only here: the kit is generated output, so the stick
  # copy should match the build exactly. Nothing on the stick under
  # \OPERATOR-KIT is anyone's only copy.
}

Write-Host ''
Write-Host "  Kit ready: $Out" -ForegroundColor Green
Write-Host ''
