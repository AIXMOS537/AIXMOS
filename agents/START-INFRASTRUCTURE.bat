@echo off
title AIXMOS Infrastructure Agents
cd /d "%~dp0"
if not exist node_modules (
  echo Installing dependencies...
  call npm install
)
echo.
echo  JARVIS + full agent council
echo  Primary: node jarvis.js
echo.
node jarvis.js
pause
