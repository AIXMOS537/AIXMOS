# Sync TMMT + AIXMODE from a Windows source folder to the Lexar drive
param(
    [string]$LexarRoot = "E:\",
    [string]$SourceTmmt = "$env:USERPROFILE\Desktop\TMMT MANAGEMENT",
    [string]$SourceAix = "$env:USERPROFILE\Desktop\AIXMODE"
)

$ErrorActionPreference = "Stop"
if (-not (Test-Path $LexarRoot)) { throw "Lexar not found at $LexarRoot" }

$exclude = @("node_modules", ".git", "__pycache__", ".env", ".env.local")
$destTmmt = Join-Path $LexarRoot "TMMT MANAGEMENT"
Write-Host "Robocopy TMMT -> $destTmmt"
robocopy $SourceTmmt $destTmmt /E /XD node_modules .git __pycache__ /XF .env .env.local .DS_Store /NFL /NDL /NJH /NJS

if (Test-Path $SourceAix) {
    $destAix = Join-Path $LexarRoot "AIXMODE"
    Write-Host "Robocopy AIXMODE -> $destAix"
    robocopy $SourceAix $destAix /E /XD node_modules .git /XF .env .DS_Store /NFL /NDL /NJH /NJS
}

Write-Host "Done."
