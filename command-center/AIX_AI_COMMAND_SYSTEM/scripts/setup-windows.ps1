# AIX AI Command System — Windows setup
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location $Root

Write-Host "AIX AI Command System — setup"
Write-Host "Project: $Root"

if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
    Write-Error "python not found. Install from https://www.python.org/downloads/"
}

python --version

if (-not (Test-Path .venv)) {
    python -m venv .venv
    Write-Host "Created virtual environment at .venv"
}

& .\.venv\Scripts\Activate.ps1
pip install -q -r requirements.txt
Write-Host "Installed Python dependencies"

if (-not (Test-Path .env)) {
    Copy-Item .env.example .env
    Write-Host "Created .env from .env.example — add your Airtable token and base ID."
} else {
    Write-Host ".env already exists — leaving it unchanged."
}

python aix_operator.py list | Select-Object -First 15

Write-Host ""
Write-Host "Done. Next: edit .env, then run: python aix_operator.py airtable list-templates"
Write-Host "See TEAM_DEPLOY.md for team rollout."
