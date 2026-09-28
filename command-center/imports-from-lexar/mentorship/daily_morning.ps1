$PY = "C:\Users\Microsoft-Laptop\AppData\Local\Programs\Python\Python311\python.exe"
Push-Location D:\AIX_AI_COMMAND_SYSTEM\mentorship
Write-Host "--- Daily Mentor Prompt ---`n"
& $PY .\cli.py --prompt daily
Write-Host "`n--- Today's Lesson (01-intro.md) ---`n"
& $PY .\cli.py --show 01-intro.md
Write-Host "`n--- 90-Day Plan ---`n"
& $PY .\cli.py --plan
Pop-Location
