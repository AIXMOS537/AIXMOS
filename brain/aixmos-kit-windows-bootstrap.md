---
name: aixmos-kit-windows-bootstrap
description: Windows local bootstrap + encrypted API-key wiring authored for the AIXMOS/PROJECT X HAILMARY kit on the command-hub tablet
metadata: 
  node_type: memory
  type: project
  originSessionId: fa64a7db-9a61-4999-8854-1c74b83dbde4
  modified: 2026-08-20T18:33:37.721Z
---

The AIXMOS/PROJECT X HAILMARY operator kit (AIXMOS02, a Mac-provisioned mirror of CYBORG) was set up to run **locally on Windows** from `C:\Users\AIXMOS\Desktop\New folder`. Done 2026-08-20 on the command-hub tablet (DESKTOP-1IT6EL5, role=`office`).

**Why it needed work:** the kit's clean `_PAYLOAD/00-BOOTSTRAP` has only macOS `.sh` scripts — no Windows bootstrap — so `START-HERE.bat` did nothing. All Windows automation was scattered in `_PAYLOAD/99-LEGACY`.

**What was built (all safe/reversible, in `_PAYLOAD\00-BOOTSTRAP\`):**
- `bootstrap.bat` + `bootstrap-local.ps1` — the missing Windows bootstrap `START-HERE.bat` calls. Records machine role → `%USERPROFILE%\.config\tmmt\machine.json`, makes config + `_RUNTIME\logs`, health-checks tooling (node/npm/python/git/tailscale all present). Deliberately does NOT: register autostart/scheduled tasks, join mesh, harden system, touch vault, or send anything.
- **API key wiring** (no more pasting): `set-anthropic-key.ps1` (user runs once, hidden prompt) stores the Anthropic key **DPAPI-encrypted** at `%USERPROFILE%\.config\tmmt\anthropic.key` (never plaintext, this-user+machine only). `load-anthropic-key.ps1` decrypts into the session. `RUN-CHUMMO.bat` / `RUN-MOOSE.bat` at kit root auto-load the key then launch the node agents. Round-trip tested.

**Held for explicit approval only (never auto-run):** autostart/scheduled-task installers, `set-machine-role` mesh join, `harden-command-center`, vault (UNLOCK/keys/passwords), autopilot/collections sends.

**Cleanup:** the redundant 738 MB nested copy (`PERSONAL\Desktop\New folder`) and the `_PAYLOAD\99-LEGACY` tree (1,088 MB / 7,566 files) were quarantined then, on the user's explicit instruction, **permanently deleted** (`C:\Users\AIXMOS\Desktop\_QUARANTINE\` removed 2026-08-20, ~1.8 GB reclaimed). Before deleting, verified the quarantined `_VAULT\TMMT-SECRETS.enc` was byte-identical (SHA-256) to the live kit's copy, so no unique secret was lost. Kit slimmed from ~2.8 GB to ~967 MB; clean 00-06 payload + brain/work/personal lanes + live `_VAULT` intact.

Follows the reversible-quarantine rule [[tmmt-cleanup-prefs]]. Related: [[go-kit]], [[worksync-usb]], [[operator-os]], [[tablet-desktop-setup]], [[free-ram-atboot]], [[local-ai-ollama]].
