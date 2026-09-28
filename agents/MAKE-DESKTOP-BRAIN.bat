@echo off
setlocal
set "SRC=%~dp0AI-BRAIN.bat"
set "DESK=%USERPROFILE%\Desktop"
set "LINK=%DESK%\AI Brain.bat"

echo Creating Desktop shortcut...
echo.

powershell -NoProfile -Command ^
  "$s = New-Object -ComObject WScript.Shell; ^
   $l = $s.CreateShortcut('%LINK%'); ^
   $l.TargetPath = '%SRC%'; ^
   $l.WorkingDirectory = '%~dp0'; ^
   $l.WindowStyle = 1; ^
   $l.Description = 'AIXMOS AI Brain'; ^
   $l.Save()"

if exist "%LINK%" (
  echo Done! Double-click "AI Brain" on your Desktop.
) else (
  echo Could not create shortcut. You can double-click:
  echo %SRC%
)
echo.
pause
