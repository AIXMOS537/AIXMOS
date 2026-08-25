# AIXMOS Mesh — Personal + Work + Team (Low-Cost Build)
**Your devices:** Personal iPhone · Work iPhone · Carry Mac · Work Mac · Home Windows (Brainiac PC)
**Your team:** Operators (in-person) · Virtual Assistants (remote) · Office computers (shared)
**Principle:** one brain, scoped access, two rings — and the brain is also your single point of cost control and governance.

---

## THE TOPOLOGY (two rings, one hub)
```
                    ┌──────────────────────────────────┐
                    │   AIXMOS GATEWAY (Cloudflare, FREE)│
                    │   • holds API keys server-side     │  the hub everyone meets at
                    │   • ROLE BROKER: secret→persona    │  enforces who can do what
                    │   • TIERS + daily caps + usage log │  enforces what it costs
                    │   • KV memory (namespaced by role) │
                    └──────────────────┬─────────────────┘
            ┌──────────────────────────┴──────────────────────────┐
      RING 1: YOU (full access)                     RING 2: TEAM (scoped, revocable)
   Personal iPhone · Work iPhone                 Operators · VAs · Office computers
   Carry Mac · Work Mac · Brainiac PC            (no keys, no access to your devices)
            └──── iCloud glues YOUR Apple devices ────┘
                    Shared state: Airtable (role views) + iCloud Drive /AIXMOS + Gateway KV
```

---

## THE GATEWAY — role broker + cost control (the production version)
Each person/role has their own secret → persona, model tier, daily cap, and scope, all enforced server-side. This is also where you control spend and revoke access.
```js
const TIERS = {
  haiku:  "claude-haiku-4-5-20251001",  // cheapest — default for team & high-frequency jobs
  sonnet: "claude-sonnet-4-6",          // balanced — drafting
  opus:   "claude-opus-4-8",            // premium — your strategic work only
};

export default {
  async fetch(req, env) {
    const url = new URL(req.url);
    const auth = req.headers.get("x-aixmos-auth");

    // Each secret = its own Cloudflare Secret = individually revocable.
    const ROLES = {
      [env.SECRET_PERSONAL]: { role:"personal", tier:"sonnet", admin:true,  cap:200,
        persona:"AIXMOS for Muhammad's personal life. Decisive, brief, proactive." },
      [env.SECRET_WORK]:     { role:"work",     tier:"sonnet", admin:true,  cap:300,
        persona:"AIXMOS for Muhammad as CEO of TMMT. Systems-oriented, ops-aware, brief." },
      [env.SECRET_OP]:       { role:"operator", tier:"haiku",  admin:false, cap:150,
        persona:"Assist a TMMT field operator: check-in/out, condition reports. No financials, CRM, or mass-send." },
      [env.SECRET_VA]:       { role:"va",       tier:"sonnet", admin:false, cap:200,
        persona:"Assist a TMMT VA: drafting, summaries, data entry. No payroll, mass-send, or financials." },
      [env.SECRET_OFFICE]:   { role:"office",   tier:"haiku",  admin:false, cap:100,
        persona:"AIXMOS on a shared TMMT office workstation. General ops only. No admin actions." },
    };
    const ctx = auth ? ROLES[auth] : null;
    if (!ctx) return new Response("Unauthorized", { status: 401 });

    // CONTROL: admin usage readout — GET /usage shows today's calls per role.
    if (url.pathname === "/usage" && ctx.admin && req.method === "GET") {
      const day = new Date().toISOString().slice(0,10), out = {};
      for (const r of ["personal","work","operator","va","office"])
        out[r] = parseInt(await env.AIXMOS_KV.get(`usage:${r}:${day}`) || "0", 10);
      return Response.json({ day, usage: out });
    }

    // Shared memory, namespaced so team roles can't read your private context.
    if (url.pathname === "/mem") {
      const scope = ctx.admin ? "" : ctx.role + ":";
      if (req.method === "GET") {
        const k = scope + url.searchParams.get("key");
        return Response.json({ key:k, value: await env.AIXMOS_KV.get(k) });
      }
      const { key, value } = await req.json();
      await env.AIXMOS_KV.put(scope + key, value);
      return Response.json({ ok:true });
    }

    // BRAIN
    if (req.method === "POST") {
      // COST/RUNAWAY CONTROL: per-role daily cap (approximate; free KV; auto-expires).
      const day = new Date().toISOString().slice(0,10);
      const ukey = `usage:${ctx.role}:${day}`;
      const used = parseInt(await env.AIXMOS_KV.get(ukey) || "0", 10);
      if (used >= ctx.cap)
        return Response.json({ error:`Daily AIXMOS limit reached for ${ctx.role}` }, { status:429 });
      await env.AIXMOS_KV.put(ukey, String(used + 1), { expirationTtl: 172800 });

      const incoming = await req.json();
      // Admins may bump tier (e.g. opus for the brief); team is locked to its role tier.
      const tier = (ctx.admin && incoming.tier && TIERS[incoming.tier]) ? incoming.tier : ctx.tier;
      const payload = {
        model: TIERS[tier],
        max_tokens: Math.min(incoming.max_tokens || 1024, 2048),
        system: ctx.persona,
        messages: incoming.messages || [{ role:"user", content: incoming.prompt || "" }],
      };
      const r = await fetch("https://api.anthropic.com/v1/messages", {
        method:"POST",
        headers:{ "x-api-key":env.ANTHROPIC_KEY, "anthropic-version":"2023-06-01", "content-type":"application/json" },
        body: JSON.stringify(payload),
      });
      return new Response(await r.text(), { status:r.status, headers:{ "content-type":"application/json" } });
    }
    return new Response("Not found", { status:404 });
  },
};
```
Set six **Secrets** (`ANTHROPIC_KEY` + the five role secrets), add the `AIXMOS_KV` binding. Clients send only `{prompt}` or `{messages}` (admins may add `"tier":"opus"`).

