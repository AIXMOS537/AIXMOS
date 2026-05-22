@echo off
setlocal
cls
echo.
echo   ============================================================
echo    AIXMOS AGENTS - FLASH DRIVE INSTALL
echo   ============================================================
echo.
where node >nul 2>nul
if errorlevel 1 (
  echo   Node.js is not installed on this computer.
  echo.
  if exist "%~dp0_installers\node-v24.15.0-x64.msi" (
    echo   Opening the included Node.js installer now.
    echo   Finish the installer, then run this START-HERE file again.
    echo.
    pause
    start "" "%~dp0_installers\node-v24.15.0-x64.msi"
    exit /b 1
  ) else (
    echo   Node installer was not found in _installers.
    echo   Install Node.js from https://nodejs.org, then run this again.
    echo.
    pause
    exit /b 1
  )
)
echo   Node.js found.
echo.
call "%~dp0LOAD-ME-FIRST-WINDOWS.bat"
