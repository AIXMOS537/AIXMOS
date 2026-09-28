# keep-alive.ps1 -- run by the AIXMOS-Watchdog task every 5 min.
# Starts Ollama (:11434) and JARVIS (:8770) only if nothing answers; never double-binds.
function Port($p) {
    $c = New-Object Net.Sockets.TcpClient
    try { $c.Connect('127.0.0.1', $p); $c.Close(); $true } catch { $false }
}
$log = Join-Path $env:LOCALAPPDATA 'AIXMOS-watchdog.log'

if (-not (Port 11434)) {
    $app = Join-Path $env:LOCALAPPDATA 'Programs\Ollama\ollama app.exe'
    $cli = Join-Path $env:LOCALAPPDATA 'Programs\Ollama\ollama.exe'
    if (Test-Path $app) { Start-Process $app } else { Start-Process $cli -ArgumentList 'serve' -WindowStyle Hidden }
    Add-Content $log "$(Get-Date -Format s) restarted Ollama"
}
if (-not (Port 8770)) {
    Start-Process cmd.exe -ArgumentList '/c', '"C:\Users\AIXMOS\Automation\project-aixmos\Serve-AIXMOS.cmd"' -WindowStyle Hidden
    Add-Content $log "$(Get-Date -Format s) restarted JARVIS"
}
