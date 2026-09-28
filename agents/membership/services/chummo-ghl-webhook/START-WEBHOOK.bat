@echo off
setlocal
title CHUMMO-GHL Webhook
cd /d "%~dp0"

if "%GHL_WEBHOOK_SHARED_SECRET%"=="" (
    echo.
    echo   GHL_WEBHOOK_SHARED_SECRET is not set in this terminal.
    echo   Set it once via:  setx GHL_WEBHOOK_SHARED_SECRET "your-long-random-secret"
    echo   then open a NEW terminal and run this script again.
    echo.
    pause
    exit /b 1
)

if "%PORT%"=="" set PORT=4099

echo.
echo   ============================================================
echo    CHUMMO-GHL Webhook
echo    Port:       %PORT%
echo    Health URL: http://localhost:%PORT%/health
echo    Endpoints:  POST /draft, /draft/sms, /draft/email, /draft/dm
echo    Backend:    %AIXMOS_LLM_BACKEND%
echo   ============================================================
echo.

node server.js
echo.
echo   Server stopped. Press a key to exit.
pause
