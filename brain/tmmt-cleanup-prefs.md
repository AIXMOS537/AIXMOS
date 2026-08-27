---
name: tmmt-cleanup-prefs
description: "How Muhammad Taha wants file cleanup done — reversible quarantine, never delete secrets"
metadata: 
  node_type: memory
  type: feedback
  originSessionId: 3a3a0781-3aa1-46e6-92ba-0b68c9e50c94
---

When cleaning up Muhammad Taha's files, **default to reversible "quarantine"** rather than permanent deletion: move removed items into a dated `_QUARANTINE-YYYY-MM-DD\` folder on the same drive so nothing is lost.

**Why:** His machine is full of many overlapping AI-generated setup attempts; it's easy to mistake something important for clutter. He explicitly asked to clean up "without deleting important things."

**How to apply:** Never touch `05_SECRETS_AND_KEYS`, `.env*` files, `TMMT-SECRETS.enc`, or the local `C:\Users\AIXMOS\TMMT` repo. macOS junk (`._*`, `.DS_Store`, `.Spotlight-V100`) on his Windows drives is safe to delete outright. Tell him he can reclaim space by deleting the quarantine folders + `99_ARCHIVE` once he's verified nothing's missing. Note `TMMT-SETUP\` on the drives is an intentional team kit, not clutter. See [[tablet-desktop-setup]] and [[team-drive-kit]].
