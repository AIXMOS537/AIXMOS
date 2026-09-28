# AIXMOS - terminal chat (no browser)
# Reads profile from ~/.aixmos/state.json so lite stays on qwen2.5:1.5b.
$ErrorActionPreference = 'Continue'

$HostDir = Join-Path $env:USERPROFILE '.aixmos'
$StatePath = Join-Path $HostDir 'state.json'
$profile = 'full'
$preferred = 'tmmt-brain'
$fallback = 'llama3.2:3b'
if (Test-Path $StatePath) {
  $state = Get-Content $StatePath -Raw | ConvertFrom-Json
  if ($state.profile) { $profile = $state.profile }
  if ($state.default_model)  { $preferred = $state.default_model }
  if ($state.fallback_model) { $fallback  = $state.fallback_model }
}

try {
  Invoke-WebRequest -Uri "http://127.0.0.1:11434/api/tags" -TimeoutSec 1 -UseBasicParsing | Out-Null
} catch {
  Write-Host "Ollama isn't running. Starting it..."
  Start-Process -FilePath "ollama" -ArgumentList "serve" -WindowStyle Hidden
  Start-Sleep -Seconds 2
}

$models = (ollama list 2>$null) -join "`n"
$model = $preferred
if ($models -notmatch ("^" + [regex]::Escape($preferred))) {
  $model = $fallback
  Write-Host "  ($preferred not built - using $model)"
}

Write-Host "Profile: $profile  |  Chat with: $model"
Write-Host "Type /bye to exit."
Write-Host "---"
ollama run $model
