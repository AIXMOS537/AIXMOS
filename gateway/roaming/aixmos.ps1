<#  AIXMOS — never-dark client for the road (Windows).
    Tries, in order, and uses the first that answers:
      1) Cloud Gateway   (best; needs internet + funded premium)
      2) Brain PC Ollama (free; needs internet/Tailscale to home)
      3) LOCAL Ollama    (works with ZERO internet — your offline brain)
    Usage:   .\aixmos.ps1 "draft a check-in message for a Turo guest"
    Config (set once via bootstrap, or env vars):
      $env:AIXMOS_GATEWAY  = "https://aixmos-gateway.aixmos.workers.dev"
      $env:AIXMOS_SECRET   = "<your CARRY secret>"
      $env:AIXMOS_BRAIN    = "http://100.64.0.1:11434"   # brain PC over Tailscale
      $env:AIXMOS_LOCAL    = "http://localhost:11434"         # this device's Ollama
      $env:AIXMOS_LOCALMDL = "llama3.2:3b"                    # small model that fits 8GB
#>
param([Parameter(ValueFromRemainingArguments=$true)][string[]]$Prompt)
$ErrorActionPreference = "SilentlyContinue"
$text = ($Prompt -join " ").Trim()
if (-not $text) { Write-Host 'Usage: .\aixmos.ps1 "your prompt"'; exit 1 }

$GATEWAY = $env:AIXMOS_GATEWAY
$SECRET  = $env:AIXMOS_SECRET
$BRAIN   = if ($env:AIXMOS_BRAIN)    { $env:AIXMOS_BRAIN }    else { "http://100.64.0.1:11434" }
$LOCAL   = if ($env:AIXMOS_LOCAL)    { $env:AIXMOS_LOCAL }    else { "http://localhost:11434" }
$LMODEL  = if ($env:AIXMOS_LOCALMDL) { $env:AIXMOS_LOCALMDL } else { "llama3.2:3b" }
$BMODEL  = if ($env:AIXMOS_BRAINMDL) { $env:AIXMOS_BRAINMDL } else { "tmmt-brain:latest" }

function Try-Gateway {
  if (-not $GATEWAY -or -not $SECRET) { return $null }
  try {
    $body = @{ prompt = $text; max_tokens = 800 } | ConvertTo-Json
    $r = Invoke-RestMethod -Uri $GATEWAY -Method Post -TimeoutSec 25 `
         -Headers @{ "x-aixmos-auth" = $SECRET; "content-type" = "application/json" } -Body $body
    if ($r.error) { return $null }                      # e.g. unfunded premium -> fall through
    if ($r.content) { return ($r.content[0].text) }      # Anthropic shape
    if ($r.text)    { return $r.text }                   # free-lane shape
  } catch { return $null }
  return $null
}
function Try-Ollama($base, $model, $label) {
  try {
    $body = @{ model = $model; stream = $false; messages = @(@{ role="user"; content=$text }) } | ConvertTo-Json -Depth 5
    $r = Invoke-RestMethod -Uri "$base/api/chat" -Method Post -TimeoutSec 60 `
         -Headers @{ "content-type" = "application/json" } -Body $body
    if ($r.message.content) { return $r.message.content }
  } catch { return $null }
  return $null
}

$ans = Try-Gateway
if ($ans) { Write-Host "[lane: cloud gateway]" -ForegroundColor DarkGray; Write-Output $ans; exit 0 }
$ans = Try-Ollama $BRAIN $BMODEL "brain"
if ($ans) { Write-Host "[lane: home brain via Tailscale]" -ForegroundColor DarkGray; Write-Output $ans; exit 0 }
$ans = Try-Ollama $LOCAL $LMODEL "local"
if ($ans) { Write-Host "[lane: LOCAL offline brain]" -ForegroundColor DarkGray; Write-Output $ans; exit 0 }
Write-Host "AIXMOS is fully offline AND the local model isn't responding. Run: ollama serve  (and: ollama pull $LMODEL)" -ForegroundColor Yellow
exit 1
