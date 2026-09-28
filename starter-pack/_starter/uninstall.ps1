# AIXMOS — remove host footprint
$HostDir = Join-Path $env:USERPROFILE '.aixmos'

Write-Host "This will remove:"
Write-Host "  - $HostDir (models + state, ~5 GB)"
Write-Host "  - tmmt-brain Ollama model"
Write-Host ""
Write-Host "It will NOT remove:"
Write-Host "  - Ollama itself (uninstall via Programs & Features)"
Write-Host "  - The USB drive"
Write-Host ""
$ans = Read-Host "Proceed? (y/N)"
if ($ans -notmatch "^[Yy]$") { Write-Host "Cancelled."; exit 0 }

if (Get-Command ollama -ErrorAction SilentlyContinue) {
  ollama rm tmmt-brain 2>$null
  Write-Host "[OK] Removed tmmt-brain model"
}
if (Test-Path $HostDir) {
  Remove-Item -Recurse -Force $HostDir
  Write-Host "[OK] Removed $HostDir"
}
Write-Host "Done."
