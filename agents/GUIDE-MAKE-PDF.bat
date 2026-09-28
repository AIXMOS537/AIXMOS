@echo off
setlocal
title AIXMOS - Render Guide to PDF
cd /d "%~dp0"
echo.
echo   Rendering AIXMOS-GUIDE.md to HTML + PDF...
echo.

REM Step 1 - md to html
node lib\build-guide.js
if errorlevel 1 (
    echo   md to html failed.
    pause
    exit /b 1
)

REM Step 2 - html to pdf via Edge headless
set "EDGE=%ProgramFiles(x86)%\Microsoft\Edge\Application\msedge.exe"
if not exist "%EDGE%" set "EDGE=%ProgramFiles%\Microsoft\Edge\Application\msedge.exe"
if not exist "%EDGE%" (
    echo   Microsoft Edge not found. Install it from https://microsoft.com/edge
    echo   OR open AIXMOS-GUIDE.html in any browser and use Print to PDF.
    pause
    exit /b 1
)

set "HTML_URI=file:///%~dp0AIXMOS-GUIDE.html"
set "HTML_URI=%HTML_URI:\=/%"
"%EDGE%" --headless --disable-gpu --no-pdf-header-footer --print-to-pdf="%~dp0AIXMOS-GUIDE.pdf" "%HTML_URI%"
if errorlevel 1 (
    echo   PDF render failed.
    pause
    exit /b 1
)

echo.
echo   Done:
echo     AIXMOS-GUIDE.md   (source)
echo     AIXMOS-GUIDE.html (browser view)
echo     AIXMOS-GUIDE.pdf  (print ready)
echo.
pause
