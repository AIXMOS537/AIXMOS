#Requires -Version 5.1
param([string]$ProjectRoot = "C:\AI-OPS-STARTER")

$ErrorActionPreference = "Stop"
Set-Location $ProjectRoot

Write-Host "Brainiac 7 — bringing intellect online..." -ForegroundColor Cyan
Write-Host "Starting Ollama (if not running)..." -ForegroundColor Cyan
$ollamaProc = Get-Process ollama -ErrorAction SilentlyContinue
if (-not $ollamaProc) {
    Start-Process "ollama" -ArgumentList "serve" -WindowStyle Hidden
    Start-Sleep -Seconds 3
}

Write-Host "Starting Docker stack..." -ForegroundColor Cyan
docker compose up -d

Write-Host "`n=== Brainiac 7 online ===" -ForegroundColor Green
Write-Host "Services (localhost only):" -ForegroundColor Green
Write-Host "  Brainiac 7 (WebUI):  http://127.0.0.1:3000"
Write-Host "  n8n:         http://127.0.0.1:5678"
Write-Host "  Qdrant:      http://127.0.0.1:6333/dashboard"
Write-Host "  Ollama:      http://127.0.0.1:11434"

$tsIp = tailscale ip -4 2>$null
if ($tsIp) {
    Write-Host "`nTailscale (from Mac/other devices):" -ForegroundColor Green
    Write-Host "  Brainiac 7:  http://brainiac-7:3000  (or http://${tsIp}:3000)"
    Write-Host "  n8n:         http://brainiac-7:5678  (or http://${tsIp}:5678)"
}
Write-Host "`nOpening line: Brainiac 7 online — Oracle, Operator, or Counsel?" -ForegroundColor Cyan

docker compose ps
