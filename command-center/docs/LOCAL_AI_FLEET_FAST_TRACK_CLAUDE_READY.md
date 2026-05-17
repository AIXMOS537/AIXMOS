# Local AI Fleet Fast-Track Runbook

Use this file with Claude Code, Cursor, ChatGPT, or any terminal assistant to help set up a 5-7 computer local-first AI fleet.

Goal: make 5-7 computers in one room behave like one powerful distributed workstation.

- MacBooks / main workstation = daily control station, editor, voice, browser, chat UI
- Best GPU desktop = local AI inference server
- Second desktop = builds, tests, agents, Docker, long-running jobs
- Third desktop = repos, backups, memory, vector database
- Extra desktops/laptops = optional workers, screens, monitoring, fallback

Do not run a full AI stack on every machine. One brain, many muscles.

---

## 0. Machine Naming Plan

Before installing anything, assign names.

Use these names or replace them with your own:

```text
ai-1       Best GPU desktop. Ollama, Open WebUI, local AI models, voice STT/TTS.
build-1    Build/test/agent desktop. Docker, tmux, CI, Aider, Claude Code, OpenCode.
data-1     Data/memory desktop. Git mirrors, Gitea, backups, vector DB.
mac-1      Main MacBook or daily driver.
mac-2      Backup/travel MacBook.
spare-1    Optional extra workstation.
spare-2    Optional extra workstation.
```

Screen layout:

```text
Screen 1: Main editor - Cursor / VS Code
Screen 2: Terminal / tmux sessions
Screen 3: Open WebUI / local AI chat
Screen 4: Browser / docs / app preview
Screen 5: Logs / CI / Docker / agents
Screen 6: GitHub / issues / planning
Screen 7: Monitoring dashboard
Screen 8: Notes / voice / calendar / scratchpad
```

---

## 1. Install Tailscale On Every Machine

Do this first. Everything else depends on private networking.

Install Tailscale:

- macOS: https://tailscale.com/download/mac
- Windows: https://tailscale.com/download/windows
- Linux: https://tailscale.com/download/linux

Sign in to the same Tailscale account/tailnet on every machine.

Then rename machines in the Tailscale admin console:

```text
ai-1
build-1
data-1
mac-1
mac-2
spare-1
spare-2
```

From `mac-1`, test:

```bash
ping ai-1
ping build-1
ping data-1
```

Also test SSH if enabled:

```bash
ssh ai-1
ssh build-1
ssh data-1
```

If SSH does not work yet, continue to the SSH section.

---

## 2. Create SSH Config On MacBooks

On each MacBook, edit:

```bash
nano ~/.ssh/config
```

Add:

```sshconfig
Host ai-1
  HostName ai-1
  User YOUR_USERNAME
  ServerAliveInterval 30
  ServerAliveCountMax 4

Host build-1
  HostName build-1
  User YOUR_USERNAME
  ServerAliveInterval 30
  ServerAliveCountMax 4

Host data-1
  HostName data-1
  User YOUR_USERNAME
  ServerAliveInterval 30
  ServerAliveCountMax 4
```

Replace `YOUR_USERNAME` with your account name on each desktop.

Generate an SSH key if needed:

```bash
ssh-keygen -t ed25519 -C "local-ai-fleet"
```

Copy your key to each machine:

```bash
ssh-copy-id ai-1
ssh-copy-id build-1
ssh-copy-id data-1
```

If `ssh-copy-id` is unavailable, ask Claude Code:

```text
Help me copy my SSH public key from this Mac to ai-1, build-1, and data-1. I am using Tailscale names. Give me exact commands and explain what each command does.
```

---

## 3. Install Shared Keyboard/Mouse Control

Pick one:

```text
Synergy     Polished paid option.
Barrier     Free/open-source option.
KVM switch   Hardware fallback.
Parsec       Remote desktop option.
Moonlight    Low-latency remote option, especially with NVIDIA/GameStream-style setup.
SSH + tmux   Best for terminal work.
```

Recommended:

```text
Use Synergy or Barrier for keyboard/mouse across screens.
Use SSH + tmux for terminal control.
Use Parsec/Moonlight only where you need full remote desktop.
```

