@echo off
REM ═══════════════════════════════════════════════════════
REM AIXMOS MOOSE — WINDOWS LAUNCHER
REM Double-click this file to start MOOSE
REM ═══════════════════════════════════════════════════════

cls
echo.
echo   ==========================================
echo    AIXMOS - MOOSE AGENT
echo    Relentless. Proactive. Executing.
echo   ==========================================
echo.

REM ── Check Node.js ──────────────────────────────────────
where node >nul 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo   Node.js not found.
    echo.
    echo   Install it from: https://nodejs.org
    echo   Download the LTS version and run the installer.
    echo   Then double-click this file again.
    echo.
    pause
    exit /b 1
)

for /f "tokens=*" %%v in ('node --version') do set NODE_VER=%%v
echo   Node.js found: %NODE_VER%

REM ── Check node_modules ─────────────────────────────────
if not exist "%~dp0node_modules" (
    echo.
    echo   Installing dependencies...
    cd /d "%~dp0"
    call npm install --silent
    echo   Dependencies installed.
)

REM ── Check API Key ───────────────────────────────────────
if "%ANTHROPIC_API_KEY%"=="" (
    echo.
    echo   No API key found.
    echo   Get your key at: https://console.anthropic.com
    echo.
    set /p API_KEY="  Paste your Anthropic API key: "
    if "%API_KEY%"=="" (
        echo   No key entered. Exiting.
        pause
        exit /b 1
    )
    set ANTHROPIC_API_KEY=%API_KEY%
    echo.
    echo   To save permanently, add this to your system environment variables:
    echo   Variable: ANTHROPIC_API_KEY
    echo   Value: %API_KEY%
)

echo   API key ready.
echo.
echo   Launching MOOSE...
echo.

cd /d "%~dp0"
node moose.js

pause
