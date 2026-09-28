# AIXMOS Starter Pack - Windows installer
# Run from LAUNCH.cmd menu option 1.
# Auto-tunes for 8 GB AMD machines (TRAPTOP profile): LITE = qwen2.5:1.5b only,
# tmmt-brain-lite at 4K context, no OWUI auto-launch.

$ErrorActionPreference = 'Stop'

$PackDir = if ($env:AIXMOS_PACK_DIR) { $env:AIXMOS_PACK_DIR } else { Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path) }
$HostDir = Join-Path $env:USERPROFILE '.aixmos'
$ModelsDir = Join-Path $HostDir 'models'
$LogDir = Join-Path $PackDir 'logs'
$Log = Join-Path $LogDir ("install-{0}.log" -f (Get-Date -Format "yyyyMMdd-HHmmss"))

New-Item -ItemType Directory -Force -Path $ModelsDir, $LogDir | Out-Null

function Log($msg) {
  $line = "[{0}] {1}" -f (Get-Date -Format "HH:mm:ss"), $msg
  Write-Host $line
  Add-Content -Path $Log -Value $line
}

Log "=== AIXMOS Starter Pack - install ==="
Log "Pack dir: $PackDir"
Log "Host dir: $HostDir"

# 1. RAM precheck + profile decision
$ramGB = [math]::Round((Get-CimInstance Win32_ComputerSystem).TotalPhysicalMemory / 1GB, 0)
if ($ramGB -lt 8) {
  Log "[X] Detected $ramGB GB RAM. AIXMOS needs 8 GB minimum. Aborting."
  exit 1
}
$cpu = (Get-CimInstance Win32_Processor | Select-Object -First 1).Name
$isAMD = $cpu -match 'AMD|Ryzen'
if ($ramGB -le 9) {
  $profile = 'lite'
  Log "[OK] RAM: $ramGB GB  CPU: $cpu"
  Log "[i]  Profile: LITE (8 GB tier - qwen2.5:1.5b only, terminal chat, no OWUI auto)"
} else {
  $profile = 'full'
  Log "[OK] RAM: $ramGB GB  CPU: $cpu"
  Log "[i]  Profile: FULL (>=10 GB - full model set, OWUI auto-launch)"
}

# 2. Disk precheck
$drive = (Get-Item $env:USERPROFILE).PSDrive
$freeGB = [math]::Round($drive.Free / 1GB, 0)
$needGB = if ($profile -eq 'lite') { 4 } else { 10 }
if ($freeGB -lt $needGB) {
  Log "[X] Only $freeGB GB free on $($drive.Name). Need $needGB GB for $profile profile. Aborting."
  exit 1
}
Log "[OK] Disk free: $freeGB GB (need $needGB for $profile)"

# 3. Ollama
$ollama = Get-Command ollama -ErrorAction SilentlyContinue
if (-not $ollama) {
  Log "Ollama not found. Please install from https://ollama.com/download/windows"
  Log "Then re-run this installer."
  Start-Process "https://ollama.com/download/windows"
  exit 1
}
Log "[OK] Ollama: $(ollama --version 2>&1 | Select-Object -First 1)"

# Start Ollama service if not already
try {
  Invoke-WebRequest -Uri "http://127.0.0.1:11434/api/tags" -TimeoutSec 1 -UseBasicParsing | Out-Null
  Log "[OK] Ollama already running"
} catch {
  Log "Starting Ollama service..."
  Start-Process -FilePath "ollama" -ArgumentList "serve" -WindowStyle Hidden
  Start-Sleep -Seconds 3
}

# 4. Copy any bundled GGUFs from USB (air-gapped path)
$pkgModels = Join-Path $PackDir '_models'
if (Test-Path $pkgModels) {
  $files = Get-ChildItem $pkgModels -File -ErrorAction SilentlyContinue | Where-Object { $_.Name -notin @('MANIFEST.json', 'README.md') }
  if ($files.Count -gt 0) {
    Log "Copying bundled model files from USB to host..."
    foreach ($f in $files) {
      Copy-Item -Path $f.FullName -Destination $ModelsDir -Force
      Log "  copied $($f.Name)"
    }
  }
}

# 5. Pull models per profile
$manifest = Get-Content (Join-Path $pkgModels 'MANIFEST.json') -Raw | ConvertFrom-Json
$wanted = if ($profile -eq 'lite') {
  $manifest.models | Where-Object { $_.id -eq 'qwen2.5:1.5b' }
} else {
  $manifest.models
}
foreach ($m in $wanted) {
  $existing = ollama list 2>$null | Select-String -Pattern "^$($m.ollama_tag)"
  if ($existing) {
    Log "[OK] $($m.ollama_tag) already pulled"
  } else {
    Log "Pulling $($m.ollama_tag) from registry..."
    try { ollama pull $m.ollama_tag 2>&1 | Select-Object -Last 3 | ForEach-Object { Log $_ } }
    catch { Log "[!] Pull failed for $($m.ollama_tag)" }
  }
}

# 6. Build brain (lite or full)
if ($profile -eq 'lite') {
  $modelfile = Join-Path $PackDir '_brain\Modelfile.tmmt-brain-lite'
  $brainName = 'tmmt-brain-lite'
} else {
  $modelfile = Join-Path $PackDir '_brain\Modelfile.tmmt-brain'
  $brainName = 'tmmt-brain'
}
if (Test-Path $modelfile) {
  Log "Building $brainName..."
  try { ollama create $brainName -f $modelfile 2>&1 | Select-Object -Last 5 | ForEach-Object { Log $_ } }
  catch { Log "[!] $brainName build failed" }
}

# 7. State file (profile is persisted - start/chat/doctor read this)
$state = @{
  installed_at    = (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ")
  pack_dir        = $PackDir
  profile         = $profile
  default_model   = $brainName
  fallback_model  = if ($profile -eq 'lite') { 'qwen2.5:1.5b' } else { 'llama3.2:3b' }
  ports           = @{ ollama = 11434; openwebui = 8080; brain_dump = 7780 }
  platform        = "Windows"
  cpu             = $cpu
  cpu_amd         = $isAMD
  ram_gb          = $ramGB
} | ConvertTo-Json -Depth 4
Set-Content -Path (Join-Path $HostDir 'state.json') -Value $state
Log "[OK] State written (profile=$profile)"

Log ""
Log "=========================================="
Log "[OK] AIXMOS Starter Pack installed."
Log "    Profile: $profile  |  Brain: $brainName"
if ($profile -eq 'lite') {
  Log "    Next: option 5 (Chat in terminal) - OWUI skipped on 8 GB"
} else {
  Log "    Next: option 2 (Start AIXMOS) - opens OWUI in browser"
}
Log "=========================================="