---

## 4. Set Up `ai-1`: Local AI Server

Purpose:

```text
ai-1 runs local models and exposes them privately over Tailscale.
MacBooks and other desktops call ai-1 instead of running big models locally.
```

Install:

```text
NVIDIA driver / CUDA if using NVIDIA GPU
Ollama
Docker
Open WebUI
Whisper/faster-whisper later
Piper/Kokoro later
```

Install Ollama:

https://ollama.com/download

Pull starter models:

```bash
ollama pull qwen2.5-coder:14b
ollama pull qwen2.5:7b
ollama pull nomic-embed-text
```

If VRAM is strong enough, also try:

```bash
ollama pull qwen2.5-coder:32b
ollama pull deepseek-r1:32b
```

Test locally on `ai-1`:

```bash
ollama run qwen2.5-coder:14b
```

From `mac-1`, test remote Ollama:

```bash
OLLAMA_HOST=http://ai-1:11434 ollama list
OLLAMA_HOST=http://ai-1:11434 ollama run qwen2.5-coder:14b
```

If this fails, ask Claude Code:

```text
I have Ollama running on ai-1 and I am trying to access it from mac-1 over Tailscale using http://ai-1:11434. Help me debug. Check whether Ollama is listening on the right interface, whether firewall rules are blocking it, and how to bind it safely to the Tailscale interface only.
```

Important security rule:

```text
Do not expose Ollama to the public internet.
Use Tailscale/private LAN only.
```

---

## 5. Install Open WebUI On `ai-1`

Open WebUI gives you a browser chat interface for local models.

Recommended Docker approach:

```bash
docker run -d \
  --name open-webui \
  -p 3000:8080 \
  -e OLLAMA_BASE_URL=http://host.docker.internal:11434 \
  -v open-webui:/app/backend/data \
  --restart always \
  ghcr.io/open-webui/open-webui:main
```

On Linux, Docker may need this extra flag:

```bash
--add-host=host.docker.internal:host-gateway
```

Open from MacBook:

```text
http://ai-1:3000
```

If the container cannot reach Ollama, ask Claude Code:

```text
Fix my Open WebUI Docker command so the container can reach Ollama running on ai-1. My goal is to access Open WebUI from mac-1 at http://ai-1:3000 and use Ollama models running on ai-1.
```

---

## 6. Set Up `build-1`: Build, Test, Agents

Purpose:

```text
build-1 runs Docker, tests, CI, long-running terminal agents, and heavy project tasks.
Your MacBook stays cool and responsive.
```

Install:

```text
Git
Docker
tmux
Node.js
Python
Go/Rust/etc as needed
Claude Code
Aider
OpenCode
GitHub CLI
```

Start using `tmux`:

```bash
ssh build-1
tmux new -s work
```

Useful tmux commands:

```text
Ctrl-b d        detach session
tmux attach -t work
tmux ls
```

Run long jobs here:

```bash
npm test
docker compose up
aider --model ollama_chat/qwen2.5-coder:14b --ollama-api-base http://ai-1:11434
```

Ask Claude Code:

```text
Create a bootstrap checklist for build-1. I want Docker, tmux, Git, Node.js, Python, GitHub CLI, Claude Code, Aider, and OpenCode. Make it safe, step-by-step, and ask before destructive changes.
```

---

## 7. Set Up `data-1`: Repos, Memory, Backups

Start simple.

Install:

```text
Git
Gitea or bare git mirrors
restic
Qdrant or Chroma later
Syncthing optionally for notes/dotfiles only
```

Recommended initial setup:

```text
Use data-1 as the source of truth for repo mirrors and backups.
Do not sync huge folders like node_modules.
Do not create five divergent copies of repos across every machine.
```

Possible layout:

```text
/srv/git
/srv/gitea
/srv/backups
/srv/vector
/srv/docs
```

Ask Claude Code:

```text
Help me set up data-1 as my repo and backup server. I want Gitea or bare Git mirrors, restic backups, and a clean directory layout under /srv. Ask me questions only when absolutely necessary.
```

---

## 8. Main MacBook Setup

Install:

