@echo off
cd /d "E:\AIX_AI_COMMAND_SYSTEM"
for /f "delims=" %%i in ('type .env ^| findstr /v "^#" ^| findstr /v "^$"') do set "%%i"
E:\AIX_AI_COMMAND_SYSTEM\.venv\Scripts\python E:\AIX_AI_COMMAND_SYSTEM\scripts\ghl-to-airtable-sync.py >> "E:\AIX_AI_COMMAND_SYSTEM\logs\ghl-sync.log" 2>&1
