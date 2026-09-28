@echo off
setlocal EnableDelayedExpansion
title AIXMOS AI Brain
cd /d "%~dp0"
color 0B

:: ── First-time: need Node ─────────────────────────────────────
where node >nul 2>nul
if errorlevel 1 (
  color 0C
  cls
  echo.
  echo    The Brain needs Node.js once.
  echo    Ask a grown-up to run: START-HERE-FLASHDRIVE.bat
  echo    or install from https://nodejs.org
  echo.
  pause
  exit /b 1
)

:: ── Install packages quietly if needed ───────────────────────
if not exist "node_modules\" (
  echo    Setting up the Brain the first time... please wait.
  call npm install --omit=dev >nul 2>&1
)

:: ── Keys reminder (one line, not scary) ─────────────────────
if not exist ".env" (
  if not exist "config\aixmos.env" (
    echo.
    echo    NOTE: First-time grown-up setup — copy config\aixmos.env.example to .env
    echo.
  )
)

:MENU
cls
echo.
echo    ========================================================
echo.
echo              A I X M O S   A I   B R A I N
echo.
echo              Your home computer helper
echo.
echo    ========================================================
echo.
echo       1   Turn Brain ON     (start everything)
echo.
echo       2   Ask the Brain     (type a question)
echo.
echo       3   Who is Waiting?   (customers need you)
echo.
echo       4   Turn Brain OFF
echo.
echo       5   Exit
echo.
echo    ========================================================
echo.

choice /c 12345 /n /m "       Pick 1, 2, 3, 4, or 5: "

if errorlevel 5 goto BYE
if errorlevel 4 goto OFF
if errorlevel 3 goto WAITING
if errorlevel 2 goto ASK
if errorlevel 1 goto ON

:ON
cls
echo.
echo    Turning the Brain ON...
echo.
node tank.js --up
echo.
node brain-status.js
echo.
echo    ========================================================
echo    If you see "Brain: ON" above, you are good.
echo    ========================================================
echo.
pause
goto MENU

:ASK
cls
node brain-ask.js
echo.
pause
goto MENU

:WAITING
cls
echo.
echo    Checking who needs help...
echo.
node brain-status.js 2>nul
echo.
node sticks.js --scan 2>nul
if errorlevel 1 (
  echo.
  echo    Customer list needs Supabase keys in .env
  echo    ^(a grown-up sets this once^)
)
echo.
pause
goto MENU

:OFF
cls
echo.
echo    Turning the Brain OFF...
echo.
node tank.js --down
echo.
echo    Brain is OFF.
echo.
pause
goto MENU

:BYE
cls
echo.
echo    Bye!
echo.
timeout /t 2 >nul
exit /b 0
