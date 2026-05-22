# WINDOWS FIRST COMMAND — full Phase 1 bootstrap
# Save as scripts\phase1-windows-bootstrap.ps1 or paste into PowerShell
$ErrorActionPreference = "Stop"
$root = "C:\AI-OPS-STARTER"
$flash = "E:\AI-OPS-STARTER"  # adjust drive letter

New-Item -ItemType Directory -Force -Path $root | Out-Null
if (Test-Path $flash) {
    Write-Host "Copying from flash $flash ..."
    robocopy $flash $root /E /XD data /XF .env | Out-Null
}

Set-Location $root

function Test-Tool($name, $script) {
    try { & $script | Out-Null; Write-Host "[OK] $name" -ForegroundColor Green; return $true }
    catch { Write-Host "[MISSING] $name" -ForegroundColor Red; return $false }
}

$ok = @(
    (Test-Tool "Docker" { docker version }),
    (Test-Tool "Ollama" { ollama --version }),
    (Test-Tool "Tailscale" { tailscale status })
) | Where-Object { $_ -eq $false }

if ($ok.Count -gt 0) {
    Write-Host "Install missing tools, then re-run." -ForegroundColor Yellow
    exit 1
}

if (-not (Test-Path .env)) { Copy-Item .env.example .env }
ollama pull qwen2.5:7b
ollama pull llama3.2
ollama pull nomic-embed-text
docker compose pull
docker compose up -d

Write-Host "`n=== Brainiac 7 online ===" -ForegroundColor Green
Write-Host "Phase 1 complete — primary intellect node ready." -ForegroundColor Cyan
Write-Host "Brainiac 7 (WebUI): http://127.0.0.1:3000"
Write-Host "n8n:                http://127.0.0.1:5678"
Write-Host "Next: docs\brainiac-7.md, first-run-checklist.md"
