# Auto-sync the AIXMOS brain to the UGREEN NAS. Best-effort: never throws, never blocks a session.
# Commits local changes always; pushes to the NAS only when it is reachable (fast check, no hang on other networks).
# Pure ASCII on purpose (non-ASCII in a no-BOM PS file breaks the parser).

$ErrorActionPreference = 'SilentlyContinue'
$brain  = 'C:\Users\AIXMOS\AIXMOS-Brain'
$nasIp  = '192.168.1.236'
$remote = 'nas'

if (-not (Test-Path "$brain\.git")) { exit 0 }

# 1) commit any local changes
$changes = git -C $brain status --porcelain
if ($changes) {
    git -C $brain add -A | Out-Null
    $stamp = Get-Date -Format 'yyyy-MM-dd HH:mm'
    git -C $brain commit -m "auto-sync $stamp" | Out-Null
}

# 2) is the NAS actually answering? (a subnet match is NOT enough: being on
#    192.168.1.x while the NAS is off/moved made git push hang forever on the
#    SMB path and pile up zombie git.exe processes. Probe SMB port 445 with a
#    1.5s cap instead - fast on every network, honest about reachability.)
$nasUp = $false
try {
    $tcp = New-Object Net.Sockets.TcpClient
    $async = $tcp.BeginConnect($nasIp, 445, $null, $null)
    $nasUp = $async.AsyncWaitHandle.WaitOne(1500) -and $tcp.Connected
    $tcp.Close()
} catch { $nasUp = $false }

# 3) push only if the NAS answered - and even then, never let git hang:
#    run the push as a job and kill it if it exceeds 60s.
if ($nasUp) {
    $job = Start-Job -ScriptBlock {
        param($b, $r) git -C $b push $r main 2>&1 | Out-Null
    } -ArgumentList $brain, $remote
    if (-not (Wait-Job $job -Timeout 60)) {
        Stop-Job $job -ErrorAction SilentlyContinue
        Get-Process git -ErrorAction SilentlyContinue |
            Where-Object { (Get-CimInstance Win32_Process -Filter "ProcessId=$($_.Id)" -ErrorAction SilentlyContinue).CommandLine -match 'AIXMOS-Brain.*push' } |
            Stop-Process -Force -ErrorAction SilentlyContinue
    }
    Remove-Job $job -Force -ErrorAction SilentlyContinue
}

exit 0
