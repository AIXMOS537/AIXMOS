# Node report: BRAINIAC-7

Bootstrapped 2026-09-26 (PVIRALSCRIPT flagship bootstrap).

| field | value |
|---|---|
| hostname | BRAINIAC-7 |
| role | HUB-WIN (headless GPU worker; control plane stays rickd on the M1) |
| tier | 30.9 GB RAM, RX 9070 XT |
| Ollama model | qwen3:14b (owner pick; already installed, no pull) |
| Ollama binding | `::` all interfaces (pre-existing, left as is; M1 reaches it over the tailnet) |
| assistant reachable | yes, http://127.0.0.1:8770 (v2.0.0, %LOCALAPPDATA%\AIXMOS, chat_model=qwen3:14b) |
| packs count | 26 (the 5 Unified Team packs are missing) |
| active skill | none (team-os does not exist on this install) |
| MCP wired | yes, `aixmos` user scope, connected |
| profile synced | no |
| loop installed | no (owner: skip on BRAINIAC) |
| autostart | no (`--no-autostart`; start with `Start AIXMOS.cmd`) |
| git branch | ops/BRAINIAC-7 |

## What could not be done and why

1. **The vault layout is not on GitHub.** `AIXMOS537/aixmos-brain` main (2ec804f) has no `CLAUDE.md`,
   `vault/VAULT-MAP.md`, `vault/UNIFIED-TEAM.md`, `vault/kit/`, `vault/claude-skills/`, `vault/bin/`
   or `vault/profile/`. main is the only branch. That blocks:
   - step 2 project skills copy (viral-shorts-day, lead-intake-router, weekly-ops-review)
   - step 4 pack sync (`aixmos-sync.ps1`) and activating `team-os`
   - step 6 profile import (`vault/profile/business.json`)
   - step 7 the TASKS / LOCKS / HANDOFFS registry
   Fix: push the vault from the machine that has it (probably the Surface), then re-run steps 2 and 4 to 6 here.
2. **Installer role came out `aixmos_member`, not `everything`.** `--role` did not reach installer.py
   through the Setup.exe stub. No effect here, because the dev lane and shortcuts were off anyway.
3. The Setup.exe has no Authenticode signature. Its SHA256 matched `SHA256SUMS.txt` (c8986ecc...3b55).
