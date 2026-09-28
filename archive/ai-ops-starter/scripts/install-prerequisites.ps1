#Requires -Version 5.1
<#
.SYNOPSIS
  Install Docker Desktop, Ollama, and Tailscale via winget (one-time per PC).
.NOTES
  Run PowerShell as Administrator. Reboot if Docker prompts you to.
#>
param(
    [switch]$SkipDocker,
    [switch]$SkipOllama,
    [switch]$SkipTailscale
)

$ErrorActionPreference = "Stop"

function Test-Tool($name) {
    return [bool](Get-Command $name -ErrorAction SilentlyContinue)
}

function Install-WingetPackage($id, $label) {
    Write-Host "Installing $label ($id)..." -ForegroundColor Cyan
    winget install --id $id -e --accept-source-agreements --accept-package-agreements
}

if (-not (Get-Command winget -ErrorAction SilentlyContinue)) {
    Write-Host "winget not found. Install App Installer from Microsoft Store, or install tools manually:" -ForegroundColor Yellow
    Write-Host "  Docker:   https://www.docker.com/products/docker-desktop/"
    Write-Host "  Ollama:   https://ollama.com/download"
    Write-Host "  Tailscale: https://tailscale.com/download"
    exit 1
}

Write-Host "`n=== Brainiac prerequisites (winget) ===`n" -ForegroundColor Cyan

if (-not $SkipDocker -and -not (Test-Tool "docker")) {
    Install-WingetPackage "Docker.DockerDesktop" "Docker Desktop"
} else {
    Write-Host "[OK] Docker" -ForegroundColor Green
}

if (-not $SkipOllama -and -not (Test-Tool "ollama")) {
    Install-WingetPackage "Ollama.Ollama" "Ollama"
} else {
    Write-Host "[OK] Ollama" -ForegroundColor Green
}

if (-not $SkipTailscale -and -not (Test-Tool "tailscale")) {
    Install-WingetPackage "Tailscale.Tailscale" "Tailscale"
} else {
    Write-Host "[OK] Tailscale" -ForegroundColor Green
}

Write-Host "`nDone. Sign in to Tailscale, start Docker Desktop, then run your install-*.ps1 script.`n" -ForegroundColor Green
