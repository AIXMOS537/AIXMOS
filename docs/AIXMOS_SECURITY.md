# AIXMOS security

What protects the owner today, and what is still open. Paired with [AIXMOS_PERMISSIONS.md](AIXMOS_PERMISSIONS.md).

## In place

| Threat | Control |
|---|---|
| A web page driving the local API | Server binds 127.0.0.1; `_guard` pins Host (DNS rebinding) and refuses cross-origin / cross-site requests (CSRF). |
| A script or agent tool approving its own work | Owner actions need the per-launch app token. `POST /api/email/send` without it only queues the email. |
| Instructions hidden in web pages, CRM records or mail | Output from those tools is wrapped as untrusted; after reading it, risky writes need a yes for that exact call; emails written afterwards are flagged in the inbox. |
| The agent sending on its own | `send_email` only queues. Nothing reaches a customer without the inbox (or an autopilot the owner switched on for that skill). |
| Runaway spending | Daily budget for automatic paid calls (media, paid search, cloud models). |
| Messaging people who opted out | Guard checks every recipient (to, cc, bcc) at send time, after approval too. |
| Keys on disk | OS keystore (DPAPI / Keychain / 0600 file). The browser only sees `....last4`. Audit arguments mask key-like names. |
| Coding agents inheriting the host's AI sessions | Claude Code / Codex run with an environment stripped of `CLAUDE*`, `ANTHROPIC*`, `OPENAI*`, `CODEX*`, and Claude Code with project settings only, strict MCP config, no session persistence, edit tools only. |
| Cloud models seeing private notes | Cloud is off by default; PRIVATE-LOCAL blocks it entirely; LOCAL_ONLY memory never goes to cloud. |
| Licence tampering | ed25519 signatures verified offline (pure-Python fallback when `cryptography` is missing). Signing key never in the repo. |

## Known gaps (tracked)

1. **Same-user local processes.** Anything running as the owner's Windows user can read the app page and its
   token, or the memory folder directly. The token stops agent tools and scripts that are not looking for it; it is
   not a boundary against malware already running as the owner.
2. **`--allow-shell`.** With shell enabled, commands can read outside the allowed roots (measured on 2.1.x). Shell
   stays off for clients; code tools ask once per run.
3. **Public image service.** Pollinations is on by default so images work without a key (owner decision
   2026-09-12). Prompts go to a public service. The audit recommends turning it off by default: owner decision.
4. **History.** Earlier customer data was removed from current code (`0402cf3`) but remains in git history. A history
   rewrite is an owner decision.
5. **Tenant separation.** One install = one business today.
