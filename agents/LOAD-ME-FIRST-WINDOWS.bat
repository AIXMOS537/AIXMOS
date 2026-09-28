@echo off
setlocal
cls
echo.
echo   ============================================================
echo    AIXMOS AGENT NETWORK - LOAD ME FIRST
echo   ============================================================
echo.
echo   This will install the agents to:
echo   %USERPROFILE%\AIXMOS
echo.
echo   It will also create Desktop launchers.
echo.
pause
call "%~dp0install-windows.bat"
