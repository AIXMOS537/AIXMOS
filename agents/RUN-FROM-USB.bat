@echo off
setlocal
title AIXMOS Agents - PORTABLE (running from USB)
cls
echo.
echo   ============================================================
echo    AIXMOS AGENTS - PORTABLE MODE
echo    Running directly from this USB. Nothing is installed to C:.
echo   ============================================================
echo.

set "USB_DIR=%~dp0"
if "%USB_DIR:~-1%"=="\" set "USB_DIR=%USB_DIR:~0,-1%"

where node >nul 2>nul
if errorlevel 1 (
    echo   Node.js is not installed on this PC.
    if exist "%USB_DIR%\_installers\node-v24.15.0-x64.msi" (
        echo   Opening the included Node.js installer.
        echo   After installing, run this file again.
        start "" "%USB_DIR%\_installers\node-v24.15.0-x64.msi"
    ) else (
        echo   Install Node.js LTS from https://nodejs.org
    )
    pause
    exit /b 1
)

if not exist "%USB_DIR%\node_modules\@anthropic-ai\sdk" (
    echo   node_modules missing on USB. Installing once (will be saved to USB)...
    cd /d "%USB_DIR%"
    call npm.cmd install --silent
)

echo   ANTHROPIC_API_KEY scope checks:
if not "%ANTHROPIC_API_KEY%"=="" (
    echo     session: set
) else (
    echo     session: NOT SET - either set it or use offline mode (AIXMOS_LLM_BACKEND=ollama)
)
echo.

echo   What do you want to launch?
echo.
echo     1. Master orchestrator menu (all 10 agents)
echo     2. CHUMMO     - customer comms
echo     3. MOOSE      - ops execution
echo     4. CAPTAIN    - command brief
echo     5. WONDERWOMAN- trust defender
echo     6. VISION     - go/no-go
echo     7. JARVIS     - speaks for the owner
echo     8. TANK       - infra heavy lifting
echo     9. FLY GUY    - customer comms support
echo    10. BOB        - audit + docs
echo    11. STICKS     - SLA monitor
echo    12. MORNING BRIEF
echo    13. AGENT SMOKE TESTS (--live)
echo.
set /p CHOICE="  Pick 1-13: "

cd /d "%USB_DIR%"
if "%CHOICE%"=="1"  ( node orchestrator.js & goto :END )
if "%CHOICE%"=="2"  ( node orchestrator.js chummo & goto :END )
if "%CHOICE%"=="3"  ( node moose.js        & goto :END )
if "%CHOICE%"=="4"  ( node captain.js      & goto :END )
if "%CHOICE%"=="5"  ( node wonderwoman.js  & goto :END )
if "%CHOICE%"=="6"  ( node vision.js       & goto :END )
if "%CHOICE%"=="7"  ( node jarvis.js       & goto :END )
if "%CHOICE%"=="8"  ( node tank.js         & goto :END )
if "%CHOICE%"=="9"  ( node flyguy.js       & goto :END )
if "%CHOICE%"=="10" ( node bob.js          & goto :END )
if "%CHOICE%"=="11" ( node sticks.js       & goto :END )
if "%CHOICE%"=="12" ( node briefing.js     & goto :END )
if "%CHOICE%"=="13" ( node test-all-agents.js --live & goto :END )

echo   Invalid choice.

:END
echo.
pause
