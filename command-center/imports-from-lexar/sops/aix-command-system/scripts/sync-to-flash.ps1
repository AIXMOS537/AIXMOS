# Sync project to LEXAR flash drive (Windows). Run before ejecting the drive.
param(
    [string]$DriveLetter = "D",
    [string]$Label = "LEXAR"
)

$src = Split-Path $PSScriptRoot -Parent

$dst = "${DriveLetter}:\aix-command-system"
$vol = Get-Volume -DriveLetter $DriveLetter -ErrorAction SilentlyContinue

if (-not $vol) {
    $removable = Get-Volume | Where-Object { $_.DriveType -eq 'Removable' -and $_.DriveLetter }
    if ($removable.Count -eq 1) {
        $DriveLetter = $removable.DriveLetter
        $dst = "${DriveLetter}:\aix-command-system"
        $vol = $removable
    } else {
        Write-Error "Flash drive not found at ${DriveLetter}:. Plug in the drive and try again."
        exit 1
    }
}

Write-Host "Syncing $src -> $dst"
robocopy $src $dst /MIR /XD __pycache__ .venv venv /XF .env /NFL /NDL /NJH /NJS | Out-Null
if ($LASTEXITCODE -ge 8) { exit $LASTEXITCODE }

Write-Host "Done. Safely eject $Label (${DriveLetter}:) before unplugging."
Write-Host "On Mac: open /Volumes/$Label/aix-command-system in Cursor"
