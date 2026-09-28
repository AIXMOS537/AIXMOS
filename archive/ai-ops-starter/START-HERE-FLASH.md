# START HERE — Flash Drive Install

This USB contains the full **AI-OPS-STARTER** kit for **Brainiac 7** and HQ operators.

---

## Muhammad Taha — Phase 1 (Brainiac 7, home PC)

1. Copy folder to `C:\AI-OPS-STARTER`
2. Open PowerShell:

```powershell
cd C:\AI-OPS-STARTER
.\scripts\phase1-windows-bootstrap.ps1
.\scripts\init-nas-layout.ps1
.\scripts\sync-registry-nas.ps1
```

3. Read **`docs\DEPLOY-ORDER.md`** for phases 2–5 + Superman/Superwoman

---

## Other operators (Dominique, Michael, Dyson, Nathan, Claryn, …)

1. Copy same folder to your PC → `C:\AI-OPS-STARTER`
2. Open **`docs\install-guides\INSTALL-<yourname>.md`** (or **`docs\TEAM-SELF-INSTALL.md`**)
3. Run **your** one-click installer:

```powershell
cd C:\AI-OPS-STARTER
.\scripts\installers\install-dominique.ps1
# Examples: install-michael.ps1, install-claryn.ps1, install-nathan.ps1
# Optional prereqs: add -InstallPrerequisites
```

Legacy manual path: **`docs\DEPLOY-ORDER.md`** → provision command → `.\install-windows.ps1`

**Claryn = Ryn = Mystique** (Phase 4, Counsel lane)

**Kayleigh** — do not install until hired (Phase 5)

---

## On this flash drive you have

| Item | Path |
|------|------|
| **Deploy order (canonical)** | `docs\DEPLOY-ORDER.md` |
| Team roster | `docs\team-roster.md` |
| Operator registry | `setup\operators\registry.yaml` |
| Brainiac 7 guide | `docs\brainiac-7.md` |
| Hierarchy | `docs\brainiac-hierarchy.md` |
| Executives (Oracle, Operator, Counsel) | `agents\` |
| Windows install | `install-windows.ps1` |
| **Your installer** | `scripts\installers\install-*.ps1` |
| Team self-install | `docs\TEAM-SELF-INSTALL.md` |
| Release zip (backup) | `..\AI-OPS-RELEASES\` on this USB |

---

## Offline git history

This USB includes **`.git`** — run `git log` on the stick without internet. See `docs\offline-git-history.md`.

## Do NOT put secrets on the stick

- **`.env`** — create on each PC from `.env.example` only
- **`data\`** — runtime cache (rebuilt per machine)

---

## MacBook (admin)

`setup\mac\MACBOOK-SETUP.md` — M1 control machine, flash sync, remote Brainiac 7.

---

## Phone — speak tasks & draft replies

With Tailscale on your phone:

- **Voice → tasks:** `docs\mobile-voice-command-center.md`
- **Messages → Counsel drafts:** `docs\auto-response-playbook.md`
- **iPhone (start here):** `setup\phone\IPHONE-SETUP.md`

Default: **you approve** before tasks go out or messages send.

---

## Verify flash (Mac admin)

```bash
./scripts/verify-flash-drive.sh /Volumes/AI-OPS/AI-OPS-STARTER
```
