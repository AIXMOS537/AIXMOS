# AIXMOS — START HERE
**The decided plan + how to stand it up safely.** This is the front door.
Depth lives in two companion files: `AIXMOS_Mesh.md` (architecture + Gateway code) and `AIXMOS_iPhone_System.md` (shortcut build steps). Read those when a step points you to them.

---

## PART A — DECISIONS (locked recommendations)
Every choice that was open is now decided. Rationale in one line each.

| # | Decision | Why it's best & safe | Cost |
|---|---|---|---|
| 1 | **Separate Apple IDs:** personal ID (personal iPhone + carry Mac); new **TMMT business ID** (work iPhone + work Mac) | Clean personal/business split, business continuity if a device is reassigned, scales to staff | $0 |
| 2 | **Gateway is the unifier, not iCloud.** Cross-phone parity via the shared brain + iCloud share-links for shortcuts + `/AIXMOS` backups | iCloud only syncs within one Apple ID; the Gateway makes AIXMOS identical across IDs and the PC | $0 |
| 3 | **Routing:** free on-device first → Haiku → Sonnet → Opus (you only) → AIXMOS Engine for heavy work | Keeps the only metered cost tiny; on-device is free, private, offline | metered, small |
| 4 | **One secret per *person*** (not just per role), all held in the Gateway | Individual revocation + accountability; revoke = rotate that one person's secret | $0 |
| 5 | **No secret on a shared disk.** Team uses their own device + personal secret; a true shared kiosk gets a Gateway-served session page | A plaintext secret on a shared office machine is the single biggest leak risk — this removes it | $0 |
| 6 | **Airtable stays** the system of record, role-scoped views; D1 is the free escape hatch if you pass the free record ceiling | You're already built on it; D1 keeps the exit free | $0 |
| 7 | **Pay ~$1/mo for iCloud 50 GB.** Keep `/AIXMOS` text/docs only | A dollar beats fighting the 5 GB wall; trivial for the reliability | ~$1/mo |
| 8 | **Business line: start free (Google Voice), upgrade to a paid VoIP once customer calls justify it** | Free to launch; a customer-facing rental op eventually wants a ToS-clean, reliable business line | $0 → ~$15/mo |
| 9 | **Set the AIXMOS spend cap + alert BEFORE going multi-device** | Hard money backstop; per-role daily caps already enforce the rest | $0 |
| 10 | **Manual config now; Apple Business Manager + light MDM only past ~5 operators** | Don't pay for or manage MDM you don't need yet | $0 now |
| 11 | **Every shortcut uses try-Gateway-then-on-device fallback** | AIXMOS never goes dark — offline or API outage still answers locally | $0 |

**Per-person secret pattern** (extends the Gateway `ROLES` map — add one line per teammate, revoke by deleting their secret):
```js
const VA_PERSONA = "Assist a TMMT VA: drafting, summaries, data entry. No payroll, mass-send, or financials.";
const OP_PERSONA = "Assist a TMMT field operator: check-in/out, condition reports. No financials, CRM, or mass-send.";
// ...add per person:
[env.SECRET_VA_AISHA]:  { role:"va",       tier:"sonnet", admin:false, cap:200, persona: VA_PERSONA },
[env.SECRET_OP_MARCUS]: { role:"operator", tier:"haiku",  admin:false, cap:150, persona: OP_PERSONA },
```

---

## PART B — DEPLOYMENT RUNBOOK (do in order; verify before advancing)

### Phase 1 — Foundation 🔑 *(Owner: you)*
- **Do:** Create the TMMT business Apple ID. Deploy the Gateway (code in `AIXMOS_Mesh.md`); set `ANTHROPIC_KEY` + per-person secrets; add the `AIXMOS_KV` binding. Set the AIXMOS monthly spend cap + usage alert.
- **Verify:** `bash aixmos.sh "ping"` returns text; open `GET /usage` with an admin secret → returns JSON.
- **Rollback:** Delete the Worker; no other system touched.

