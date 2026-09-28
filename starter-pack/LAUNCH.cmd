@echo off
REM AIXMOS Starter Pack — Windows launcher
REM Double-click this file from Explorer to open the menu.

setlocal EnableDelayedExpansion
cd /d "%~dp0"
set "PACK_DIR=%CD%"
set "AIXMOS_PACK_DIR=%PACK_DIR%"

:MENU
cls
echo ================================================================
echo    AIXMOS  STARTER  PACK  -  v1
echo ================================================================
echo.

REM Detect install state
if exist "%USERPROFILE%\.aixmos\state.json" (
  set "INSTALL_STATE=[OK] installed"
) else (
  set "INSTALL_STATE=[!] not installed (run option 1)"
)

REM Detect profile from state.json (lite / full)
set "PROFILE=unknown"
if exist "%USERPROFILE%\.aixmos\state.json" (
  for /f "tokens=2 delims=:," %%P in ('findstr /C:"\"profile\"" "%USERPROFILE%\.aixmos\state.json"') do (
    set "PROFILE=%%~P"
    set "PROFILE=!PROFILE: =!"
    set "PROFILE=!PROFILE:"=!"
  )
)

REM Detect RAM tier for first-run hint
for /f "tokens=2 delims==" %%R in ('wmic ComputerSystem get TotalPhysicalMemory /value ^| find "="') do set "RAM_BYTES=%%R"
set /a RAM_GB=!RAM_BYTES:~0,-9! / 1 2>nul
if not defined RAM_GB set "RAM_GB=?"

REM Detect running
curl -s --max-time 1 http://127.0.0.1:11434/api/tags >nul 2>&1
if !errorlevel! equ 0 (
  set "RUN_STATE=[OK] Ollama running"
) else (
  set "RUN_STATE=[--] Ollama stopped"
)

echo   Pack:    %PACK_DIR%
echo   RAM:     ~!RAM_GB! GB     Profile: !PROFILE!
echo   Status:  !INSTALL_STATE!   ^|   !RUN_STATE!
echo.
if "!PROFILE!"=="lite" (
  echo   [i] LITE profile - 8 GB tier. Use option 5 for chat ^(no browser^).
  echo.
)
echo   WHAT DO YOU WANT TO DO?
echo   -----------------------------------------------------
echo    1) Install AIXMOS (first time, ~3 min)
echo    2) Start AIXMOS (open chat in browser)
echo    3) Stop AIXMOS
echo    4) Doctor (run health check)
echo    5) Chat in terminal (no browser)
echo    6) Open OPERATIONS_BRAIN docs
echo    7) Copy system prompt to clipboard
echo    8) Download/refresh model weights (~5 GB, internet)
echo    9) Unlock PRO pack (Agents of Chaos)
echo   10) Uninstall (remove %USERPROFILE%\.aixmos models)
echo    q) Quit
echo   -----------------------------------------------------
set /p "choice=  Choice: "

if /i "%choice%"=="1"  powershell -ExecutionPolicy Bypass -File "%PACK_DIR%\_starter\install.ps1"
if /i "%choice%"=="2"  powershell -ExecutionPolicy Bypass -File "%PACK_DIR%\_starter\start.ps1"
if /i "%choice%"=="3"  powershell -ExecutionPolicy Bypass -File "%PACK_DIR%\_starter\stop.ps1"
if /i "%choice%"=="4"  powershell -ExecutionPolicy Bypass -File "%PACK_DIR%\_starter\doctor.ps1"
if /i "%choice%"=="5"  powershell -ExecutionPolicy Bypass -File "%PACK_DIR%\_starter\chat.ps1"
if /i "%choice%"=="6"  start "" "%PACK_DIR%\_brain\docs\OPERATIONS_BRAIN.pdf" 2>nul || start "" "%PACK_DIR%\_brain\docs\OPERATIONS_BRAIN.md"
if /i "%choice%"=="7"  type "%PACK_DIR%\_brain\system-prompts\default.md" | clip && echo   [OK] System prompt copied.
if /i "%choice%"=="8"  powershell -ExecutionPolicy Bypass -File "%PACK_DIR%\_starter\download-models.ps1"
if /i "%choice%"=="9"  powershell -ExecutionPolicy Bypass -File "%PACK_DIR%\_pro\unlock.ps1" 2>nul || echo   PRO pack not present on this drive.
if /i "%choice%"=="10" powershell -ExecutionPolicy Bypass -File "%PACK_DIR%\_starter\uninstall.ps1"
if /i "%choice%"=="q"  goto :END

echo.
pause
goto MENU

:END
endlocal
exit /b 0
