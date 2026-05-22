# TMMT — start every morning (5 steps)

## 1. Open TMMT OS

https://tmmt-c919-two.vercel.app/login → **Internal dashboard**

Handle anything red on cases / vendor jobs first.

## 2. Run one command

```bash
cd /Volumes/LEXAR/AIX_AI_COMMAND_SYSTEM
./scripts/tmmt-day
```

This checks your connections, prints today’s **morning prompt**, and (when keys are set) pulls a live snapshot from Airtable + Supabase.

## 3. Paste the prompt into AI

Copy the morning block from the terminal into **ChatGPT** or **Claude**.

If you ran a snapshot, paste the AI summary too — or add: “Here is my live data:” and paste the JSON.

## 4. Act on the top 3

Put outcomes in **Airtable** (tasks, leads, money) or **TMMT OS** (case status, vendor assignment). Don’t leave it in chat only.

## 5. Midday (2 minutes)

```bash
./scripts/tmmt-day --midday
```

Paste the midday prompt before close of business.

---

## Keys (one-time, in `.env`)

| Variable | Get it from |
|----------|-------------|
| `AIRTABLE_API_KEY` | [airtable.com/create/tokens](https://airtable.com/create/tokens) → base `appcenWUju039rD7b` |
| `SUPABASE_KEY` | Supabase → Settings → API → **service_role** |
| `OPENAI_API_KEY` | Optional — AI summaries in `tmmt-day` |

Already set: `AIRTABLE_BASE_ID`, `SUPABASE_URL`, `VERCEL_APP_URL`, `VERCEL_SNAPSHOT_PATHS=/api/status`.

After updating TMMT OS, redeploy to Vercel so `/api/status` is live.

---

**More:** `INTEGRATION.md` · `integrations/TMMT_OS.md` · `START_HERE.md`
