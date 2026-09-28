# Download/refresh all models from Ollama registry.
$ErrorActionPreference = 'Stop'
$PackDir = if ($env:AIXMOS_PACK_DIR) { $env:AIXMOS_PACK_DIR } else { Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path) }

if (-not (Get-Command ollama -ErrorAction SilentlyContinue)) {
  Write-Host "[X] Ollama not installed. Install from https://ollama.com/download/windows"
  exit 1
}

try {
  Invoke-WebRequest -Uri "http://127.0.0.1:11434/api/tags" -TimeoutSec 1 -UseBasicParsing | Out-Null
} catch {
  Start-Process -FilePath "ollama" -ArgumentList "serve" -WindowStyle Hidden
  Start-Sleep -Seconds 3
}

Write-Host "=== Downloading AIXMOS model set ==="
$manifest = Get-Content (Join-Path $PackDir '_models\MANIFEST.json') -Raw | ConvertFrom-Json
foreach ($m in $manifest.models) {
  Write-Host ""
  Write-Host "-> ollama pull $($m.ollama_tag)"
  ollama pull $m.ollama_tag
}

$mf = Join-Path $PackDir '_brain\Modelfile.tmmt-brain'
if (Test-Path $mf) {
  Write-Host ""
  Write-Host "-> Building tmmt-brain..."
  ollama create tmmt-brain -f $mf
}

Write-Host ""
Write-Host "[OK] Done. All models present on host."
