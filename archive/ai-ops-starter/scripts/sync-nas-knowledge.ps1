#Requires -Version 5.1
param(
    [string]$NasKnowledge = "Z:\knowledge",
    [string]$NasSops = "Z:\sops",
    [string]$LocalIngest = "C:\AI-OPS-STARTER\data\ingest"
)

New-Item -ItemType Directory -Force -Path $LocalIngest | Out-Null
robocopy $NasKnowledge (Join-Path $LocalIngest "knowledge") /MIR
robocopy $NasSops (Join-Path $LocalIngest "sops") /MIR
Write-Host "Synced NAS knowledge to $LocalIngest — ingest via Open WebUI Documents"
