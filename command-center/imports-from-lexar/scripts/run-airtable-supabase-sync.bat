@echo off
cd /d "E:\AIX_AI_COMMAND_SYSTEM"
for /f "delims=" %%i in ('type .env ^| findstr /v "^#" ^| findstr /v "^$"') do set "%%i"
E:\AIX_AI_COMMAND_SYSTEM\.venv\Scripts\python E:\AIX_AI_COMMAND_SYSTEM\scripts\airtable-to-supabase-sync.py >> "E:\AIX_AI_COMMAND_SYSTEM\logs\airtable-supabase-sync.log" 2>&1