```text
Tailscale
Cursor
VS Code if desired
Continue extension
Ollama client
Claude Code
Aider
iTerm2 or preferred terminal
1Password or SSH key manager
Syncthing optionally for notes/dotfiles
```

Set Ollama remote host:

```bash
export OLLAMA_HOST=http://ai-1:11434
```

Add to shell profile:

```bash
echo 'export OLLAMA_HOST=http://ai-1:11434' >> ~/.zshrc
```

Test:

```bash
ollama list
ollama run qwen2.5-coder:14b
```

Configure Continue or local AI editor plugin to use:

```text
Provider: Ollama
Base URL: http://ai-1:11434
Model: qwen2.5-coder:14b
Embeddings: nomic-embed-text
```

---

## 9. Tool Roles

Use each AI tool for the job it is best at.

```text
Open WebUI
  Browser chat with local models.
  Best for general questions, planning, summaries, code explanation.

Continue
  Local model chat/editing inside editor.
  Best for low-cost local coding help.

Cursor
  Premium IDE and cloud agent.
  Best for high-value coding, architecture, stubborn bugs, PR review.

Claude Code
  Terminal coding agent.
  Best for scripts, Docker Compose, debugging installs, editing repos, automation.

Aider / OpenCode
  Terminal coding assistants.
  Best for local or hybrid model-driven refactors.

Tailscale
  Private network.
  Best for stable machine names, private service access, no port forwarding.

tmux
  Persistent remote terminal sessions.
  Best for long-running jobs on build-1.
```

Rule:

```text
Local models first for volume work.
Cloud models only for architecture, nasty bugs, security/legal review, or when local fails twice.
```

---

## 10. Claude Code Master Prompt

Paste this into Claude Code on any machine:

```text
You are helping me set up a local-first AI fleet.

My machines are:
- ai-1: best GPU desktop, runs Ollama, Open WebUI, local models, voice STT/TTS
- build-1: build/test/agent desktop, runs Docker, tmux, CI, Aider/OpenCode/Claude Code
- data-1: repos, backups, memory, Gitea, restic, optional vector DB
- mac-1: main daily driver and control station
- mac-2: backup/travel daily driver
- spare machines may exist later

Constraints:
- Use Tailscale/private networking.
- Do not expose Ollama, Open WebUI, SSH, Gitea, or dashboards to the public internet.
- Prefer safe, reversible setup steps.
- Ask before destructive changes.
- Give commands for my current OS.
- Explain how to verify each step.
- If something fails, debug from first principles: service status, listening ports, firewall, hostname resolution, credentials, logs.

Current task:
<REPLACE THIS WITH THE TASK>
```

Example tasks:

```text
Set up Ollama on ai-1 and make it reachable from mac-1 over Tailscale.
```

```text
Write a Docker Compose file for Open WebUI on ai-1 connected to Ollama.
```

```text
Create an SSH config for mac-1 so I can connect to ai-1, build-1, and data-1.
```

```text
Help me configure Continue in Cursor to use Ollama at http://ai-1:11434.
```

```text
Set up tmux on build-1 and create a workflow for long-running agent sessions.
```

```text
Set up data-1 with Gitea and restic backups.
```

---

## 11. Cursor Prompt

Paste this into Cursor when working inside a repo:

```text
We are using a local-first AI fleet.

Use local models for routine code explanation, refactors, tests, docs, and repetitive edits when possible.
Use cloud reasoning only when the task requires high judgment or local attempts fail.

Infrastructure:
- ai-1 runs Ollama and Open WebUI.
- build-1 runs Docker, tests, tmux, and terminal agents.
- data-1 stores repos, mirrors, backups, and later vector search.
- mac-1 is the main editor/control machine.

For this repo, keep changes scoped and safe.
Before editing, inspect the relevant files.
After editing, run the smallest useful verification command.
Do not rewrite unrelated code.

Task:
<REPLACE THIS WITH THE CODING TASK>
```

---

## 12. Weekend Fast-Track Schedule

### Day 1: Network And Control

Checklist:

