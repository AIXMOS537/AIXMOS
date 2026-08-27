# 🔗 Brain Sync Status

**Hub:** UGREEN NAS → `\\192.168.1.236\personal_folder\AIXMOS\AIXMOS-Brain` (drive `N:` when mounted)
**Model:** each device keeps a LOCAL working brain (offline-safe); `git push nas` / `git pull nas` syncs through the NAS master copy, which is also a readable Obsidian vault and auto-backed to OneDrive/Google Drive.

## Devices
- ✅ **Tablet** (Surface, `AIXMOS`) — local: `C:\Users\AIXMOS\AIXMOS-Brain`, remote `nas` wired 2026-06-06.
- ⏳ **Brainiac** (`BRAINIAC-7`) — to clone from the NAS.
- ⏳ **Carry Mac / Work Mac** — to clone from the NAS.

## How to sync (Claude does this for you)
- Save your work: `git -C <brain> add -A && git -C <brain> commit -m "..." && git -C <brain> push nas main`
- Get latest on another device: `git -C <brain> pull nas main`

See [[ugreen-nas]] · [[operator-os]].