---

## RING 1 — YOUR DEVICES
### Two-iPhone model (personal vs work)
| | Personal iPhone | Work iPhone (new) |
|---|---|---|
| Identity | Personal Apple ID | Dedicated TMMT business Apple ID |
| Secret | `SECRET_PERSONAL` | `SECRET_WORK` |
| Persona | Personal-life assistant | TMMT CEO / ops assistant |
| Runs | Brief, Capture, life logistics | Rental, Shift, GHL, Slack, NFC lot tags |
| Line | Personal number | Business line (see Cost — free option exists) |
| Syncs with | Carry Mac | Work Mac |

Separate Apple IDs = clean personal/business split + scales to the team; you lose free shortcut-sync *between the two phones* (bridge via Gateway = same brain, + iCloud share-links + `/AIXMOS/shortcut-backups/`). One Apple ID on both is simpler but mixes data — separate is recommended with staff in the picture.

### Roles
Brainiac PC = always-on 24/7 node · Work Mac = TMMT cockpit + AIXMOS Engine · Carry Mac = mobile cockpit · phones as above.

---

## RING 2 — YOUR TEAM (scoped, revocable, no keys)
| Role | Device | Secret | Can do | Cannot do |
|---|---|---|---|---|
| Operator | Shared office iPhone/iPad or PC | `SECRET_OP` | Check-in/out, condition reports, log to Airtable | Financials, CRM, mass-send |
| VA | Own/office machine, via web | `SECRET_VA` | Draft, summarize, data entry | Payroll, mass-send, financials |
| Office computer | Shared workstation | `SECRET_OFFICE` | General ops help | Any admin action |
Connect: a web page or shortcut POSTs `{prompt}` + their role secret to the Gateway. Revoke anyone = rotate that one secret.

---

## SHARED STATE
Airtable (role-scoped views; system of record) · iCloud Drive `/AIXMOS` (your docs + backups; PC via iCloud for Windows; team does NOT get this) · Gateway KV (working context, team-namespaced).

---

