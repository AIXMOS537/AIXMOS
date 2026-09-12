@echo off
REM Serve-AIXMOS.cmd -- headless launcher used by the logon task (no browser window).
REM Starts the server on 8770 only if nothing already answers there; never double-binds.
cd /d "%~dp0"
powershell -NoProfile -ExecutionPolicy Bypass -Command "$c=New-Object Net.Sockets.TcpClient; try{$c.Connect('127.0.0.1',8770);$c.Close()}catch{ Start-Process -WindowStyle Hidden 'C:\Program Files\Python314\pythonw.exe' -ArgumentList (Join-Path (Get-Location) 'project_aixmos_server.py'),'8770' }"
