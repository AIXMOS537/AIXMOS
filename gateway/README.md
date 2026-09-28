# AIXMOS Gateway — Ship It

This folder is your AIXMOS **brain hub**. Deploy it once to Cloudflare (free), and every
device you own — both Macs, your PC, both iPhones — plus your team can talk to AIXMOS
through it, with your API key kept safe and your spending capped.

## In plain terms
- The Gateway is a tiny program that runs on Cloudflare's free network.
- It holds your AIXMOS API key, so the key never sits on a phone or laptop.
- Each person or device sends it a prompt + a password ("secret"); it replies with AIXMOS's answer.
- It picks which AIXMOS model to use per role and caps how much each role can spend.

## What you need first (one-time, ~10 min)
1. **Node.js** installed (you already have it from AIXMOS Engine). Check: `node -v`
2. A free **Cloudflare account** — dash.cloudflare.com
3. An **AIXMOS API key** — console.anthropic.com → API Keys
   → While there, set a **monthly spend limit + usage alert**. Do this before anything else.

## Ship it (3 steps, ~5 min)
Open **Terminal** (Mac) or **Git Bash** (Windows), then:
```bash
cd aixmos-gateway
bash deploy.sh
```
The script: installs the Cloudflare tool if needed (via npx — no global install), logs you in
(opens a browser), creates the memory store and wires it up for you, asks for your secrets
(typed privately, **never saved to a file**), and deploys. At the end it prints your **Gateway URL** — copy it.

When asked for secrets, set just two to start: **`ANTHROPIC_KEY`** and **`SECRET_PERSONAL`**.
Skip `SECRET_WORK` / `SECRET_OP` / `SECRET_VA` / `SECRET_OFFICE` for now — add those when you bring in the work phone and team.

## Test it
```bash
export AIXMOS_GATEWAY="https://your-url.workers.dev"   # paste your URL
export AIXMOS_SECRET="your-SECRET_PERSONAL-value"
bash aixmos.sh "AIXMOS online. Reply in one sentence."
```
Get a sentence back → you're live.

## Use it day to day
- **From any Mac/PC terminal:** `bash aixmos.sh "draft a follow-up to a Turo customer"`
- **From your iPhone:** build the shortcuts in `docs/AIXMOS_iPhone_System.md`, pointed at your Gateway URL.
- **Check spend anytime (admin):** open `https://your-url.workers.dev/usage` with your secret in the `x-aixmos-auth` header, or run `npm run tail` to watch live traffic.

## Safe by default
- Your API key lives only inside the Gateway, encrypted. It's never in these files or on a device.
- Spending is capped twice: per-role daily caps in the code, and the monthly cap you set in the AIXMOS console.
- To cut someone off later: `npx wrangler secret put SECRET_VA` with a new value (or delete it). That one role/person is gone; nobody else is affected.
- Nothing here stores a secret on disk; `.gitignore` keeps local config out of any git repo.

## The bigger picture (when you're ready)
- `docs/AIXMOS_START_HERE.md` — the decided plan + step-by-step rollout for all your devices and team.
- `docs/AIXMOS_Mesh.md` — how the five devices + team fit together.
- `docs/AIXMOS_iPhone_System.md` — building the Siri shortcuts.

## If something hiccups
- **`wrangler: command not found`** → it runs via `npx`, so just re-run `bash deploy.sh`. If npx prompts to install, say yes.
- **Login issue** → run `npx wrangler login` manually, then re-run the script.
- **KV creation errors (older tool)** → run `npx wrangler kv:namespace create AIXMOS_KV`, copy the 32-character id into `wrangler.toml` (replace `PASTE_KV_ID`), then `npx wrangler deploy`.
- **Watch live logs** → `npm run tail`
