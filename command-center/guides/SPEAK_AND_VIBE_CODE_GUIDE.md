# Speak to Your Computer & Vibe Code — Team Guide

**PDF (send to team):** `guides/SPEAK_AND_VIBE_CODE_GUIDE.pdf` (5 pages, print-ready)

**For:** Anyone with a laptop who does cleanup, Airtable, docs, or app fixes  
**Time to set up:** 10 minutes once · saves hours every week  
**You do NOT need:** coding experience · the owner's Mac · API keys in chat

---

## What this means (30 seconds)

| Term | Plain English |
|------|----------------|
| **Speak to your computer** | You talk; the computer types. Use that text in ChatGPT, Cursor, or WhatsApp. |
| **Vibe code** | You describe the outcome in normal words ("fix the login button", "clean duplicate leads"). AI does the typing/editing. You check the result. |
| **Agent** | The AI that can change files, run commands, and fix several things in one go (Cursor Agent or Codex). |

**Your job:** Say what you want · Review what AI did · Fix wrong details (especially money and customer names).

---

## Three speeds (pick one)

```text
FASTEST (phone, no laptop)
  Voice note in WhatsApp → Lead/Admin types into Airtable or paste into ChatGPT

MEDIUM (any laptop)
  Dictation ON → talk into ChatGPT or Claude → copy result into Airtable / ops chat

FASTEST FOR CODE (tech role)
  Dictation ON → talk into Cursor Agent → AI edits files → you click Accept after reading
```

| If you are… | Use this |
|-------------|----------|
| Operator on shift | Phone voice note → Admin or template (not vibe code) |
| Admin / VA with Airtable | ChatGPT/Claude + dictation for rows, messages, cleanup lists |
| Tech / cleanup | **Cursor** + dictation for app and doc fixes |
| Huge repo cleanup | **Codex** + dictated prompt (see workflow guide) |

---

## Step 1 — Turn on "talk and it types" (every laptop)

### Mac

1. **System Settings → Keyboard → Dictation → On**  
2. Shortcut: press **fn twice** (or mic key on keyboard) — speak — press **fn** again when done.  
3. Works in: Notes, ChatGPT in browser, Cursor chat box, Airtable notes field.

**Tip:** Say punctuation if you need it: "period" "new line" "comma".

### Windows

1. **Settings → Time & language → Speech** — turn on speech services.  
2. **Win + H** = dictate anywhere (Edge, Notepad, ChatGPT, Cursor).  
3. Or use **Microsoft Word / Google Docs** dictate, then copy.

### Phone (everyone)

- **WhatsApp voice note** to yourself or Admin — they transcribe or paste into AI.  
- **iPhone:** Voice Memos or dictate in Notes → copy to ChatGPT app.  
- **Android:** Google Keyboard mic in any text box.

---

## Step 2 — Vibe code without writing code (Admin + VAs)

Use **ChatGPT** or **Claude** (free or team account owner gives you). Turn on dictation, then **say** one of these:

### Clean up Airtable (say this)

```text
I have a car rental business. Here are 5 rows I verified by phone today:
[paste or dictate names, phones, amounts]

For each row tell me:
1) What fields to update in Airtable
2) What status to use: Open, Collected, Blocked, Closed
3) One sentence for the Notes field: source WhatsApp shift and today's date

Do not invent phone numbers or dollar amounts I did not say.
```

### Write a shift post (say this)

```text
Write a SHIFT END post for our ops WhatsApp group.
Rules: English only, short lines, include collections total, blocked items, handoff.
Today's facts: [dictate what happened on your shift]
Do not add fake customers or money.
```

### Turn messy notes into a task list (say this)

```text
Turn my voice notes into a numbered task list for today only.
Mark each P1 or P2. No tasks older than today unless I said still open.
```

**Then:** Copy AI output → paste into Airtable or ops chat yourself. **Read every number and name before sending.**

---

## Step 3 — Vibe code in Cursor (tech / cleanup role)

### Install (once)

1. https://cursor.com — download, sign in.  
2. **File → Open Folder** — open only the folder owner gave you (`TMMT` or `AIX-Command-Center`).  
3. Open **Chat** (sidebar) → switch mode to **Agent** (not Ask-only).

### The 60-second loop

```text
1. Double-tap fn (Mac) or Win+H (Windows) — DICTATE your request
2. Let Cursor Agent work — watch the file list it touches
3. Read the diff (green/red changes) — wrong customer name? STOP, undo
4. Click Accept only when it matches today's truth
5. Dictate the next step: "now run the build" or "fix the typo on the payments page"
```

### Good voice prompts (say these out loud)

**Small fix:**

```text
On the payments page, change the button label from Submit to Save Payment.
Do not change any other files. Show me the one file you edited.
```

**Cleanup:**

```text
Find duplicate headings in the guides folder markdown files only.
List duplicates first. Do not delete anything until I say yes.
```

**Deploy help:**

