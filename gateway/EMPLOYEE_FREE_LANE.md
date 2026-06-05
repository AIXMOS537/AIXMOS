# Employee Free Lane (Tailscale → your brain PC) + Lock-Down

Most employees use AIXMOS **for free**, running on your own brain PC (`brainiac-7`) over your
private Tailscale network. It **never touches the public internet**, so there's nothing exposed.

## How an employee gets on it (one-time, ~5 min)
1. **Install Tailscale** on their device and sign in to the **TMMT tailnet** (you invite them — see ACL below).
2. Confirm they can see the brain PC: it's `brainiac-7` at `100.64.0.1`.
3. On a Mac/PC, set two lines (add to `~/.zshrc` / `~/.bashrc`):
   ```bash
   export AIXMOS_OLLAMA="http://100.64.0.1:11434"
   export AIXMOS_MODEL="tmmt-brain:latest"   # or llama3.1:8b
   ```
4. Use it: `bash aixmos-free.sh "draft a check-in message for a Turo guest"`
   (iPhone: a Shortcut that POSTs to `http://100.64.0.1:11434/api/chat` over Tailscale.)

Available models on the brain PC: `tmmt-brain`, `cyborg`, `tmmt-ops`, `llama3.1:8b`, `llama3.2:3b`, `qwen2.5-coder` variants.

## Who uses what (the full picture)
| People | Lane | How |
|---|---|---|
| Most employees | 🆓 free | `aixmos-free.sh` → Tailscale → brain PC. $0, private. |
| You + premium few | 💎 cloud | `aixmos.sh` → Gateway (their secret). Credit-metered. |

Premium folks can use **both**: free for routine stuff, gateway when they need cloud quality.

---

## 🔒 LOCK-DOWN CHECKLIST (do these to keep the brain private)
Ollama has **no built-in password** — so access = being on your tailnet. Lock that down:

1. **Restrict the tailnet with an ACL** so only specific devices can reach the brain's port.
   In the Tailscale admin console (AIXMOS537@ tailnet) → Access Controls, add:
   ```jsonc
   // tag the brain PC, and only allow tagged employee devices to reach Ollama
   "tagOwners": { "tag:brain": ["AIXMOS537@..."], "tag:staff": ["AIXMOS537@..."] },
   "acls": [
     { "action": "accept", "src": ["tag:staff","AIXMOS537@..."], "dst": ["tag:brain:11434"] },
     // deny everything else to the brain by not granting it
   ]
   ```
   Tag `brainiac-7` as `tag:brain`; tag employee devices `tag:staff`. Now only staff devices hit `:11434`.
2. **Bind Ollama to Tailscale only (not the LAN/public).** On the brain PC, ensure Ollama isn't
   reachable on its regular LAN IP — set `OLLAMA_HOST` to the Tailscale IP, or add a Windows
   Firewall rule allowing TCP 11434 **only on the Tailscale interface**. (I can SSH in and set this.)
3. **Off-board instantly:** remove a person's device from the tailnet → free-lane access gone.
   Revoke a premium person → delete their Gateway secret. Two clean levers.
4. **MFA on the Tailscale account** (AIXMOS537@) — it's now the key to your free brain.
