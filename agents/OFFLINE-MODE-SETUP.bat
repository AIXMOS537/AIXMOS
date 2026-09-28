@echo off
setlocal EnableDelayedExpansion
title AIXMOS - OFFLINE MODE SETUP (Ollama)
cls
echo.
echo   ============================================================
echo    AIXMOS - OFFLINE MODE SETUP
echo    Installs Ollama and pulls a local model so agents can run
echo    without internet or an Anthropic API key.
echo   ============================================================
echo.
echo   QUALITY NOTE:
echo     Local models are noticeably weaker than Claude Sonnet for
echo     voice/brand work (CHUMMO drafts, customer messages).
echo     Analytical agents (BOB, STICKS, VISION verdicts) hold up better.
echo.
echo   This script:
echo     1. Opens the official Ollama Windows installer
echo     2. Waits for you to install it
echo     3. Pulls Phi-3 Mini (~2.3 GB, fits anywhere)
echo     4. Optionally pulls Llama 3.1 8B (~4.7 GB, better quality)
echo     5. Switches AIXMOS_LLM_BACKEND to ollama in your User env
echo.
pause

REM ── STEP 1: OLLAMA INSTALL ────────────────────────────
echo.
echo   [1/5] Checking Ollama...
where ollama >nul 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo   Ollama not found. Opening official download page.
    echo   Install it, then come back to this window and press a key.
    start https://ollama.com/download/windows
    pause
    where ollama >nul 2>nul
    if !ERRORLEVEL! NEQ 0 (
        echo   Ollama still not on PATH. Open a new terminal after install
        echo   and run this script again.
        pause
        exit /b 1
    )
)
echo   Ollama detected.
echo.

REM ── STEP 2: SERVICE RUNNING ───────────────────────────
echo   [2/5] Starting Ollama service...
start "" /B ollama serve >nul 2>nul
timeout /t 3 /nobreak >nul
echo   Service kicked off (it also auto-starts on login).
echo.

REM ── STEP 3: PULL PHI-3 ────────────────────────────────
echo   [3/5] Pulling Phi-3 Mini (~2.3 GB)...
ollama pull phi3:mini
if %ERRORLEVEL% NEQ 0 (
    echo   Pull failed. Check internet + try again.
    pause
    exit /b 1
)
echo.

REM ── STEP 4: OPTIONAL LLAMA 8B ─────────────────────────
echo   [4/5] Optional: pull Llama 3.1 8B (~4.7 GB, better quality)
set /p PULL_LLAMA="  Pull Llama 3.1 8B now? (y/n): "
if /i "%PULL_LLAMA%"=="y" (
    ollama pull llama3.1:8b
    if !ERRORLEVEL! EQU 0 (
        echo   Llama 3.1 8B ready.
        set "MODEL=llama3.1:8b"
    ) else (
        echo   Llama pull failed. Falling back to phi3:mini.
        set "MODEL=phi3:mini"
    )
) else (
    set "MODEL=phi3:mini"
)
echo.

REM ── STEP 5: WIRE ENV VARS ─────────────────────────────
echo   [5/5] Configuring AIXMOS environment...
setx AIXMOS_LLM_BACKEND "ollama" >nul
setx OLLAMA_HOST "http://localhost:11434" >nul
setx OLLAMA_MODEL "%MODEL%" >nul
echo   AIXMOS_LLM_BACKEND=ollama
echo   OLLAMA_MODEL=%MODEL%
echo.
echo   These are set in your User environment. Open a NEW terminal
echo   for them to take effect. To switch back to Claude:
echo     setx AIXMOS_LLM_BACKEND "claude"
echo.
echo   ============================================================
echo    OFFLINE MODE READY. Test it:
echo      1. Open a new terminal
echo      2. cd %USERPROFILE%\AIXMOS  (or this USB folder)
echo      3. node test-all-agents.js --live
echo   ============================================================
echo.
pause
