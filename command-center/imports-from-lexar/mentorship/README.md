Mentorship Module

Overview

This folder contains a mentorship and education scaffold derived from the provided PDFs and TMMT operator playbook. It includes:

- `curriculum.md` — high-level program outline and learning objectives
- `prompts/MASTER_MENTOR_PROMPT.md` — starter system prompt for conversational sessions
- `lessons/` — lesson markdown files (editable daily)
- `cli.py` — lightweight CLI to view lessons, format prompts, and optionally call OpenAI if `OPENAI_API_KEY` is set

Quick start

1. Read `curriculum.md`, `90_day_plan.md`, and the lessons in `lessons/`.
2. Edit lessons daily for revisions and coaching notes.
3. To run the CLI (Python 3.11 required):

```powershell
& "$env:LOCALAPPDATA\Programs\Python\Python311\python.exe" cli.py --list
```

4. For daily mentor sessions, run:

```powershell
& "$env:LOCALAPPDATA\Programs\Python\Python311\python.exe" cli.py --prompt daily
```

5. To view the full 90-day roadmap:

```powershell
& "$env:LOCALAPPDATA\Programs\Python\Python311\python.exe" cli.py --plan
```

6. To use low-token Codex-style output, set environment variables and run:

```powershell
setx OPENAI_API_KEY "sk-..."
setx OPENAI_MODEL "gpt-4o-mini"
& "$env:LOCALAPPDATA\Programs\Python\Python311\python.exe" cli.py --codex "Write a 3-point follow-up message template for rental leads"
```

Optional: set `OPENAI_API_KEY` and `OPENAI_MODEL` to enable remote chat and Codex-style calls.
