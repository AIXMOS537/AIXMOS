@echo off
REM RESEAL-AIXMOS.bat <folder to seal>  -  owner only, on the master stick.
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0RESEAL-AIXMOS.ps1" -From "%~1"
pause
