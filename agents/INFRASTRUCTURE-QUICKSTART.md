# AIXMOS Infrastructure Agents — Quick Start

## Simple mode (home PC — start here)

**Double-click `AI-BRAIN.bat`** (or run `MAKE-DESKTOP-BRAIN.bat` once for a Desktop icon).

| Key | What it does |
|-----|----------------|
| **1** | Turn Brain ON |
| **2** | Ask the Brain |
| **3** | Who is Waiting? |
| **4** | Turn Brain OFF |

See `README-AI-BRAIN.txt` for the one-page guide.

---

## Setup env once

Copy `config\aixmos.env.example` → `.env` and fill:

- `ANTHROPIC_API_KEY`
- `TMMT_OPS_URL` + `AGENT_WEBHOOK_SECRET` (JARVIS production votes)
- `SUPABASE_URL` + `SUPABASE_SERVICE_ROLE_KEY` (STICKS alerts)
- `GHL_OVERDUE_WEBHOOK_SECRET` (STICKS → GHL tag)

Or keep secrets only in `tmmt-os\.env.local` — they load automatically.

## One command (recommended)

```bat
cd /d D:\AIXMOS-AGENTS
npm run jarvis
```

## Wired integrations

| Command | What it does |
|---------|----------------|
| `npm run tank:up` | **Auto-starts** hub-brain Docker (n8n + Open WebUI) |
| `npm run tank:status` | `docker compose ps` |
| `npm run sticks:scan` | Pulls **real overdue** from Supabase (ledger, payments, cases, GHL forms) |
| `npm run sticks:push` | Scan + POST to `tmmt-os` → GHL `payment-overdue` tag |
| `npm run jarvis:vote "…"` | Opens **production 3-of-5 panel** on TMMT OS + casts votes |

Or double-click **`START-INFRASTRUCTURE.bat`**.

## JARVIS modes

1. **Route my request** — tells you which agent owns it + execute-now steps  
2. **Infrastructure health** — scans paths, Docker, n8n:5678, chummo:3000  
3. **Owner brief** — payouts, business, day-to-day, bottlenecks (your voice)  
4. **Full council** — VISION → CAPTAIN → M.O.O.S.E in one run  

Quick council from terminal:

```bat
node jarvis.js "n8n is down and rental customers are waiting on replies"
```

## Run one agent

```bat
npm run tank      REM Docker, n8n, Supabase, Vercel
npm run sticks    REM SLA + overdue customer requests
npm run bob       REM audit trail + SOPs
npm run captain   REM priorities + team routing
npm run wonderwoman
npm run vision
npm run chummo    REM C.H.U.M.M.O messaging
npm run moose     REM M.O.O.S.E execution
```

## Who owns infrastructure

| Layer | Agent |
|-------|--------|
| Customer comms | C.H.U.M.M.O (+ FLY GUY support) |
| Close loops / CRM | M.O.O.S.E |
| Command / Rubik's cube | CAPTAIN |
| Trust / bad CX | WONDERWOMAN → you |
| Policy / bad ideas | VISION |
| Docker, n8n, DB, deploy | TANK |
| Logs + SOPs | BOB |
| SLA + timeliness | STICKS |
| Everything routed | JARVIS |

## What still needs you

- Insurance claims  
- Unpleasant customers / pitfalls  
- Level A outbound approval (when required)

## State file

All handoffs save to `D:\AIXMOS-AGENTS\aixmos-state.json`.
