@echo off
REM Double-click this. It is the only file in this folder you need.
cd /d "%~dp0"
where bash >nul 2>nul
if %errorlevel%==0 (
  bash bin/aixmos
) else (
  echo AIXMOS needs Git Bash or WSL on Windows.
  echo Install Git for Windows: https://git-scm.com/download/win
  echo Then double-click this file again.
  echo.
  echo Or run the classic installer instead:  install-windows.bat
  pause
)
