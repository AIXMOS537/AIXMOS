#Requires -Version 5.1
param(
    [string]$ProjectRoot = "C:\AI-OPS-STARTER",
    [string]$BackupRoot = "Z:\backups\ai-ops"
)

$ErrorActionPreference = "Stop"
$stamp = Get-Date -Format "yyyy-MM-dd"
$dest = Join-Path $BackupRoot $stamp
New-Item -ItemType Directory -Force -Path $dest | Out-Null

Set-Location $ProjectRoot

Write-Host "Backing up to $dest"

# Kit files (no .env)
robocopy $ProjectRoot (Join-Path $dest "kit") /MIR /XD .git data /XF .env | Out-Null

# Docker volumes
$volumes = @("ai-ops-starter_open-webui-data", "ai-ops-starter_n8n-data", "ai-ops-starter_postgres-data", "ai-ops-starter_qdrant-data")
foreach ($v in $volumes) {
    $vPath = Join-Path $dest "volumes\$v"
    New-Item -ItemType Directory -Force -Path $vPath | Out-Null
    docker run --rm -v "${v}:/data" -v "${vPath}:/backup" alpine tar czf /backup/archive.tar.gz -C /data . 2>$null
    if ($LASTEXITCODE -eq 0) { Write-Host "[OK] $v" } else { Write-Host "[SKIP] $v" }
}

# n8n workflow exports
Copy-Item -Recurse -Force "$ProjectRoot\n8n" (Join-Path $dest "n8n-export")

Write-Host "Backup complete: $dest"