## PC + OFFICE BRIDGE
iCloud for Windows → `/AIXMOS` in Explorer. `aixmos.sh` (PC uses `SECRET_WORK`, office uses `SECRET_OFFICE`):
```bash
#!/usr/bin/env bash
GATEWAY="https://YOUR.workers.dev"; SECRET="ROLE_SECRET_HERE"
curl -s -X POST "$GATEWAY" -H "x-aixmos-auth: $SECRET" -H "content-type: application/json" \
  -d "$(jq -n --arg p "$*" '{messages:[{role:"user",content:$p}]}')" | jq -r '.content[0].text'
```
Task Scheduler runs overnight jobs → writes `/AIXMOS/ops-brief.md` → work iPhone reads it at dawn.

---

## 💵 COST — making it majority free
| Component | Plan | Cost | Lever to stay cheap |
|---|---|---|---|
| Cloudflare Worker + KV (Gateway) | Free tier | **$0** | Generous free daily limits cover you + a small team |
| `workers.dev` URL | Free | **$0** | No custom domain needed |
| Apple Intelligence "Use Model" (on-device) | Built in | **$0** | **Do simple/local jobs here, not on the API** |
| AIXMOS Engine (PC/Mac heavy agentic work) | Your existing subscription | **included** | Use for long multi-step work instead of metered API |
| AIXMOS API (Gateway → AIXMOS) | Pay-as-you-go | **the only real variable** | Haiku default, Opus rarely, caps + spend limit |
| Airtable | Free tier (~1,000 records/base) | **$0** until you outgrow it | If records balloon, Cloudflare D1 (free) can replace it |
| iCloud Drive | 5 GB free / ~$1–3 mo for headroom | **~$0–3/mo** | Keep `/AIXMOS` to text + docs to stay in free tier |
| iCloud for Windows | Free | **$0** | — |
| Business phone line | Google Voice (free, US) → paid VoIP | **$0–~$15/mo** | Free Voice number keeps it $0; check ToS for business use |
| PC→phone push (optional) | ntfy (open-source) | **$0** | Free public server or self-host |
| Apple Business Manager (if you scale) | Free | **$0** | Add light MDM only past a handful of operators |

**The routing policy that makes it cheap (use in every shortcut/script):**
1. **Tier 0 — FREE, on-device (Apple Intelligence "Use Model"):** summarize, rewrite, proofread, classify, extract-to-JSON, short drafts. No Gateway call. Works offline.
2. **Tier 1 — Haiku (Gateway):** lightweight jobs needing AIXMOS (ops classification, structured extraction the on-device model fumbles, all team calls).
3. **Tier 2 — Sonnet (Gateway):** real drafting — VA comms, shift summaries.
4. **Tier 3 — Opus (Gateway, `"tier":"opus"`):** your morning brief and hard reasoning only. Low frequency.
5. **Heavy/agentic — AIXMOS Engine (subscription, not metered):** repo work, big multi-step automations on the PC/Mac.
**Backstop:** set a monthly **spend cap + usage alert** in the AIXMOS console. Even a leak or loop can't exceed it.

---

## 📡 COVERAGE — consistent + resilient
- **Global edge, free HA:** Cloudflare Workers run at the edge worldwide — high availability with no server to maintain.
- **Offline / outage coverage:** Apple's on-device model works with no network. Build your shortcuts to **try the Gateway, and on any error fall back to the on-device "Use Model" action** — AIXMOS still answers if you're offline or the API is down. You're never dead.
- **Consistent reach:** every device — your 5, plus team web — hits the *same* Gateway, so AIXMOS behaves identically everywhere.
- **Data coverage:** Airtable (cloud) is the source of truth; iCloud Drive syncs your files across all nodes; KV is edge-replicated. Lose a device and nothing is lost.

---

