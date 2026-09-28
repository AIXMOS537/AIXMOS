# AIXMOS Starter Pack - health check (Windows)
$PackDir = if ($env:AIXMOS_PACK_DIR) { $env:AIXMOS_PACK_DIR } else { Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path) }
$HostDir = Join-Path $env:USERPROFILE '.aixmos'
$StatePath = Join-Path $HostDir 'state.json'

function Pass($m) { Write-Host "  [OK] $m" -ForegroundColor Green }
function Fail($m) { Write-Host "  [X]  $m" -ForegroundColor Red }
function Warn($m) { Write-Host "  [!]  $m" -ForegroundColor Yellow }

Write-Host ""
Write-Host "=== AIXMOS Doctor ==="
Write-Host ""

# 0. Profile
$profile = 'unknown'
$preferred = 'tmmt-brain'
if (Test-Path $StatePath) {
  Pass "Install state present"
  $state = Get-Content $StatePath -Raw | ConvertFrom-Json
  if ($state.profile) { $profile = $state.profile }
  if ($state.default_model) { $preferred = $state.default_model }
  Pass "Profile: $profile (default model: $preferred)"
} else {
  Fail "Not installed. Run LAUNCH option 1."
}

# 1. RAM + CPU
$ramGB = [math]::Round((Get-CimInstance Win32_ComputerSystem).TotalPhysicalMemory / 1GB, 0)
$cpu = (Get-CimInstance Win32_Processor | Select-Object -First 1).Name
if ($ramGB -ge 8) { Pass "RAM: $ramGB GB  CPU: $cpu" } else { Fail "RAM $ramGB GB (need 8+)" }

# 2. Disk
$drv = (Get-Item $env:USERPROFILE).PSDrive
$freeGB = [math]::Round($drv.Free / 1GB, 0)
if ($freeGB -ge 3) { Pass "Disk free: $freeGB GB" } else { Fail "Disk free $freeGB GB (need 3+)" }

# 3. Ollama binary
if (Get-Command ollama -ErrorAction SilentlyContinue) {
  Pass ("Ollama installed: " + (ollama --version 2>&1 | Select-Object -First 1))
} else {
  Fail "Ollama missing. Install from https://ollama.com/download/windows"
}

# 4. Ollama service
try {
  $tags = Invoke-WebRequest -Uri "http://127.0.0.1:11434/api/tags" -TimeoutSec 1 -UseBasicParsing | Select-Object -ExpandProperty Content | ConvertFrom-Json
  Pass "Ollama service running on :11434"
  Write-Host ("      Models: " + (($tags.models | ForEach-Object { $_.name }) -join ", "))
} catch { Warn "Ollama not running. Start with: ollama serve" }

# 5. Brain model present (per profile)
$models = (ollama list 2>$null) -join "`n"
if ($models -match ("^" + [regex]::Escape($preferred))) {
  Pass "$preferred model present"
} else {
  Warn "$preferred not built. Re-run option 1."
}
# Profile-required base model check
$baseRequired = if ($profile -eq 'lite') { 'qwen2.5:1.5b' } else { 'llama3.2:3b' }
if ($models -match ("^" + [regex]::Escape($baseRequired))) {
  Pass "$baseRequired (profile base) pulled"
} else {
  Warn "$baseRequired NOT pulled - $profile profile incomplete"
}

# 6. Ports (only show OWUI if full profile)
$portsToCheck = if ($profile -eq 'lite') { @(11434) } else { @(11434, 8080, 7780) }
foreach ($port in $portsToCheck) {
  $listening = Get-NetTCPConnection -State Listen -LocalPort $port -ErrorAction SilentlyContinue
  if ($listening) { Pass "Port $port listening" } else { Warn "Port $port not in use" }
}

# 7. OWUI bundled (only meaningful for full)
if ($profile -ne 'lite') {
  if (Test-Path (Join-Path $PackDir '_runtime\open-webui\.venv\Scripts\open-webui.exe')) {
    Pass "Open WebUI bundled"
  } else {
    Warn "Open WebUI NOT bundled (terminal chat works via option 5)"
  }
}

Write-Host ""
Write-Host "Done. Copy this output if asking for help."
