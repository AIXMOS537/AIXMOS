# AIXMOS — Hand It to Your Mac or PC

**You deploy the Gateway ONCE**, from whichever machine is easiest. After that it lives on
Cloudflare, and every other device (your other Mac, the PC, both iPhones) just *talks* to it —
nothing else gets "deployed." Your Windows PC already has Claude Code, so it's the most ready.

---

## Step 1 — Get this folder onto the machine (pick one)
- **Easiest:** open claude.ai on the Mac/PC (same account) → open this chat → download `aixmos-gateway.zip` right there.
- **Mac:** AirDrop the zip from your iPhone.
- **Any machine:** drop the zip on your NAS from the iPhone, then grab it from the Mac/PC.

Then unzip: double-click (Mac) or right-click → **Extract All** (Windows).

## Step 2 — One thing first: cap the money
console.anthropic.com → set a **monthly spend limit + alert**. One minute. Do it before deploying.

## Step 3a — Let Claude Code handle it (recommended)
Open a terminal **inside the unzipped folder**, start Claude Code (`claude`), and paste this:

> Read README.md in this folder and deploy this Cloudflare Worker for me. Run deploy.sh.
> Log me into Cloudflare when the browser opens. When it asks for secrets, set
> ANTHROPIC_KEY and SECRET_PERSONAL — I'll paste the values privately. Then run the test
> command from the README and show me the result. If anything errors, fix it and keep going.

Claude Code reads the steps, runs them, deals with any hiccup, and tells you when it's live.

## Step 3b — Or do it yourself (2 commands)
In **Terminal** (Mac) or **Git Bash** (Windows), inside the folder:
```bash
bash deploy.sh
```
Set `ANTHROPIC_KEY` and `SECRET_PERSONAL` when asked (skip the rest for now). It prints your URL. Then:
```bash
export AIXMOS_GATEWAY="<that url>"
export AIXMOS_SECRET="<your SECRET_PERSONAL value>"
bash aixmos.sh "AIXMOS online. Reply in one sentence."
```
A sentence back = you're live. 🎯

## Step 4 — Use it from your OTHER machines (no redeploy)
On any other Mac/PC, just point at the live Gateway:
```bash
export AIXMOS_GATEWAY="https://your-url.workers.dev"
export AIXMOS_SECRET="your SECRET_PERSONAL value"
bash aixmos.sh "draft a follow-up to a Turo customer"
```
Add those two `export` lines to your `~/.zshrc` (Mac) or `~/.bashrc` (Git Bash) so they stick.

---

**Need:** Node.js (already on your machines from Claude Code — check `node -v`). Everything else installs itself via `npx`.
**Green light:** the test line returns a sentence. That's the whole hand-off.