## 🎛️ CONTROL — one choke point governs everything
All AI traffic flows through the Gateway, so from one place you can:
- **Revoke** — rotate a role's secret; that person is cut off instantly, nobody else affected.
- **Throttle** — per-role daily caps are in the code; lower a cap to rein in spend.
- **Observe** — `GET /usage` (admin) shows each role's calls today; free **Cloudflare Analytics** shows request volume; AIXMOS console shows token spend.
- **Change behavior centrally** — edit a persona or tier once; every device on that role updates with no shortcut edits.
- **Hard money backstop** — AIXMOS monthly spend cap + alert.
- **Least privilege** — team personas are enforced server-side; a VA literally cannot perform admin actions or read your private context.

---

## SETUP ORDER
1. TMMT business Apple ID → work iPhone + work Mac. Personal devices stay on your personal ID.
2. Deploy the Gateway code above; set six secrets + `AIXMOS_KV`. Set the AIXMOS spend cap.
3. `/AIXMOS` in iCloud Drive (text/docs only to stay free); iCloud for Windows on the PC.
4. Build shortcuts once per Apple ID using the **try-Gateway-then-fall-back-to-on-device** pattern; share iCloud links; back up to `/AIXMOS`.
5. Work iPhone: business line (free Google Voice or paid), "TMMT Ops" Focus, NFC lot tags.
6. Scoped Airtable views per role; hand each team member their role secret + Hub link.
7. Office PCs: `aixmos.sh` with `SECRET_OFFICE`; per-user OS accounts.

---

## 💾 OWNED DATA TIER — THE NAS
Your NAS is private, high-capacity storage you already own. It becomes the **files layer behind Airtable's records** — and relieves the two free-tier ceilings (iCloud 5 GB, Airtable ~1k records) at $0 recurring.

**The clean data split:**
| Layer | Holds | Cost |
|---|---|---|
| Gateway (Cloudflare) | the brain | free |
| Airtable | structured records (who/what/when + a path pointer) | free tier |
| **NAS** | **the files those records point to: fleet condition photos, customer IDs/contracts/insurance, backups, overnight ops-briefs** | **$0 (owned)** |
| iCloud Drive | your personal working docs synced across Apple devices | ~$0–3/mo |

**What goes on the NAS:** `TMMT/Rentals/<customer>/in|out/` condition photos · customer docs (PII stays private, off third-party clouds) · backups of the master memory doc, shortcut exports, and periodic Airtable CSV exports · the overnight `ops-brief.md`.

**Mounting it:** iPhone/iPad → Files → Connect to Server → `smb://NAS-HOST`. Mac → Finder → Go → Connect to Server. Windows/PC → map a network drive. Once mounted, Shortcuts and `aixmos.sh` can read/write it.

**Make it a real mesh node — Tailscale (free):** today you reach the NAS only on home Wi-Fi, but the work phone lives at the lot. Install **Tailscale** (runs natively on Synology/QNAP) to put the NAS + all your devices on one private network reachable anywhere — **without exposing the NAS to the internet. Do not port-forward it.** That's the safe, recommended remote-access path.

**Optional — NAS as the always-on jobs node:** if your NAS runs Docker (Synology/QNAP do), it can replace the PC as the 24/7 worker — it never sleeps and sips power. Run the overnight Airtable→Gateway→`ops-brief.md` job here; the work phone reads the brief each morning.

**Safe & recommended for the NAS:**
- Enable NAS **drive encryption + scheduled snapshots/backup** — it now holds customer PII.
- Reach it only over **Tailscale**, never a public port.
- For team uploads (operators dropping condition photos), create a **dedicated NAS user with write-only access to the upload folder** — never NAS admin, and prefer they upload from the work/office device rather than personal phones.

**Setup add-ons (slot into the runbook after the Gateway is live):**
1. Install Tailscale on the NAS + your devices; confirm the NAS is reachable off-Wi-Fi.
2. Mount the NAS in Files on both iPhones and in Finder/Explorer on the Macs/PC.
3. Create `TMMT/Rentals/` on the NAS; build the NAS-aware Rental flow (see `AIXMOS_iPhone_System.md` §⑦).
4. Point the overnight ops-brief job's output at the NAS; add a scoped uploader account if operators will add photos.