```text
[ ] Install Tailscale on every machine
[ ] Rename machines in Tailscale
[ ] Confirm ping from mac-1 to ai-1/build-1/data-1
[ ] Set up SSH keys
[ ] Confirm SSH from mac-1 to desktops
[ ] Install Synergy/Barrier or decide on KVM
[ ] Create screen role layout
```

Success condition:

```text
From mac-1, I can SSH into ai-1, build-1, and data-1 by name.
```

### Day 2: Local AI

Checklist:

```text
[ ] Install Ollama on ai-1
[ ] Pull qwen2.5-coder:14b
[ ] Pull qwen2.5:7b
[ ] Pull nomic-embed-text
[ ] Test Ollama locally
[ ] Test Ollama from mac-1 using OLLAMA_HOST
[ ] Install Open WebUI
[ ] Open http://ai-1:3000 from mac-1
```

Success condition:

```text
From a MacBook browser, I can chat with a model running on ai-1.
```

### Day 3: Build Machine

Checklist:

```text
[ ] Install Docker on build-1
[ ] Install tmux on build-1
[ ] Install Git/language runtimes
[ ] Install Claude Code/Aider/OpenCode
[ ] Run a long command in tmux
[ ] Detach and reattach successfully
```

Success condition:

```text
I can start a job on build-1, close the laptop, come back, and the job is still running.
```

### Day 4: Data Machine

Checklist:

```text
[ ] Create /srv directory layout
[ ] Install Gitea or create bare git mirrors
[ ] Set up restic backups
[ ] Test restore of one small file
```

Success condition:

```text
My repos and important files have a clear source of truth and a tested backup path.
```

### Day 5: Editor Integration

Checklist:

```text
[ ] Install Cursor on mac-1
[ ] Install Continue
[ ] Configure Continue to use ai-1 Ollama
[ ] Install Claude Code on mac-1 and build-1
[ ] Install Aider
[ ] Test local model from editor
[ ] Test local model from terminal
```

Success condition:

```text
I can edit on mac-1 while AI runs on ai-1 and builds/tests run on build-1.
```

---

## 13. Debug Checklist

When something fails, check in this order:

```text
1. Can I ping the machine name?
2. Can I SSH into the machine?
3. Is the service running?
4. Is the service listening on the expected port?
5. Is it bound to localhost only or reachable on Tailscale?
6. Is the firewall blocking it?
7. Are Docker containers healthy?
8. Are logs showing auth, network, or permission errors?
9. Am I using the right hostname and port?
10. Did I accidentally expose something publicly?
```

Useful commands:

```bash
tailscale status
ping ai-1
ssh ai-1
curl http://ai-1:11434/api/tags
curl http://ai-1:3000
docker ps
docker logs open-webui
tmux ls
```

On Linux:

```bash
systemctl status ollama
ss -tulpn
ufw status
```

On macOS:

```bash
lsof -iTCP -sTCP:LISTEN -n -P
```

On Windows PowerShell:

```powershell
Get-NetTCPConnection -State Listen
Get-Service
```

---

## 14. Security Rules

```text
Do not port-forward Ollama.
Do not expose Open WebUI publicly unless you know exactly what you are doing.
Use Tailscale/private network.
Use SSH keys, not passwords where possible.
Use a password manager.
Back up secrets separately and carefully.
Keep one source of truth for repos.
Test backups by restoring files.
```

---

## 15. Final Target Workflow

Daily flow:

```text
1. Sit at mac-1 / control station.
2. Open Cursor or VS Code on Screen 1.
3. Open terminal/tmux on Screen 2.
4. Open Open WebUI at http://ai-1:3000 on Screen 3.
5. Run app previews/docs/browser on Screen 4.
6. Watch build-1 logs/CI on Screen 5.
7. Keep tasks/issues on Screen 6.
8. Keep monitoring/notes/voice on Screens 7-8.
```

Compute flow:

```text
AI inference -> ai-1
Builds/tests/agents -> build-1
Repos/backups/memory -> data-1
Editing/chat/control -> mac-1/mac-2
```

Decision rule:

```text
Use local AI first.
Use cloud AI when judgment matters.
Use build-1 for long-running work.
Use data-1 as source of truth.
Use Tailscale for private access.
```

This is the end state: one room, many machines, one cockpit.