### Phase 2 — Your devices 🖥️ *(Owner: you)*
- **Do:** Sign personal iPhone + carry Mac into personal ID; work iPhone + work Mac into business ID. Turn **Shortcuts → iCloud Sync ON** on all four. Create `/AIXMOS` in iCloud Drive. Install **iCloud for Windows** on the Brainiac PC.
- **Verify:** Drop a file in `/AIXMOS` on a Mac → it appears in Explorer on the PC within a minute.
- **Rollback:** Sign out; remove iCloud for Windows. Local files remain.

### Phase 3 — The brain on every device 🧠 *(Owner: you; delegable for testing)*
- **Do:** Build `AIXMOS Brain` once per Apple ID using the **try-Gateway → fall back to on-device "Use Model"** pattern (steps in `AIXMOS_iPhone_System.md`). Share iCloud links to the matching devices; back up to `/AIXMOS/shortcut-backups/`.
- **Verify:** Run it online → AIXMOS answers. Turn on Airplane Mode → it still answers via on-device. (That single test proves coverage.)
- **Rollback:** Delete the shortcut; re-import from backup.

### Phase 4 — Work phone provisioning 📱 *(Owner: you)*
- **Do:** Add the business line (free Google Voice to start), create the "TMMT Ops" Focus, place NFC lot tags, build the Rental / Shift / GHL flows on the work phone.
- **Verify:** "Hey Siri, AIXMOS rental" → a test record lands in Airtable with the right fields.
- **Rollback:** Disable the automation; delete the test record.

### Phase 5 — Team onboarding 👥 *(Owner: you → then delegable)*
- **Do:** Add a per-person secret for each operator/VA (Part A pattern). Create role-scoped Airtable views. Hand each person their secret + the Rental Ops Hub link. Team works from their **own** device — no secret on shared disks.
- **Verify:** A VA secret can draft a summary; the same secret is **refused** an admin action (you should get the 401/scope block); `GET /usage` shows their calls.
- **Rollback:** Rotate/delete that person's secret in Cloudflare → instant cutoff, nobody else affected. Remove them as your AIXMOS systemrtable collaborator.

### Phase 6 — Always-on node ⚙️ *(Owner: you)*
- **Do:** Windows **Task Scheduler** runs an overnight job that pulls next-day rentals from Airtable, sends them to the Gateway for a risk summary, and writes `/AIXMOS/ops-brief.md`. A work-phone shortcut reads and speaks it each morning.
- **Verify:** `ops-brief.md` is freshly dated each morning and the phone reads it.
- **Rollback:** Disable the scheduled task.

---

## PART C — SECURITY REVIEW (what's safe, and the risks already handled)
- **Keys never on a device** — they live as encrypted Gateway secrets. Rotating one re-keys everyone on that role at once.
- **Biggest risk = shared-disk secret → eliminated** by Decision 5 (per-person secrets on personal devices; kiosk gets a server-side page).
- **Least privilege, enforced server-side** — a teammate's persona/scope/model is set by the Gateway; the client can't override it. A VA cannot perform admin actions or read your private context (team KV is namespaced).
- **Spend can't run away** — per-role daily caps in code + a hard monthly cap in the console.
- **Individual accountability** — per-person secrets + `GET /usage` show who's calling and how much.
- **No single point of darkness** — on-device fallback keeps AIXMOS working if the network or API is down.
- **Clean offboarding** — delete one secret + remove one Airtable collaborator. Done.

---

## WHAT'S DECIDED vs WHAT NEEDS YOUR HANDS
- **Decided & built (here + the two companion docs):** the architecture, the Gateway with cost/role/scope/usage controls, all six iPhone flows, the PC bridge, the team model, the routing policy, and this runbook.
- **Only you can do (account-bound):** deploy the Worker, create the Apple IDs, provision devices and the business line, and hand out team secrets. None of it needs further design.

> Want me to build the **Gateway-served kiosk page** (Decision 5, for a shared office workstation with no stored secret) or the **scoped VA / operator shortcuts** next? Both are ready to write against this Gateway — just say which.
