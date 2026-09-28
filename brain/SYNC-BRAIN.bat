@echo off
REM Double-click to fully sync your brain with the NAS (pull latest, then push).
REM Use this when you switch between devices.
echo Syncing AIXMOS brain with the NAS...
cd /d "C:\Users\AIXMOS\AIXMOS-Brain"
git pull nas main
git add -A
git commit -m "manual sync" 1>nul 2>nul
git push nas main
echo.
echo Done. Press any key to close.
pause 1>nul
