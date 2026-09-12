<#
  paths.ps1 - the only place that knows where anything lives.

  Every script sources this instead of hardcoding a path. That is the whole
  point: on 2026-09-01 eight separate scripts still pointed at the
  retired TMMT folder, whose .git had been removed weeks earlier.
  Each one had to be found and fixed by hand. With one map, repointing a lane
  is a single edit to kit.json and every caller follows.

  Resolves identically whether the kit sits on C:, on a flashdrive, or in a
  bootable image - so a script written here runs unchanged on all three.
#>

$script:KitRoot  = Split-Path $PSScriptRoot -Parent
$script:KitFile  = Join-Path $KitRoot 'kit.json'
$script:Kit      = Get-Content $KitFile -Raw | ConvertFrom-Json

# Which shape are we running in? The kit living under a user profile means this
# is the installed copy; anywhere else means we booted or plugged in, and the
# lanes take their on-drive layout instead.
$script:KitMode  = if ($KitRoot -like '*:\Users\*') { 'local' } else { 'portable' }
# Either way the workspace is the folder the kit sits in: the profile when
# installed, the drive root on a stick, the staging folder while a stick is built.
$script:Workspace = Split-Path $KitRoot -Parent

function Get-KitLane {
    <# Absolute path for a lane name. Get-KitLane canon #>
    param([Parameter(Mandatory)][string]$Name)
    $lane = $Kit.lanes.$Name
    if (-not $lane) { throw "Unknown lane '$Name'. Known: $($Kit.lanes.PSObject.Properties.Name -join ', ')" }
    $rel = if ($KitMode -eq 'local') { $lane.local } else { $lane.drive }
    if (-not $rel) { $rel = $lane.local }
    Join-Path $Workspace ($rel -replace '/', '\')
}

function Test-KitLane { param([Parameter(Mandatory)][string]$Name); Test-Path (Get-KitLane $Name) }

function Get-KitLanes { $Kit.lanes.PSObject.Properties.Name }

function Get-KitRetired {
    # Dead paths, so a caller can warn instead of silently doing nothing.
    foreach ($r in $Kit.retired) {
        [pscustomobject]@{
            Path       = (Join-Path $Workspace ($r.path -replace '/', '\'))
            Reason     = $r.reason
            ReplacedBy = $r.replacedBy
        }
    }
}

function Get-KitInfo {
    [pscustomobject]@{
        KitRoot   = $KitRoot
        Mode      = $KitMode
        Workspace = $Workspace
        Version   = $Kit.version
    }
}
