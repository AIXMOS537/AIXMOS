# AIXMOS Starter Pack - start daily session (Windows)
# On LITE profile (8 GB AMD), skips Open WebUI auto-launch to avoid swap thrash.
$ErrorActionPreference = 'Stop'

$PackDir = if ($env:AIXMOS_PACK_DIR) { $env:AIXMOS_PACK_DIR } else { Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path) }
$HostDir = Join-Path $env:USERPROFILE '.aixmos'
$StatePath = Join-Path $HostDir 'state.json'

if (-not (Test-Path $StatePath)) {
  Write-Host "[X] AIXMOS isn't installed yet. Run option 1 first."
  exit 1
}
$state = Get-Content $StatePath -Raw | ConvertFrom-Json
$profile = if ($state.profile) { $state.profile } else { 'full' }

# Start Ollama if not up
try {
  Invoke-WebRequest -Uri "http://127.0.0.1:11434/api/tags" -TimeoutSec 1 -UseBasicParsing | Out-Null
} catch {
  Write-Host "Starting Ollama..."
  Start-Process -FilePath "ollama" -ArgumentList "serve" -WindowStyle Hidden
  for ($i=0; $i -lt 10; $i++) {
    Start-Sleep -Seconds 1
    try { Invoke-WebRequest -Uri "http://127.0.0.1:11434/api/tags" -TimeoutSec 1 -UseBasicParsing | Out-Null; break } catch {}
  }
}
Write-Host "[OK] Ollama on :11434"

if ($profile -eq 'lite') {
  Write-Host ""
  Write-Host "[i] LITE profile (8 GB tier) - skipping Open WebUI to stay out of swap."
  Write-Host "    Chat in terminal: choose menu option 5"
  Write-Host "    Or run:           ollama run $($state.default_model)"
  Write-Host ""
  Write-Host "AIXMOS is running. To stop: choose option 3."
  exit 0
}

# FULL profile - try Open WebUI
$OwuiVenv = Join-Path $PackDir '_runtime\open-webui\.venv\Scripts\open-webui.exe'
if (Test-Path $OwuiVenv) {
  Write-Host "Starting Open WebUI on :8080..."
  Start-Process -FilePath $OwuiVenv -ArgumentList "serve","--host","127.0.0.1","--port","8080" -WindowStyle Hidden
  Start-Sleep -Seconds 3
  Start-Process "http://127.0.0.1:8080"
  Write-Host "[OK] Open WebUI: http://127.0.0.1:8080"
} else {
  Write-Host "[!] Open WebUI not bundled on this drive. Use option 5 (Chat in terminal)."
}
Write-Host ""
Write-Host "AIXMOS is running. To stop: choose option 3 from the menu."
