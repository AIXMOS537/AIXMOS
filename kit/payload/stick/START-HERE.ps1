<#
  START-HERE - TMMT + JARVIS straight off this stick, on any Windows PC.

  Python, Node, Git, Ollama and ffmpeg all run from _RUNTIME\win. They go on
  PATH for this window only. Nothing is installed; pull the stick and the PC is
  exactly as it was.
#>
param([string]$Go = '')
$ErrorActionPreference = 'Continue'

$Root = $PSScriptRoot
$K    = Get-Content (Join-Path $Root 'AIXMOS-KIT\kit.json') -Raw | ConvertFrom-Json
function Lane($n) { Join-Path $Root ($K.lanes.$n.drive -replace '/', '\') }
$RT = @{}
foreach ($p in $K.bootstick.runtimes.PSObject.Properties) { $RT[$p.Name] = Join-Path $Root ($p.Value.drive -replace '/', '\') }

$Canon    = Lane 'canon'
$Jarvis   = Join-Path (Lane 'automation') 'project-aixmos'
$KitCmd   = Join-Path (Lane 'kit') 'bin\aixmos.ps1'
$PortFile = Join-Path $env:TEMP 'aixmos-stick-port.txt'

$env:PATH = (@($RT.python, (Join-Path $RT.python 'Scripts'), $RT.node, (Join-Path $RT.git 'cmd'), $RT.ffmpeg, $RT.ollama) -join ';') + ';' + $env:PATH
$env:OLLAMA_MODELS = Join-Path $Root ($K.bootstick.models -replace '/', '\')

function Ok($t)  { Write-Host '  [ OK ] ' -ForegroundColor Green -NoNewline; Write-Host $t }
function Bad($t) { Write-Host '  [FAIL] ' -ForegroundColor Red   -NoNewline; Write-Host $t }
function Up([int]$port) {
    $c = New-Object Net.Sockets.TcpClient
    try { $c.Connect('127.0.0.1', $port); $true } catch { $false } finally { $c.Close() }
}
function Wait-Up([int]$port, [int]$secs) {
    for ($i = 0; $i -lt $secs; $i++) { if (Up $port) { return $true }; Start-Sleep 1 }
    $false
}

function Start-Brain {
    if (Up 11434) { Ok 'offline brain: using the Ollama already running on this PC'; return }
    $exe = Join-Path $RT.ollama 'ollama.exe'
    if (-not (Test-Path $exe)) { Bad "ollama missing at $exe"; return }
    Start-Process $exe -ArgumentList 'serve' -WindowStyle Hidden
    if (Wait-Up 11434 40) { Ok 'offline brain up - models read straight off the stick' }
    else { Bad 'Ollama did not start' }
}

function Start-Jarvis {
    Start-Brain
    if (Test-Path $PortFile) {
        $p = [int](Get-Content $PortFile -Raw)
        if (Up $p) { Ok "JARVIS already running -> http://localhost:$p"; Start-Process "http://localhost:$p"; return }
    }
    # 8770 is JARVIS's home port. If this PC already runs its own JARVIS there,
    # the stick's copy (with the stick's memory) takes 8777 instead.
    $port = if (Up 8770) { 8777 } else { 8770 }
    $py   = Join-Path $RT.python 'pythonw.exe'
    Start-Process $py -ArgumentList "`"$(Join-Path $Jarvis 'project_aixmos_server.py')`"", $port -WorkingDirectory $Jarvis -WindowStyle Hidden
    if (Wait-Up $port 60) {
        Set-Content $PortFile $port
        Ok "JARVIS online -> http://localhost:$port"
        Start-Process "http://localhost:$port"
    } else {
        Bad 'JARVIS did not answer. To see why, run:'
        Write-Host "    `"$(Join-Path $RT.python 'python.exe')`" `"$(Join-Path $Jarvis 'project_aixmos_server.py')`" $port" -ForegroundColor DarkGray
    }
}

function Open-TmmtShell {
    $cmd = "Set-Location '$Canon'; function aixmos { & '$KitCmd' @args }; " +
           "Write-Host 'TMMT shell - node, npm, git, python, ollama from the stick are on PATH.' -ForegroundColor Cyan; " +
           "Write-Host 'node_modules is not carried: run  npm ci  (needs internet) before  npm run dev.' -ForegroundColor DarkGray"
    Start-Process powershell -ArgumentList '-NoExit', '-ExecutionPolicy', 'Bypass', '-Command', $cmd -WorkingDirectory $Canon
    Ok 'TMMT shell opened'
}

function Stop-Stick {
    $r = $Root.TrimEnd('\')
    $n = 0
    Get-CimInstance Win32_Process | Where-Object { $_.ExecutablePath -and $_.ExecutablePath.StartsWith($r, [StringComparison]::OrdinalIgnoreCase) } |
        ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue; $n++ }
    Remove-Item $PortFile -ErrorAction SilentlyContinue
    Ok "stopped $n process(es) running from the stick - safe to unplug"
}

function Install-Jarvis {
    # The 4THEPEOPLE bundle: role picker (TMMT Operator / AIXMOS Movement / Both), Genesis first boot.
    $exe    = Join-Path $Root ($K.bootstick.installer.windows -replace '/', '\')
    $readme = Join-Path $Root ($K.bootstick.installer.readme -replace '/', '\')
    if (Test-Path $readme) { Get-Content $readme | ForEach-Object { Write-Host "   $_" -ForegroundColor DarkGray }; Write-Host '' }
    if (Test-Path $exe) { Start-Process $exe; Ok "started $(Split-Path $exe -Leaf) - it installs JARVIS on this PC for good" }
    else { Bad "installer missing: $exe" }
}

function Ask-Brain {
    Start-Brain
    $q = Read-Host '  Ask'
    if ($q) { & $KitCmd ai $q }
}

switch -Regex ($Go.ToLower()) {
    '^jarvis$' { Start-Jarvis; return }
    '^stop$'   { Stop-Stick;   return }
    '^shell$'  { Open-TmmtShell; return }
}

while ($true) {
    Clear-Host
    Write-Host ''
    Write-Host '   AIXMOS  //  TMMT + JARVIS  //  running from the stick' -ForegroundColor Cyan
    Write-Host "   $Root" -ForegroundColor DarkGray
    Write-Host ''
    Write-Host '   [1] JARVIS          start the offline brain + JARVIS, open it  (Enter)'
    Write-Host '   [2] TMMT shell      PowerShell in TMMT-canon with node/git/python from the stick'
    Write-Host '   [3] Kit status      lanes, brain, live side, owner gates'
    Write-Host '   [4] Ask the brain   one question to the offline model, no internet'
    Write-Host '   [5] Install JARVIS  install it on this PC for good (4THEPEOPLE installer - see its START-HERE.txt)'
    Write-Host '   [S] Stop            stop everything the stick started (before unplugging)'
    Write-Host '   [Q] Quit'
    Write-Host ''
    $c = (Read-Host '   choose').Trim().ToUpper()
    switch ($c) {
        ''  { Start-Jarvis }
        '1' { Start-Jarvis }
        '2' { Open-TmmtShell }
        '3' { & $KitCmd status }
        '4' { Ask-Brain }
        '5' { Install-Jarvis }
        'S' { Stop-Stick }
        'Q' { return }
    }
    Write-Host ''
    Read-Host '   Enter for the menu' | Out-Null
}
