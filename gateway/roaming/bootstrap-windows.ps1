<#  AIXMOS Carry Device Bootstrap — 8GB Windows AMD (run in PowerShell as your user).
    Sets up the never-dark roaming brain: Tailscale + Ollama + a small offline model +
    the aixmos client + your env. NO secrets are stored in this file — it asks you.
    Run:  powershell -ExecutionPolicy Bypass -File .\bootstrap-windows.ps1
#>
$ErrorActionPreference = "Stop"
Write-Host "== AIXMOS carry-device bootstrap ==" -ForegroundColor Cyan

# 1) Tailscale (reach home hub + brain PC when you have internet)
if (-not (Get-Command tailscale -ErrorAction SilentlyContinue)) {
  Write-Host "Installing Tailscale..."; winget install -e --id Tailscale.Tailscale --accept-source-agreements --accept-package-agreements
}
Write-Host "After install: run 'tailscale up' and sign into the AIXMOS537 tailnet so this device can reach the brain." -ForegroundColor Yellow

# 2) Ollama (your LOCAL offline brain)
if (-not (Get-Command ollama -ErrorAction SilentlyContinue)) {
  Write-Host "Installing Ollama..."; winget install -e --id Ollama.Ollama --accept-source-agreements --accept-package-agreements
}
Write-Host "Pulling a small model that fits 8GB (works with NO internet once pulled)..."
Start-Process -NoNewWindow -Wait ollama -ArgumentList "pull","llama3.2:3b"   # ~2GB; swap to qwen2.5:3b if preferred

# 3) Lay down the client + a place for offline business docs
$AIX = "$env:USERPROFILE\AIXMOS"; New-Item -ItemType Directory -Force -Path $AIX | Out-Null
Copy-Item "$PSScriptRoot\aixmos.ps1" "$AIX\aixmos.ps1" -Force
New-Item -ItemType Directory -Force -Path "$AIX\KnowledgeBase" | Out-Null
Write-Host "Put your TMMT_Knowledge_Base (SOPs/playbooks) in $AIX\KnowledgeBase for OFFLINE reference."

# 4) Env config — secret is PROMPTED, never written to disk in plaintext by this script
[Environment]::SetEnvironmentVariable("AIXMOS_GATEWAY","https://aixmos-gateway.aixmos.workers.dev","User")
[Environment]::SetEnvironmentVariable("AIXMOS_BRAIN","http://100.64.0.1:11434","User")
[Environment]::SetEnvironmentVariable("AIXMOS_LOCAL","http://localhost:11434","User")
[Environment]::SetEnvironmentVariable("AIXMOS_LOCALMDL","llama3.2:3b","User")
$sec = Read-Host "Paste your CARRY gateway secret (from 1Password)"
[Environment]::SetEnvironmentVariable("AIXMOS_SECRET",$sec,"User")

Write-Host ""
Write-Host "DONE. Open a NEW PowerShell window, then:" -ForegroundColor Green
Write-Host '   tailscale up        # sign in once'
Write-Host '   cd $env:USERPROFILE\AIXMOS'
Write-Host '   .\aixmos.ps1 "AIXMOS online?"   # works online OR fully offline'
Write-Host ""
Write-Host "SECURITY: turn on BitLocker (Settings > Privacy & security > Device encryption) so a lost laptop's disk is useless." -ForegroundColor Yellow
