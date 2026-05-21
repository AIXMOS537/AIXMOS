# AIX Command Center — Operating Guide (v1)

This guide tells you, the owner, how to use the brain-dump → ClickUp agent.

## How to brain-dump

1. Open `http://<home-pc-tailscale-name>:3000` from any device on your Tailnet.
2. Sign in.
3. New Chat → select the **TMMT Command Center** model.
4. Type or paste your brain-dump. Be specific about who, what, and when when you can. The more context you give in your message, the better the tasks come out.
5. The agent replies with a numbered list of the tasks it created, each with a clickable ClickUp URL.

### Good brain-dumps

> Customer Maria Rodriguez needs a follow-up call Tuesday. The white Mustang VIN ending 8847 needs an oil change before Thursday. Also John Smith's contract expires Friday — flag for renewal.

> Three urgent things: 1) inspect the Tahoe before it goes out tomorrow, 2) chase the insurance on rental #4421, 3) follow up with the GHL lead from yesterday named Tony.

### Mediocre brain-dumps

> need to deal with stuff today

(Not specific enough — the agent will ask clarifying questions instead of creating tasks.)

## What happens after

Every task the agent creates is assigned to YOU in ClickUp. You review them, then re-assign to your EAs in the normal ClickUp UI. EA-assignment automation is v1.5 (a future plan).

## Adding a new venture

When you launch business #2 (or any future venture):

1. Create a new list in ClickUp for that venture.
2. Copy its list ID (right-click the list → Copy link → the trailing `/li/<id>` segment).
3. Open `~/AIX-Command-Center/config/ventures.json` on the home PC (or any machine with the repo).
4. Add an entry:
   ```json
   {
     "slug": "venture-2-short-name",
     "name": "Venture 2 Pretty Name",
     "clickup_list_id": "<the new list id>",
     "default_tag": "venture-2-short-name",
     "status": "active"
   }
   ```
5. `git commit && git push` (if you've pushed this repo to GitHub).
6. The next time you start a chat with the agent it picks up the new venture automatically — no Open WebUI restart needed.

## Troubleshooting

| Symptom | What to check |
|---|---|
| Agent says "I don't see a venture called X" | The venture isn't in `ventures.json`, or you typed the slug wrong. |
| Agent reply contains `{"error": "CLICKUP_API_TOKEN not configured ..."}` | Tool valves aren't set. Open WebUI → Workspace → Tools → TMMT Command Center → Valves. Paste the `pk_` token. |
| Agent reply contains `{"error": "ClickUp API returned 401"}` | The token is wrong or expired. Re-generate via ClickUp → Settings → Apps → API Token. |
| Agent reply contains `{"error": "ClickUp API returned 429"}` | Rate-limited. Wait 60 seconds and re-paste the brain-dump. |
| URLs work but no tasks appear in ClickUp | You're looking at the wrong list. The list ID in `ventures.json` may not be the TMMT Rentals list — re-check Task 1 Step 3 of the v1 plan. |
| Open WebUI URL won't load | Tailscale isn't connected, OR Open WebUI isn't running on the home PC. SSH in and run `docker compose ps`. |

## What's coming next (per the v1 spec)

- **v1.5:** EA routing — say "route task #2 to Maria" and the agent reassigns the ClickUp task.
- **v2:** Voice input — speak your brain-dump, Whisper transcribes locally on the home PC.
- **v3:** Conversational status queries — "how's TMMT Rentals this week?" pulls from ClickUp + Supabase.
- **Onwards:** Adding new ventures becomes a routine config-file edit.

See `~/Documents/TMMT/docs/superpowers/specs/2026-05-21-brain-dump-clickup-agent-design.md`.

## Setup checklist (before first use)

Before brain-dumping for the first time, complete these one-time owner tasks (from the v1 plan):

- [ ] **Task 1** — Generate ClickUp API token, find your user ID, find the TMMT Rentals list ID
- [ ] Paste the three values into `~/AIX-Command-Center/.env` (replace the `REPLACE_ME` placeholders)
- [ ] Edit `~/AIX-Command-Center/config/ventures.json` — replace `REPLACE_ME_after_Task_1` with the real TMMT Rentals list ID
- [ ] **Task 9** — On the home PC, paste `tools/openwebui_tools.py` into Open WebUI → Workspace → Tools, set the Valves (`CLICKUP_API_TOKEN`, `CLICKUP_DEFAULT_ASSIGNEE_ID`), and create the "TMMT Command Center" model with the persona prompt from `agents/tmm-business-command-center.agent.md`
- [ ] **Task 10** — Run the smoke test: paste the canonical 3-item brain-dump, confirm 3 tasks land in ClickUp

The full plan is at `~/Documents/TMMT/docs/superpowers/plans/2026-05-21-brain-dump-clickup-agent.md`.
