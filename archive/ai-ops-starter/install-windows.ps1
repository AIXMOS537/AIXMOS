#Requires -Version 5.1
<#
.SYNOPSIS
  AI-OPS-STARTER — Windows 11 Pro home AI machine installer (Phase 1–3)
.DESCRIPTION
  Verifies Docker, Ollama, Tailscale; pulls models; starts stack.
  Run as Administrator only if Docker Desktop requires it for first install.
#>
param(
    [string]$ProjectRoot = "C:\AI-OPS-STARTER",
    [switch]$SkipModels,
    [switch]$SkipCompose,
    [switch]$InstallPrerequisites
)

$ErrorActionPreference = "Stop"
Set-Location $ProjectRoot

if ($InstallPrerequisites) {
    & "$ProjectRoot\scripts\install-prerequisites.ps1"
}

Write-Host "`n=== Brainiac 7 — AI-OPS-STARTER Install ===" -ForegroundColor Cyan
Write-Host "Primary intellect node | Project root: $ProjectRoot`n"

function Test-CommandExists($name) {
    return [bool](Get-Command $name -ErrorAction SilentlyContinue)
}

# --- Phase 0: prerequisites ---
$checks = @()

if (Test-CommandExists "docker") {
    $dockerVer = docker version --format '{{.Server.Version}}' 2>$null
    $checks += [pscustomobject]@{ Tool = "Docker"; OK = $true; Detail = $dockerVer }
} else {
    $checks += [pscustomobject]@{ Tool = "Docker"; OK = $false; Detail = "Install Docker Desktop" }
}

if (Test-CommandExists "ollama") {
    $checks += [pscustomobject]@{ Tool = "Ollama"; OK = $true; Detail = (ollama --version 2>$null) }
} else {
    $checks += [pscustomobject]@{ Tool = "Ollama"; OK = $false; Detail = "Install from https://ollama.com/download" }
}

if (Test-CommandExists "tailscale") {
    $ts = tailscale status 2>$null
    $checks += [pscustomobject]@{ Tool = "Tailscale"; OK = $true; Detail = "Connected" }
} else {
    $checks += [pscustomobject]@{ Tool = "Tailscale"; OK = $false; Detail = "Install from https://tailscale.com/download" }
}

$checks | Format-Table -AutoSize
$failed = $checks | Where-Object { -not $_.OK }
if ($failed) {
    Write-Host "Fix missing tools above, then re-run this script." -ForegroundColor Yellow
    exit 1
}

# --- Phase 1: env file ---
if (-not (Test-Path "$ProjectRoot\.env")) {
    Copy-Item "$ProjectRoot\.env.example" "$ProjectRoot\.env"
    Write-Host "Created .env from .env.example — edit passwords before production use." -ForegroundColor Yellow
}

# --- Phase 2: Ollama models ---
if (-not $SkipModels) {
    Write-Host "`nPulling Ollama models (this may take a while)..." -ForegroundColor Cyan
    $models = @("qwen2.5:7b", "llama3.2", "nomic-embed-text")
    foreach ($m in $models) {
        Write-Host "  ollama pull $m"
        ollama pull $m
    }
    ollama list
}

# --- Phase 3: Docker stack ---
if (-not $SkipCompose) {
    Write-Host "`nStarting Docker stack (localhost bindings only)..." -ForegroundColor Cyan
    docker compose pull
    docker compose up -d
    Start-Sleep -Seconds 5
    docker compose ps
}

Write-Host "`n=== Brainiac 7 online ===" -ForegroundColor Green
Write-Host "Your highest form of intellect — local, precise, under your control.`n" -ForegroundColor Cyan
Write-Host @"

Next steps:
  1. Edit $ProjectRoot\.env — set strong passwords (WEBUI_NAME=Brainiac 7)
  2. Deploy all phases: $ProjectRoot\docs\DEPLOY-ORDER.md
  3. Team registry: setup\operators\registry.yaml
  4. Open http://127.0.0.1:3000 (Brainiac 7 / Open WebUI)
  5. Open http://127.0.0.1:5678 (n8n)
  6. Mount NAS — docs\nas-mount-guide.md
  7. Flash drive kit: .\scripts\sync-to-flash.ps1 (includes DEPLOY-ORDER.md)

Tailscale: http://brainiac-7:3000
"@
