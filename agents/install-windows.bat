@echo off
setlocal EnableDelayedExpansion

REM ═══════════════════════════════════════════════════════
REM AIXMOS AGENT NETWORK - WINDOWS INSTALLER (v3, 10 agents + offline-ready)
REM Copies the FULL agent tree to %USERPROFILE%\AIXMOS, creates Desktop
REM launchers for all 10 agents, configures the API key, optionally schedules
REM the morning brief, and tells you how to enable offline (Ollama) mode.
REM ═══════════════════════════════════════════════════════

cls
echo.
echo   ============================================================
echo    AIXMOS AGENT NETWORK - WINDOWS INSTALLER
echo    CHUMMO * MOOSE * CAPTAIN * WONDER WOMAN * VISION
echo    JARVIS * TANK * FLY GUY * BOB * STICKS
echo    For the people. By the people.
echo   ============================================================
echo.

set "SCRIPT_DIR=%~dp0"
if "%SCRIPT_DIR:~-1%"=="\" set "SCRIPT_DIR=%SCRIPT_DIR:~0,-1%"
set "INSTALL_DIR=%USERPROFILE%\AIXMOS"
echo   Source:        %SCRIPT_DIR%
echo   Install path:  %INSTALL_DIR%
echo.

REM ── STEP 1: NODE.JS ───────────────────────────────────
echo   [1/6] Checking Node.js...
where node >nul 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo   Node.js not found.
    if exist "%SCRIPT_DIR%\_installers\node-v24.15.0-x64.msi" (
        echo   Opening included Node.js installer.
        start "" "%SCRIPT_DIR%\_installers\node-v24.15.0-x64.msi"
    ) else (
        echo   Install Node.js LTS from https://nodejs.org then re-run.
    )
    pause
    exit /b 1
)
for /f "tokens=*" %%v in ('node --version') do echo   Node.js: %%v
echo.

REM ── STEP 2: MIRROR TREE ───────────────────────────────
echo   [2/6] Mirroring agent tree to %INSTALL_DIR%...
if not exist "%INSTALL_DIR%" mkdir "%INSTALL_DIR%"
robocopy "%SCRIPT_DIR%" "%INSTALL_DIR%" /MIR /XF aixmos-state.json /R:2 /W:2 /NFL /NDL /NJH /NJS >nul
if %ERRORLEVEL% GEQ 8 (
    echo   robocopy failed with exit %ERRORLEVEL%. Investigate.
    pause
    exit /b 1
)
echo   Tree mirrored. State file preserved.
echo.

REM ── STEP 3: NPM DEPS ──────────────────────────────────
echo   [3/6] Verifying node_modules...
cd /d "%INSTALL_DIR%"
if exist "%INSTALL_DIR%\node_modules\@anthropic-ai\sdk" (
    echo   node_modules already present.
) else (
    echo   Running npm install...
    call npm.cmd install --silent
)
echo.

REM ── STEP 4: API KEY ───────────────────────────────────
echo   [4/6] Anthropic API key...
if "%ANTHROPIC_API_KEY%"=="" (
    echo   No ANTHROPIC_API_KEY found in environment.
    echo   Get yours at https://console.anthropic.com
    echo.
    set /p API_KEY="  Paste your API key (or press Enter to skip): "
    if not "!API_KEY!"=="" (
        setx ANTHROPIC_API_KEY "!API_KEY!" >nul 2>nul
        set ANTHROPIC_API_KEY=!API_KEY!
        echo   Key saved to User environment.
    ) else (
        echo   Skipped. Set ANTHROPIC_API_KEY later or use offline mode.
    )
) else (
    echo   ANTHROPIC_API_KEY already set.
)
echo.

REM ── STEP 5: DESKTOP LAUNCHERS ─────────────────────────
echo   [5/6] Creating Desktop launchers for all 10 agents...
set "DESK=%USERPROFILE%\Desktop"
set "FOLDER=%DESK%\AIXMOS-LAUNCHERS"
if not exist "%FOLDER%" mkdir "%FOLDER%"

REM Master menu launcher on Desktop root
(
echo @echo off
echo title AIXMOS - Master Orchestrator
echo cd /d "%INSTALL_DIR%"
echo node orchestrator.js
echo pause
) > "%DESK%\AIXMOS.bat"

call :MAKE_LAUNCHER CHUMMO        "orchestrator.js chummo"
call :MAKE_LAUNCHER MOOSE         "moose.js"
call :MAKE_LAUNCHER CAPTAIN       "captain.js"
call :MAKE_LAUNCHER WONDER-WOMAN  "wonderwoman.js"
call :MAKE_LAUNCHER VISION        "vision.js"
call :MAKE_LAUNCHER JARVIS        "jarvis.js"
call :MAKE_LAUNCHER TANK          "tank.js"
call :MAKE_LAUNCHER FLY-GUY       "flyguy.js"
call :MAKE_LAUNCHER BOB           "bob.js"
call :MAKE_LAUNCHER STICKS        "sticks.js"
call :MAKE_LAUNCHER MORNING-BRIEF "briefing.js"
call :MAKE_LAUNCHER BRAIN-ASK     "brain-ask.js"
call :MAKE_LAUNCHER BRAIN-STATUS  "brain-status.js"
call :MAKE_LAUNCHER RUN-AGENT-TESTS "test-all-agents.js --live"
echo   14 launchers in %FOLDER%
echo   Master menu:   %DESK%\AIXMOS.bat
echo.

REM ── STEP 6: OPTIONAL SCHEDULE + OFFLINE NOTE ──────────
echo   [6/6] Optional extras...
set /p AUTO_SCHED="  Schedule daily morning brief at 7:00 AM? (y/n): "
if /i "%AUTO_SCHED%"=="y" (
    schtasks /create /tn "AIXMOS Morning Brief" /tr "node \"%INSTALL_DIR%\briefing.js\"" /sc daily /st 07:00 /f >nul 2>nul
    if %ERRORLEVEL% EQU 0 (
        echo   Scheduled. Edit/disable in Task Scheduler.
    ) else (
        echo   Could not create scheduled task (may need admin).
    )
)
echo.

echo   ============================================================
echo    INSTALLED. Try it now:
echo   ============================================================
echo.
echo     Master menu:       Desktop\AIXMOS.bat
echo     Per-agent:         Desktop\AIXMOS-LAUNCHERS\*.bat
echo     Smoke test:        Desktop\AIXMOS-LAUNCHERS\RUN-AGENT-TESTS.bat
echo.
echo   OFFLINE MODE (optional, no internet required):
echo     From the USB:      OFFLINE-MODE-SETUP.bat
echo     Or set:            AIXMOS_LLM_BACKEND=ollama
echo                        (after installing Ollama + pulling a model)
echo.
pause
exit /b 0

REM ── HELPER: MAKE_LAUNCHER name cmd ────────────────────
:MAKE_LAUNCHER
set "NAME=%~1"
set "CMD=%~2"
(
echo @echo off
echo title AIXMOS - %NAME%
echo cd /d "%INSTALL_DIR%"
echo node %CMD%
echo pause
) > "%FOLDER%\%NAME%.bat"
exit /b 0
