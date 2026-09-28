$base = Split-Path -Parent $MyInvocation.MyCommand.Path
$python = Join-Path $base 'venv\Scripts\python.exe'
if (-not (Test-Path $python)) {
    Write-Host 'Python virtual environment not found. Run install_operator.ps1 first.' -ForegroundColor Red
    exit 1
}

Push-Location $base
& $python .\operator_dashboard.py
Pop-Location
