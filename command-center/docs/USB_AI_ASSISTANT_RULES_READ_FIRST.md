# USB AI Assistant Rules - Read First

Use this file when giving the USB drive to Claude, Cursor, ChatGPT, or any other AI coding assistant.

Important: this USB may contain a copy of a full user drive. Treat it as private and sensitive.

---

## Master Instruction For Claude / Cursor

Paste this first:

```text
You are helping me set up a local-first AI fleet using the files on this USB drive.

Important security rules:
- Do not upload, summarize, index, or inspect the entire USB drive.
- Do not scan my whole user folder unless I explicitly ask.
- Do not open credential folders or secret files.
- Do not read browser profiles, password manager data, SSH private keys, API keys, .env files, tokens, cookies, AppData, or system keychains.
- Ask before installing software, changing system settings, modifying SSH config, modifying firewall rules, or starting network services.
- Ask before deleting, moving, renaming, syncing, or uploading anything.
- Prefer reading the setup runbook first:
  LOCAL_AI_FLEET_FAST_TRACK_CLAUDE_READY.md
- Use only the files I specifically point you to.
- If you need a config file, ask me for that file directly instead of searching the whole drive.
- If you accidentally encounter secrets, stop and tell me without printing the secret value.

Goal:
Help me execute the local AI fleet setup step by step across my machines:
- ai-1: best GPU desktop, local AI server
- build-1: builds, tests, Docker, terminal agents
- data-1: repos, backups, memory
- mac-1: main daily driver
- mac-2: backup/travel daily driver

Start by reading LOCAL_AI_FLEET_FAST_TRACK_CLAUDE_READY.md and giving me the next 3 actions for the machine I am currently using.
```

---

## Safe Files To Share With AI

These are usually safe:

```text
LOCAL_AI_FLEET_FAST_TRACK_CLAUDE_READY.md
USB_AI_ASSISTANT_RULES_READ_FIRST.md
machine_names.txt
install_checklist.txt
ssh_config_template.txt
Docker Compose templates you created for this setup
README files
non-secret project source code
```

---

## Do Not Upload Or Paste These Into AI

Do not upload or paste:

```text
.ssh private keys
.env files
API keys
access tokens
browser profiles
cookies
password manager exports
AppData
keychains
cloud sync auth folders
wallet files
bank/tax/identity documents
personal photos unless needed
Downloads folder unless you inspect it first
```

Common sensitive paths on Windows:

```text
C:\Users\taha1\.ssh
C:\Users\taha1\AppData
C:\Users\taha1\.aws
C:\Users\taha1\.azure
C:\Users\taha1\.config
C:\Users\taha1\.docker
C:\Users\taha1\.git-credentials
C:\Users\taha1\Downloads
C:\Users\taha1\OneDrive
```

Common sensitive paths on macOS:

```text
~/.ssh
~/.aws
~/.azure
~/.config
~/.docker
~/.git-credentials
~/Library/Application Support
~/Library/Keychains
~/Downloads
~/Desktop
~/Documents
```

---

## If The AI Wants To Search The USB

Say:

```text
Do not search the entire USB. Only inspect the specific setup files I list:
- LOCAL_AI_FLEET_FAST_TRACK_CLAUDE_READY.md
- USB_AI_ASSISTANT_RULES_READ_FIRST.md

If you need another file, ask me for the exact path and reason.
```

---

## If The AI Needs SSH

Allowed:

```text
Help me create a new SSH key.
Help me create an SSH config template.
Help me copy a public key to ai-1/build-1/data-1.
Help me verify SSH works.
```

Not allowed without explicit permission:

```text
Reading existing SSH private keys.
Printing private keys.
Uploading keys.
Changing authorized_keys without asking.
Deleting old keys.
```

Safe prompt:

```text
Help me set up SSH for my local AI fleet. Do not read or print any private keys. If a key is needed, help me generate a new one and copy only the public key.
```

---

## If The AI Needs Tailscale

Allowed:

```text
Help install Tailscale.
Help rename machines.
Help test ping/SSH between machines.
Help write ACL suggestions.
```

Not allowed without explicit permission:

```text
Changing ACLs.
Enabling public sharing.
Enabling Funnel/public exposure.
Exposing Ollama or Open WebUI publicly.
```

Safe prompt:

```text
Help me configure Tailscale for private access only. Do not enable public sharing or Funnel. I want ai-1, build-1, and data-1 reachable only from my own devices.
```

---

## If The AI Needs Ollama / Open WebUI

Allowed:

```text
Install Ollama.
Pull models.
Run Open WebUI locally.
Connect MacBook to ai-1 over Tailscale.
Debug local network access.
```

Not allowed without explicit permission:

```text
Public port forwarding.
Exposing Ollama to the internet.
Opening firewall to all networks.
Uploading model chats/logs.
```

Safe prompt:

```text
Help me run Ollama and Open WebUI on ai-1 privately over Tailscale. Do not expose either service publicly.
```

---

## If The AI Needs To Install Tools

Before installing anything, the AI should show:

```text
Tool name
Why it is needed
Install command
What it changes
How to uninstall or disable it
How to verify it worked
```

Safe prompt:

```text
Before installing anything, show me the exact command, what it changes, and how I can undo it.
```

---

## First Prompt To Use On The MacBook

Paste this into Claude Code or Cursor on the MacBook:

```text
Read USB_AI_ASSISTANT_RULES_READ_FIRST.md first.
Then read LOCAL_AI_FLEET_FAST_TRACK_CLAUDE_READY.md.

Do not scan the whole USB drive.
Do not inspect secrets, credentials, browser profiles, AppData, keychains, SSH private keys, .env files, cookies, or tokens.

I am setting up my local AI fleet. This MacBook is my daily driver.
Give me the next 3 actions only. For each action, include exact commands and how to verify it worked.
```

---

## Emergency Rule

If anything feels wrong, stop and use this:

```text
Pause. Do not make changes. Summarize what you were about to do, what files or settings you need, and why.
```

---

## Bottom Line

Use the USB as a reference kit, not as something to blindly upload.

The only file the AI should need first is:

```text
LOCAL_AI_FLEET_FAST_TRACK_CLAUDE_READY.md
```

This file adds the rules:

```text
USB_AI_ASSISTANT_RULES_READ_FIRST.md
```

