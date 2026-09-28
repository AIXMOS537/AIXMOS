param(
    [string]$SourceDrive = "D:\",
    [string]$BundlePath = "",
    [switch]$SkipCopy,
    [switch]$IncludeCursorZip,
    [switch]$IncludeSensitive,
    [switch]$InitGit
)
$ErrorActionPreference = "Stop"
if (-not $BundlePath) { $BundlePath = Join-Path $SourceDrive.TrimEnd('\') "MacMigrationBundle" }
$SourceDrive = $SourceDrive.TrimEnd('\') + '\'
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path

function Write-Step($msg) { Write-Host "`n==> $msg" -ForegroundColor Cyan }

if (-not $SkipCopy) {
    if (-not (Test-Path $SourceDrive)) { throw "Source not found: $SourceDrive" }
    Write-Step "Building bundle at $BundlePath"
    New-Item -ItemType Directory -Force -Path $BundlePath | Out-Null
    $folders = @("AIXMOS","credit_business_corporate_system","all_in_one_platform","Business","Media","Archive","_CyborgReports")
    foreach ($f in $folders) {
        $src = Join-Path $SourceDrive $f
        if (-not (Test-Path $src)) { Write-Host "  SKIP $f"; continue }
        $dest = Join-Path $BundlePath $f
        if (Test-Path $dest) { Remove-Item $dest -Recurse -Force }
        Write-Host "  Copy $f..."
        Copy-Item $src $dest -Recurse -Force
    }
    if ($IncludeSensitive -and (Test-Path (Join-Path $SourceDrive "Personal"))) {
        Copy-Item (Join-Path $SourceDrive "Personal") (Join-Path $BundlePath "Personal") -Recurse -Force
    }
} else {
    Write-Step "SkipCopy: refreshing agents, scripts, manifest only"
    if (-not (Test-Path $BundlePath)) { throw "Bundle not found: $BundlePath" }
}

$agentsDest = Join-Path $BundlePath ".cursor\agents"
New-Item -ItemType Directory -Force -Path $agentsDest | Out-Null
Get-ChildItem $SourceDrive -Filter "*.agent.md" -File -EA SilentlyContinue | ForEach-Object {
    Copy-Item $_.FullName (Join-Path $agentsDest $_.Name) -Force
}
$cyborgInReports = Join-Path $BundlePath "_CyborgReports\cyborg.agent.md"
if (Test-Path $cyborgInReports) { Copy-Item $cyborgInReports (Join-Path $agentsDest "cyborg.agent.md") -Force }

$macSh = Join-Path $ScriptDir "mac-setup.sh"
if (Test-Path $macSh) { Copy-Item $macSh (Join-Path $BundlePath "mac-setup.sh") -Force }

$runTxt = Join-Path $ScriptDir "RUN-IN-VSCODE.txt"
if (Test-Path $runTxt) { Copy-Item $runTxt (Join-Path $BundlePath "RUN-IN-VSCODE.txt") -Force }

@(
"Mac Migration Bundle",
"",
"1. Copy this folder to your Mac (USB exFAT, AirDrop, or Git).",
"2. chmod +x mac-setup.sh && ./mac-setup.sh ~/Projects",
"3. Open ~/Projects/all_in_one_platform in Cursor",
"4. cp .cursor/agents/* to ~/.cursor/agents/",
"",
"See RUN-IN-VSCODE.txt in credit_business_corporate_system/scripts/"
) | Set-Content (Join-Path $BundlePath "START_ON_MAC.txt") -Encoding UTF8

$log = @()
Get-ChildItem $BundlePath -Directory | ForEach-Object { $log += "$($_.Name),folder,present" }

if ($IncludeCursorZip) {
    $ch = Join-Path $env:USERPROFILE ".cursor"
    if (Test-Path $ch) {
        $zip = Join-Path $BundlePath "cursor-settings-windows.zip"
        $tmp = Join-Path $env:TEMP "cursor-export"
        if (Test-Path $tmp) { Remove-Item $tmp -Recurse -Force }
        New-Item -ItemType Directory -Path $tmp | Out-Null
        Get-ChildItem $ch -Force | Where-Object { $_.Name -notin @("extensions","CachedData","Cache","logs") } | ForEach-Object {
            Copy-Item $_.FullName (Join-Path $tmp $_.Name) -Recurse -Force -EA SilentlyContinue
        }
        if (Test-Path $zip) { Remove-Item $zip -Force }
        Compress-Archive -Path "$tmp\*" -DestinationPath $zip -Force
        Remove-Item $tmp -Recurse -Force -EA SilentlyContinue
        $log += "cursor-settings-windows.zip,zip,created"
    }
}

if ($InitGit) {
    $pp = Join-Path $BundlePath "all_in_one_platform"
    if (Test-Path $pp) {
        Push-Location $pp
        $repo = (Resolve-Path .).Path
        git config --global --add safe.directory $repo 2>$null
        git config --global --add safe.directory "D:/MacMigrationBundle/all_in_one_platform" 2>$null
        if (-not (Test-Path ".git")) { git init 2>$null | Out-Null }
        git add . 2>$null
        $commit = git commit --trailer "Co-authored-by: Cursor <cursoragent@cursor.com>" -m "Migration scaffold" 2>&1
        if ($LASTEXITCODE -ne 0) {
            Write-Host "  Git commit note: $commit" -ForegroundColor Yellow
        } else {
            Write-Host "  Git commit OK" -ForegroundColor Green
        }
        Pop-Location
        $log += "git,init,attempted"
    }
}

$log | Out-File (Join-Path $BundlePath "MIGRATION_MANIFEST.csv") -Encoding UTF8
$mb = [math]::Round(((Get-ChildItem $BundlePath -Recurse -File -EA SilentlyContinue | Measure-Object Length -Sum).Sum / 1MB), 1)
Write-Step "DONE ~${mb} MB"
Write-Host "Bundle: $BundlePath"
exit 0