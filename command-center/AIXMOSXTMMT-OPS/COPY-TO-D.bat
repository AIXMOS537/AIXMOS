@echo off
set SRC=%~dp0
set DEST=D:\AIXMOSXTMMT-OPS

echo Copying to %DEST% ...
if not exist D:\ (
  echo ERROR: Drive D: not found. Plug in USB AIXMOS02.
  pause
  exit /b 1
)

mkdir "%DEST%" 2>nul
robocopy "%SRC%" "%DEST%" /E /XD node_modules dist /XF .env /R:2 /W:2
if %ERRORLEVEL% GEQ 8 (
  echo robocopy failed.
  pause
  exit /b %ERRORLEVEL%
)

echo.
echo Done: %DEST%
echo Next:
echo   cd /d %DEST%
echo   scripts\setup-windows.ps1
pause
