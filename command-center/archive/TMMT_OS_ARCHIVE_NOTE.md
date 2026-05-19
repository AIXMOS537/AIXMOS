# Archived: TMMT OS prototype

**Removed:** 2026-05-19

TMMT OS was an early Next.js 14 prototype (internal / investor / vendor portals
plus a case/job workflow engine). It lived at
`AIX_AI_COMMAND_SYSTEM/integrations/tmmt-os/` along with a `TMMT_OS.md` doc.

It has been **superseded by TMMT Rentals** — the production Next.js 16 app in
the private repo `AIXMOS537/TMMT`, which has the full admin suite, customer
intake forms, partner portal, and tests.

Only one app is maintained and deployed: **TMMT Rentals**. The TMMT OS prototype
and its doc were deleted from this repo to remove the duplicate. Recover the old
code from git history if ever needed:

```bash
git log --all --diff-filter=D -- "AIX_AI_COMMAND_SYSTEM/integrations/tmmt-os/*"
```
