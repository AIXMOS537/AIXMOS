# AIXMOS Road Warrior — Do Business Anywhere, Even Offline

Your setup: **this M1 Max = always-on command hub at home.** Your **carry Mac + 8GB Windows AMD =
roaming battle stations.** This is how they stay armed with little-to-no internet.

## The "never goes dark" brain
Every AIXMOS call on a carry device tries, in order, and uses the first that answers:
1. ☁️ **Cloud Gateway** — best models, needs internet (+ funded premium)
2. 🏠 **Home brain PC** (Ollama over Tailscale) — free, needs internet to home
3. 💻 **LOCAL model on the device** — **works with ZERO internet** (your offline brain)

So: full signal → cloud. Weak/home-only → your brain PC. **No signal → the local model on the laptop.** You're never without AIXMOS.

| Device | Local offline model | Notes |
|---|---|---|
| 8GB Windows AMD | `llama3.2:3b` (~2GB) | small but real; drafting, summaries, ops Q&A offline |
| Carry Mac (M-series) | `llama3.1:8b` or bigger | can run heavier models locally |

## Setup (once per device)
**Windows AMD:** run `bootstrap-windows.ps1` (installs Tailscale + Ollama + small model + client + env). Then `tailscale up`, and `.\aixmos.ps1 "test"`.
**Carry Mac:** `bash bootstrap-mac.sh` (Tailscale + Ollama + model + `aixmos-anywhere.sh`).

## What works OFFLINE vs ONLINE
| Task | Offline? | How |
|---|---|---|
| AI drafting / summaries / ops help | ✅ yes | local model |
| Your SOPs / playbooks / pricing | ✅ yes | keep `TMMT_Knowledge_Base` synced to the device |
| Passwords / keys | ✅ yes | **1Password caches your vault locally** (works offline) |
| TMMT OS, Supabase, GHL, Airtable, email | ❌ online | cloud apps — open when you have signal |
| Premium Claude (Sonnet/Opus) | ❌ online | via the gateway |
| Reach home hub / brain PC | ❌ online | Tailscale |

**Offline workflow:** draft with the local model + your local SOPs → it queues → when signal returns, push to the cloud apps / sync to NAS + GitHub.

## 🔒 Security — the device you carry is the one you'll lose
The LEXAR taught us. Lock the carry devices down:
1. **Disk encryption ON** — BitLocker (Windows) / FileVault (Mac). A lost laptop's disk = useless gibberish.
2. **No bulk secrets on the device.** Only the **CARRY gateway secret** (bounded: sonnet ceiling, 1500 tokens/mo, non-admin) + your **1Password** (its own master password/biometric). Never the admin/personal gateway secret.
3. **Tailscale, not open ports.** The brain PC is reachable only over your private tailnet (and locked to it by firewall — already done).
4. **Auto-lock + strong login** on both devices; biometric where possible.

## 🚨 LOST / STOLEN CARRY DEVICE — do this immediately
1. **Revoke the carry key:** on a trusted machine → `cd ~/dev/aixmos-gateway && npx wrangler secret delete SECRET_CARRY` (kills that device's gateway access only; your admin access untouched).
2. **Remove it from Tailscale:** admin console (AIXMOS537@) → delete the device → it can no longer reach the brain.
3. **1Password:** sign that device out of your account (1Password.com → Devices).
4. Disk encryption already means the local files/model are unreadable to a thief.
Result: a lost laptop is an inconvenience, not a breach.

## The hub must stay alive (home M1 Max)
- Plugged into **AC power** (a hub on battery dies).
- `sudo pmset -a sleep 0 disksleep 0 standby 0 womp 1 autorestart 1` — never sleeps, wakes on network, auto-restarts after outage.
- Already running: SSH, Tailscale, Ollama, TMMT OS, + 11 auto-start services.
