---
name: team-drive-kit
description: Plug-and-play USB setup kit that onboards any Win/Mac machine to the TMMT team
metadata: 
  node_type: memory
  type: project
  originSessionId: 05286da1-b7da-474a-bb4e-c792d0a2d7ff
---

A portable setup kit that turns any computer into a TMMT node (see [[tmmt-system]], [[device-architecture]]).

- **Master copy:** `C:\Users\AIXMOS\TMMT-TEAM-DRIVE` (on the Surface tablet). Reload more flash drives by copying this folder to `<DRIVE>:\TMMT-SETUP`.
- **Deployed to:** USB drives E: "CYBORG" and F: "AIXMOS02" (folder `TMMT-SETUP`).

**What the kit does per machine:** installs Claude Code (`npm i -g @anthropic-ai/claude-code`), Node, Git, GitHub CLI (winget on Windows / Homebrew on Mac), clones the public repo `https://github.com/Metavibez4L/TMMT.git` to `~/TMMT` (Win: `%USERPROFILE%\TMMT`), runs `npm install`, and writes `.env` from `config/.env.public`. Idempotent — re-running updates the repo and never overwrites an existing `.env`.

**Run it:** Windows = double-click `windows\SETUP.bat`. Mac = `bash <drive>/mac/setup.sh` in Terminal (double-click `SETUP.command` also works if Gatekeeper allows).

**Smart-split secrets:** the drive's `config/.env.public` holds only the Supabase URL + publishable key (safe — publishable key is public anyway). The **service-role key is NOT on the drive**; paste it into `~/TMMT/.env` only on trusted power machines (work-Mac hub, brainiac PC), not office PCs.

**Two manual per-machine steps no script can do:** (1) `claude` then sign in once; (2) `gh auth login` only if that machine will push code.

**Gotcha:** keep the `.ps1`/`.sh` scripts pure ASCII — em-dashes in a no-BOM file broke the PowerShell parser ("missing closing }").