```text
The Vercel build failed with this error — paste last 20 lines of log.
Suggest the smallest fix. Do not touch env files or secrets.
```

### Bad prompts (wastes time)

- "Fix everything"  
- "Make the app perfect"  
- "Use my API key" (never say keys out loud)  
- Copying old spreadsheet without saying "verify by phone today"

---

## Step 4 — Heavy work: dictate to Codex

When the job is **many files** or **whole folder cleanup**, open **Codex** (desktop app or CLI), open the same repo folder, and **dictate** the same way — then paste if dictation is in another app.

**Say:**

```text
Bounded cleanup only. Read docs/superpowers/specs/2026-05-19-aix-command-center-hub-cleanup-design.md.
Move loose root markdown into guides or archive. Do not rename AIX_AI_COMMAND_SYSTEM or ops folders.
No env or API keys. Show before and after file tree. Wait for my yes before deleting.
```

Owner or lead approves before merge.

---

## Prompt recipe (works for voice or typing)

Use **GOAL → RULES → FACTS → STOP**:

| Part | Example (say it) |
|------|------------------|
| **GOAL** | "I need a SHIFT END message for ops WhatsApp." |
| **RULES** | "English only, under 12 lines, no made-up money." |
| **FACTS** | "Collected 840 from Jay, blocked on unit 12 battery, handing to night shift." |
| **STOP** | "Do not post anywhere — only give me the text to copy." |

Adding **STOP** stops the AI from doing extra steps you did not want.

---

## Speed tips (cut time in half)

1. **Dictate long, edit short** — 45 seconds of talking beats 10 minutes of typing prompts.  
2. **One job per message** — "fix button" then "run build", not both in a ramble.  
3. **Paste today's truth** — screenshot or paste the ops chat line before asking AI to update Airtable.  
4. **@ file in Cursor** — type `@` and pick the file so AI does not guess the wrong page.  
5. **Say "smallest change"** — keeps diffs small and review fast.  
6. **Phone for capture, laptop for fix** — voice note on lot → at desk, dictate into Cursor/ChatGPT.

---

## Safety (non-negotiable)

| Never | Always |
|-------|--------|
| Dictate passwords or API keys | Let owner put secrets in Vercel / `.env` |
| Trust AI dollar amounts you did not say | Call customer, then dictate verified numbers |
| Click Accept without reading diffs | Undo (Cmd+Z) if wrong name or amount |
| Post AI text straight to customers | Lead reviews customer-facing messages |
| Use owner's Mac | Your account, your machine |

**Old lists are wrong until verified today** — say that in every cleanup prompt.

---

## Who should use what

| Role | Speak where | Vibe code where |
|------|-------------|-----------------|
| Operator | WhatsApp voice note | ❌ — templates only |
| Admin Recorder | Dictation → ChatGPT | Airtable fields from AI draft |
| Lead Assistant | Dictation → ChatGPT | OWNER BRIEF, announcements draft |
| VA Ops | Dictation for reminders | Pin text, not code |
| Tech cleanup | Dictation → **Cursor Agent** | File fixes, small deploys |
| Owner | All of the above | Codex for big repo jobs |

---

## 5-minute practice (do once)

1. Open Notes (Mac) or Notepad (Windows).  
2. Turn on dictation. Say: "Today I verified three payments: 200, 150, and 490. Period."  
3. Copy text into ChatGPT. Say: "Format as a SHIFT END collections line for WhatsApp, English, short."  
4. Read output — if numbers match what you said, you are ready.  
5. (Tech only) Open Cursor, open one markdown file, dictate: "Fix spelling in this file only, show diff."

---

## Copy for WhatsApp (send to team)

```text
NEW — work faster by talking to your laptop

1) Turn on DICTATION:
   Mac: Settings → Keyboard → Dictation ON, press fn twice to talk
   Windows: Win + H to talk in any box

2) VIBE CODE = describe the job in plain English, AI does the typing
   Admin/VA: use ChatGPT + dictation for Airtable notes & shift posts
   Tech: use Cursor.com (Agent mode) + dictation to fix app/docs

3) RULE: Say real numbers you verified today. AI will NOT guess old list data.

4) You do NOT need the boss Mac or coding class.

Full guide: SPEAK_AND_VIBE_CODE_GUIDE (owner sends file)
```

---

## Related files

| File | Topic |
|------|--------|
| `guides/TEAM_WORKFLOW_AND_CLEANUP_GUIDE.md` | Cursor, Codex, Vercel, Airtable |
| `docs/LOCAL_AI_TOOL_GUIDE.md` | Cursor vs Claude vs Ollama |
| `guides/OPEN_IN_CURSOR.md` | Open the right folder |
| `AIX_AI_COMMAND_SYSTEM/DEVICE_SETUP_CHECKLIST.md` | Phone voice notes + pins |

---

*Talk like you are briefing a smart assistant. Review like you are signing a contract.*
