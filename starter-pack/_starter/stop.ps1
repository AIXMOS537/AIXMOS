# AIXMOS Starter Pack — clean shutdown (Windows)
Write-Host "Stopping AIXMOS services..."

Get-Process -Name "open-webui*" -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue
Write-Host "[OK] Open WebUI stopped (if running)"

Get-Process -Name "brain-dump-agent*" -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue
Write-Host "[OK] Brain-dump agent stopped (if running)"

$ollama = Get-Process -Name "ollama" -ErrorAction SilentlyContinue
if ($ollama) {
  Write-Host "  Ollama is still running. Stop manually with: Stop-Process -Name ollama"
}

Write-Host "Done. Safe to unplug USB."
