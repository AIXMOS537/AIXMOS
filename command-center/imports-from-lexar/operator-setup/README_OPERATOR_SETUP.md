Operator Plug-and-Play Setup

Goal

Make any Windows computer into a ready operator workstation when the flash drive is plugged in.

What this contains

- `install_operator.ps1` — creates a local Python venv and installs the operator tools
- `run_operator.ps1` — launches the daily mentor/operator workflow
- `operator_start.bat` — quick double-click launcher for Windows
- `operator_requirements.txt` — required Python packages

How to install

1. Plug the flash drive into the computer.
2. Open PowerShell as Administrator or a standard user.
3. Run:

```powershell
cd D:\AIX_AI_COMMAND_SYSTEM\operator-setup
powershell -ExecutionPolicy Bypass -File .\install_operator.ps1
```

What it does

- Uses `py` or `python` to create a virtual environment in `operator-setup\venv`
- Installs `openai`, `pdfminer.six`, and any other operator dependencies
- Prepares the `run_operator.ps1` launcher

Daily use

To start the operator workspace:

```powershell
cd D:\AIX_AI_COMMAND_SYSTEM\operator-setup
powershell -ExecutionPolicy Bypass -File .\run_operator.ps1
```

Or double-click `operator_start.bat`.

If you want AI-assisted prompts and code generation, set these:

```powershell
setx OPENAI_API_KEY "sk-..."
setx OPENAI_MODEL "gpt-4o-mini"
```

Then use the built-in CLI commands:

```powershell
& .\venv\Scripts\python.exe ..\mentorship\cli.py --prompt daily
& .\venv\Scripts\python.exe ..\mentorship\cli.py --plan
& .\venv\Scripts\python.exe ..\mentorship\cli.py --codex "Write a short follow-up message for a rental lead"
```

Operator access

This setup gives any operator access to:
- the 90-day mentorship plan
- daily mentor prompt and lesson content
- low-token Codex prompt templates
- a one-click morning workflow

If you want, I can also add a `operator_dashboard.html` web UI for even easier daily use.
