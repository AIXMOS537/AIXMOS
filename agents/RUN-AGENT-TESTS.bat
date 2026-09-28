@echo off
title AIXMOS Agent Smoke Tests
cd /d "%~dp0"
echo.
echo   Running agent smoke tests (structure + optional live API)...
echo.
where node >nul 2>&1
if errorlevel 1 (
  echo   Node.js not found. Install Node or run START-HERE-FLASHDRIVE installer.
  pause
  exit /b 1
)
if not exist node_modules (
  echo   Installing npm dependencies...
  call npm install
)
echo.
echo   === Phase 1: structure / registry / state ===
node test-all-agents.js
set PHASE1=%ERRORLEVEL%
echo.
echo   === Phase 2: live Claude API (each agent) ===
node test-all-agents.js --live
set PHASE2=%ERRORLEVEL%
echo.
if %PHASE1% neq 0 (
  echo   Phase 1 FAILED — fix syntax/registry before using agents.
) else (
  echo   Phase 1 PASSED.
)
if %PHASE2% neq 0 (
  echo   Phase 2 FAILED — check ANTHROPIC_API_KEY in .env or User env vars.
) else (
  echo   Phase 2 PASSED — all agents responded via API.
)
echo.
pause
exit /b %PHASE2%
