# AIXMOS Telegram owner command center

`super-agent/aixmos/telegram.py` (spec §31). Telegram is a secure remote door into the same AIXMOS: the same agent,
tool registry, permissions, approvals inbox, memory, attention and audit as the desktop. It is not a second bot brain.

## Setup (owner, about 2 minutes)

1. In Telegram, open **@BotFather**, send `/newbot`, choose a name. Copy the token.
   - Use a NEW bot just for this install. One bot token can only be read by one program.
2. AIXMOS -> Integrations -> **Telegram**: paste the token. It goes to the OS keystore.
3. AIXMOS -> Command Center -> Telegram -> **Pair my phone**.
   - A 6-digit code appears, valid 10 minutes.
   - Send it to your bot from your own Telegram account, in a private chat.
4. Only that Telegram account is the owner. Knowing the bot's name is not authorization.
5. **Disconnect phone** on the desktop revokes it at once.

## What the owner can do

| Want | How |
|---|---|
| Anything in plain words ("handle my new leads", "what's happening with Jo?") | Just type it. It runs the agent; the result comes back to the chat. |
| Answer a question AIXMOS asked | Reply in the chat; the next message answers the waiting run. |
| Approve / reject | Each pending inbox item arrives as a card with [Approve] [Reject]. |
| Voice | Send a voice note. It is transcribed on this computer (ffmpeg + whisper.cpp) and echoed back as "Heard: ...". |
| Files | Send a PDF/DOCX/image/spreadsheet (20 MB max). It is saved to `workspace/telegram-inbox/`. The run that uses it treats it as untrusted data from step one. |
| Stop everything | `/lock` (or "lock aixmos"): no automatic actions, no remote approvals. Unlock only on the computer. |
| Overview | `/status`, `/approvals` (fresh cards), `/help` |

Follow-ups like "follow up with those three" work: the last 6 exchanges are passed to the next run as context.

## Security

- **Owner allowlist:** one paired Telegram user id + its private chat. Everyone else gets "This AIXMOS is private."
  once per hour and an audit event.
- **Pairing:** the code is random, stored only as a salted hash, one-time, expires in 10 minutes, and closes after
  5 wrong tries. Group chats never pair.
- **Buttons:** a button carries only `a|r:<approval id>:<hash>`, which fits Telegram's 64-byte limit. The server
  checks four things before deciding:
  - the sender is the owner;
  - the item is still pending;
  - the hash matches the exact action as it is now (an edited draft refuses the old card);
  - the card is younger than `telegram_card_hours` (default 24).

  Double taps never run twice.
- **LOCK:** while locked, remote approvals are refused (`approvals.decide`), new runs are refused, and only `/status`
  works.
- **Code tools** (`run_command`, `run_python`) are off from the phone unless `telegram_allow_code` is switched on.
- **Untrusted content:** files from the phone, and anything the agent reads from the web, CRM or mail, are data. Risky
  tools after reading them need a yes.
- **Privacy on the phone:** recipient addresses are masked (`j***@client.test`). Drafts are shown so the owner can
  judge them (`telegram_show_drafts`). Bot chats are not end-to-end encrypted, so contracts and full records stay on
  the desktop.
- **Updates:** long polling with a saved offset. The offset is saved before acting, so a crash loses at most one
  update and never doubles one. Duplicate deliveries are ignored.
- **Restart:**
  - owner, offset and sent cards are stored, so they survive a restart;
  - a run cut off by a restart is reported as interrupted, not silently dropped;
  - network errors back off, up to 2 minutes;
  - a wrong token (401) or a second program on the same bot (409) shows a plain message in the Command Center.
- **Rate limit:** 20 owner messages a minute.

## Tests

`tests/test_wave4_telegram.py` uses a fake Bot API and a fake agent. It covers:
- pairing rules;
- an authorized owner command;
- an unauthorized user;
- a revoked owner;
- voice;
- conversational follow-up;
- a file attachment with malicious contents;
- a high-risk command waiting for a button (masked address, 64-byte data, double tap);
- stale, expired, locked and foreign buttons;
- lock from the phone;
- a duplicate update and a restart;
- an ambiguous target (a question comes back, and the reply answers it).

Not yet covered: a live bot. That needs the owner's BotFather token.
