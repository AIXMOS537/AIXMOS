@echo off
title Project Crimson Shadow
cd /d "%~dp0"
REM Just open the chat. The server normally already runs (CrimsonShadow-AtBoot task),
REM so we only start one if port 8770 isn't answering -- never a double-bind.
powershell -NoProfile -ExecutionPolicy Bypass -Command "$c=New-Object Net.Sockets.TcpClient; try{$c.Connect('127.0.0.1',8770);$c.Close()}catch{ Start-Process -WindowStyle Hidden 'C:\Program Files\Python314\pythonw.exe' -ArgumentList (Join-Path (Get-Location) 'crimson_shadow_server.py'),'8770'; Start-Sleep -Seconds 2 }"
start "" http://localhost:8770
