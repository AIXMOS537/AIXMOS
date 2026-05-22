$base = Split-Path -Parent $MyInvocation.MyCommand.Path
$venvDir = Join-Path $base 'venv'

function Get-PythonExe {
    if (Get-Command py -ErrorAction SilentlyContinue) {
        return (py -3 -c "import sys; print(sys.executable)").Trim()
    }
    if (Get-Command python -ErrorAction SilentlyContinue) {
        return (python -c "import sys; print(sys.executable)").Trim()
    }
    return $null
}

$pythonExe = Get-PythonExe
if (-not $pythonExe) {
    Write-Host 'Python not found. Please install Python 3.11+ first.' -ForegroundColor Yellow
    exit 1
}

if (-not (Test-Path $venvDir)) {
    Write-Host "Creating venv at $venvDir"
    & $pythonExe -m venv $venvDir
}

$pipExe = Join-Path $venvDir 'Scripts\pip.exe'
if (-not (Test-Path $pipExe)) {
    Write-Host 'Failed to create virtual environment.' -ForegroundColor Red
    exit 1
}

& $pipExe install --upgrade pip
& $pipExe install -r (Join-Path $base 'operator_requirements.txt')

Write-Host 'Installation complete.' -ForegroundColor Green
Write-Host 'Run the operator launcher:'
Write-Host "powershell -ExecutionPolicy Bypass -File '$base\run_operator.ps1'"
