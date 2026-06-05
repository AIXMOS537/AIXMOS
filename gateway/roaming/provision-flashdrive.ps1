<#  provision-flashdrive.ps1 — make a USB drive a PLUG-AND-PLAY AIXMOS kit (Windows).
    Run this on the PC where your drives are plugged in.
    Lays down AIXMOS-KIT/ (never-dark clients, device bootstraps, road runbook, your SOPs).
    SAFE: only ADDS/UPDATES AIXMOS-KIT (never deletes your files). NO raw secrets
    (optional -WithEncKeys writes an AES-256 encrypted bundle). GitHub = source of truth.

    Usage:
      powershell -ExecutionPolicy Bypass -File .\provision-flashdrive.ps1
      powershell -ExecutionPolicy Bypass -File .\provision-flashdrive.ps1 -Drive E: -KnowledgeBase C:\path\to\TMMT_Knowledge_Base
#>
param([string]$Drive, [string]$KnowledgeBase, [switch]$WithEncKeys)
$ErrorActionPreference = "Stop"

# 0) get the kit from GitHub (truth). Clone to a temp work dir, or pull if present.
$work = Join-Path $env:USERPROFILE "aixmos-gateway"
if (Test-Path (Join-Path $work ".git")) { git -C $work pull --ff-only 2>$null }
elseif (Get-Command git -ErrorAction SilentlyContinue) {
  Write-Host "Cloning kit from GitHub..."; git clone https://github.com/AIXMOS537/aixmos-gateway.git $work 2>$null
} else { Write-Warning "git not found — using local .\roaming if present"; $work = (Resolve-Path "$PSScriptRoot\..").Path }
$kitSrc = Join-Path $work "roaming"
if (-not (Test-Path $kitSrc)) { throw "Kit source not found at $kitSrc" }

# 1) pick the removable drive
if (-not $Drive) {
  $rem = Get-CimInstance Win32_LogicalDisk -Filter "DriveType=2"   # 2 = removable
  if (-not $rem) { throw "No removable USB drive detected. Plug one in and re-run, or pass -Drive E:" }
  Write-Host "Removable drives:"; $i=0; $map=@{}
  foreach ($d in $rem) { $i++; $map[$i]=$d.DeviceID; "  [$i] $($d.DeviceID)  $([math]::Round($d.Size/1GB,1))GB free $([math]::Round($d.FreeSpace/1GB,1))GB" }
  $n = Read-Host "Pick a drive number"; $Drive = $map[[int]$n]
}
if (-not (Test-Path "$Drive\")) { throw "Drive $Drive not available" }
$dest = Join-Path "$Drive\" "AIXMOS-KIT"
Write-Host "Target: $dest" -ForegroundColor Cyan
New-Item -ItemType Directory -Force -Path "$dest\kit" | Out-Null

# 2) copy kit (add/update only — robocopy without /MIR so nothing is deleted)
Write-Host "Copying never-dark clients + bootstraps + runbook..."
robocopy $kitSrc "$dest\kit" /E /XF "*.DS_Store" /NJH /NJS /NDL /NP | Out-Null
if ($KnowledgeBase -and (Test-Path $KnowledgeBase)) {
  Write-Host "Copying Knowledge Base (offline SOPs)..."
  robocopy $KnowledgeBase "$dest\KnowledgeBase" /E /NJH /NJS /NDL /NP | Out-Null
} else { New-Item -ItemType Directory -Force -Path "$dest\KnowledgeBase" | Out-Null; Write-Host "(no -KnowledgeBase given — created empty folder; drop your SOPs there)" }

# 3) optional encrypted keys bundle (off by default)
if ($WithEncKeys) {
  $vault = Join-Path $env:USERPROFILE "aixmos-KEYS-canonical\gateway-secrets.env"
  if (Test-Path $vault) {
    $pw = Read-Host "Passphrase to encrypt keys bundle" -AsSecureString
    $bytes = [System.Text.Encoding]::UTF8.GetBytes((Get-Content $vault -Raw))
    # simple AES via openssl if available; else skip with a clear note
    if (Get-Command openssl -ErrorAction SilentlyContinue) {
      $plain = [Runtime.InteropServices.Marshal]::PtrToStringAuto([Runtime.InteropServices.Marshal]::SecureStringToBSTR($pw))
      $env:AIX_PW=$plain; cmd /c "openssl enc -aes-256-cbc -pbkdf2 -salt -pass env:AIX_PW -in `"$vault`" -out `"$dest\keys.enc`""; Remove-Item Env:AIX_PW
      Write-Host "Wrote encrypted $dest\keys.enc"
    } else { Write-Warning "openssl not found — skipped encrypted keys. Install openssl or use 1Password instead." }
  }
}

# 4) START-HERE + launcher
@'
AIXMOS PLUG-AND-PLAY KIT
========================
WINDOWS:  powershell -ExecutionPolicy Bypass -File .\kit\bootstrap-windows.ps1
          (paste your CARRY secret when asked, then: tailscale up)
          use:  .\kit\aixmos.ps1 "test"     (works online OR fully offline)
MAC:      bash kit/aixmos-anywhere.sh "test"
OFFLINE:  local model + KnowledgeBase (SOPs) work with NO internet.
SECURITY: turn on BitLocker/FileVault. No raw secrets on this drive (use 1Password / keys.enc).
'@ | Set-Content "$dest\START-HERE.txt"

@'
@echo off
cd /d "%~dp0kit"
set /p q="Ask AIXMOS: "
powershell -ExecutionPolicy Bypass -File .\aixmos.ps1 "%q%"
pause
'@ | Set-Content "$dest\AIXMOS (Windows).bat"

# 5) verify
$N = (Get-ChildItem -Recurse -File $dest | Measure-Object).Count
Write-Host ""; Write-Host "DONE. Provisioned $dest ($N files)." -ForegroundColor Green
Write-Host "Eject safely from the taskbar before unplugging (these drives drop writes if yanked)." -ForegroundColor Yellow
