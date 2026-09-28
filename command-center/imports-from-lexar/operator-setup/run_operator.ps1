$base = Split-Path -Parent $MyInvocation.MyCommand.Path
$venv = Join-Path $base 'venv'
$python = Join-Path $venv 'Scripts\python.exe'
if (-not (Test-Path $python)) {
    Write-Host 'Python virtual environment not found. Run install_operator.ps1 first.' -ForegroundColor Red
    exit 1
}

$workspace = Resolve-Path (Join-Path $base '..\mentorship')
if (-not (Test-Path $workspace)) {
    Write-Host 'Mentorship folder not found. Ensure this drive is plugged in and the repo path is correct.' -ForegroundColor Red
    exit 1
}

Push-Location $workspace
Write-Host 'Starting the mentorship operator workspace...' -ForegroundColor Green
& $python .\cli.py --prompt daily
Write-Host "`nTo view the 90-day plan, run:`n& $python .\cli.py --plan"
Pop-Location
