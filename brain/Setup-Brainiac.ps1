# ============================================================
#  Setup-Brainiac.ps1  —  RUN THIS ON BRAINIAC (one time)
#  Connects to the NAS, clones the shared AIXMOS brain locally,
#  and wires it for two-way git sync + Obsidian.
#  Run in PowerShell:  powershell -ExecutionPolicy Bypass -File Setup-Brainiac.ps1
# ============================================================
$ErrorActionPreference = 'Stop'

$nasIp     = '192.168.1.236'                                   # NAS on the Verizon LAN
$nasUser   = 'MUHAMMAD TAHA'                                   # NAS SMB username (with the space)
$share     = "\\$nasIp\personal_folder"
$vaultUnc  = "\\$nasIp\personal_folder\AIXMOS\AIXMOS-Brain"    # the brain repo on the NAS
$dest      = "$env:USERPROFILE\AIXMOS-Brain"                   # local copy on Brainiac

Write-Host "== AIXMOS Brain setup for Brainiac ==" -ForegroundColor Cyan

# 1) Can Brainiac reach the NAS?
if (-not (Test-Connection -ComputerName $nasIp -Count 2 -Quiet)) {
  Write-Host "NAS $nasIp is not reachable from here." -ForegroundColor Yellow
  Write-Host "Either join the same WiFi as the NAS (Verizon), OR enable the Tailscale app in UGOS" -ForegroundColor Yellow
  Write-Host "and re-run this using the NAS's Tailscale name instead of $nasIp." -ForegroundColor Yellow
  exit 1
}

# 2) Connect to the NAS share (will prompt for the NAS password)
Write-Host "Connecting to $share  (enter the NAS password for '$nasUser' when asked)..." -ForegroundColor Cyan
net use $share /user:"$nasUser" *

# 3) Make git trust the UNC path, then clone or update
git config --global --add safe.directory "$vaultUnc" 2>$null
if (Test-Path "$dest\.git") {
  Write-Host "Brain already here — pulling latest..." -ForegroundColor Green
  git -C $dest pull nas main
} else {
  Write-Host "Cloning the brain to $dest ..." -ForegroundColor Green
  git clone "$vaultUnc" "$dest"
  git -C $dest remote rename origin nas 2>$null
}

# 4) Done
Write-Host ""
Write-Host "DONE. Your brain is at: $dest" -ForegroundColor Green
Write-Host "Open that folder as a Vault in Obsidian (Open folder as vault)." -ForegroundColor Green
Write-Host "To sync later:  git -C `"$dest`" pull nas main   (get updates)" -ForegroundColor Gray
Write-Host "                git -C `"$dest`" push nas main   (send your edits)" -ForegroundColor Gray
Start-Process $dest
