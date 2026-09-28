@echo off
setlocal
title AIXMOS Agents - START HERE
cls
echo.
echo   ============================================================
echo    AIXMOS AGENT NETWORK - START HERE
echo    10 agents: CHUMMO * MOOSE * CAPTAIN * WONDER WOMAN * VISION
echo               JARVIS * TANK * FLY GUY * BOB * STICKS
echo   ============================================================
echo.
echo   What do you want to do?
echo.
echo     1. INSTALL agents to this PC (recommended for daily use)
echo        Copies the tree to %%USERPROFILE%%\AIXMOS, creates
echo        Desktop launchers, can schedule the 7am brief.
echo.
echo     2. RUN agents from this USB (no install, fully portable)
echo        Borrowed PC or quick spin-up. Needs USB plugged in.
echo.
echo     3. SET UP OFFLINE MODE (install Ollama + local model)
echo        Lets the agents work without internet or an API key.
echo        Quality drops for voice work; analytical agents are fine.
echo.
echo     4. OPEN THE USER GUIDE (PDF)
echo.
echo     5. EXIT
echo.
set /p CHOICE="  Pick 1-5: "

set "HERE=%~dp0"
if "%HERE:~-1%"=="\" set "HERE=%HERE:~0,-1%"

if "%CHOICE%"=="1" ( call "%HERE%\install-windows.bat" & goto :END )
if "%CHOICE%"=="2" ( call "%HERE%\RUN-FROM-USB.bat"    & goto :END )
if "%CHOICE%"=="3" ( call "%HERE%\OFFLINE-MODE-SETUP.bat" & goto :END )
if "%CHOICE%"=="4" (
    if exist "%HERE%\AIXMOS-GUIDE.pdf" ( start "" "%HERE%\AIXMOS-GUIDE.pdf" ) else ^
    if exist "%HERE%\..\AIXMOS-GUIDE.pdf" ( start "" "%HERE%\..\AIXMOS-GUIDE.pdf" ) else ^
    if exist "%HERE%\AIXMOS-GUIDE.html" ( start "" "%HERE%\AIXMOS-GUIDE.html" ) else (
        echo   Guide PDF not yet generated. Run GUIDE-MAKE-PDF.bat first.
    )
    goto :END
)
if "%CHOICE%"=="5" ( goto :END )

echo   Invalid choice.

:END
echo.
pause
