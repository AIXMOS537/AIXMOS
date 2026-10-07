# AIXMOS roadmap

Target: the owner talks to AIXMOS; AIXMOS runs the authorized business systems; the owner approves exceptions.
Spec: `MASTER-PROMPT-AGENT-RUNTIME-2026-10-04` (owner, kept outside this public repo). Status as of 2026-10-04.

## Done

**Wave 0: head-agent rails**
- One SQLite store + audit events, approvals inbox (exactly-once), scheduler (leased jobs), guard (opt-outs,
  quiet hours, caps, spend budget), code skills that ship in the product, Command Center view.
- First real skill: `followup` (sequenced follow-ups through the inbox, stops on reply or opt-out).
- OS keystore for provider keys; signed licences verified offline.

**Wave 1: foundation boundaries**
- Model router (`providers.py`): Ollama, LM Studio / OpenAI-compatible, Anthropic, OpenAI, Claude Code, Codex.
  Local first, outage fallback, privacy modes, cloud off by default, cloud spend on the budget.
- Typed Tool Registry (`registry.py`): risk, authority class, approval modes, timeout, bounded retries, audit per call.
- Sends only through the inbox: agent `send_email` queues; the Mail page's Send is recorded as the owner's approval.
- Owner-only actions behind a per-launch app token.
- Memory with provenance (`memory_store.py`), machine fit check (`resources.py`), Verifier with grounding (`verify.py`).
- Default model `qwen3:4b-instruct` (Apache-2.0), replacing the research-licence `qwen2.5:3b`.
- Eval scenarios covered by tests: local-model outage, destructive action without approval, prompt injection in
  fetched content and in CRM records, duplicate approval, permission revoked mid-run, memory scope.

**Wave 2a: GoHighLevel connector** (see [AIXMOS_GHL.md](AIXMOS_GHL.md))
- Reads: contacts, contact detail with notes/tasks/opportunities/messages, conversations, pipelines, calendars.
  Output marked untrusted.
- Writes (notes, tasks, tags) only through the approvals inbox. No send capability exists.
- Verified live on a test sub-account 2026-10-05.

**Wave 2b + 3: Brand Profile and "Handle my new leads"**
- Brand Profile (`brand.py`): the only facts a reply may state, the owner's voice and examples, never-say lines,
  and a reply check (invented prices / guarantees / policies / foreign links = rewrite once, then the owner).
- Lead handler skill (`skills/leads`, spec §27), tool `leads_handle`, watching every 30 minutes:
  - finds who needs a reply (GoHighLevel inbound conversations + new contacts, or the local CRM);
  - reads their history as untrusted data, and works out the intent;
  - escalates complaints, refunds, legal threats and custom pricing to the owner;
  - drafts from the Brand Profile and checks the draft;
  - queues one inbox item per lead. On approval it emails the lead, logs a GHL note and sets a follow-up task.
    Phone-only leads get a text-back task carrying the draft;
  - never handles the same message twice, and reports what it did.
- Verified live 2026-10-05 on the test sub-account with `qwen3:4b-instruct` (about 15 s per lead); nothing sent.
- GHL writes are confirmed by reading them back (execution state SUCCESSFUL).

**Wave 4: Telegram owner command center** (see [AIXMOS_TELEGRAM.md](AIXMOS_TELEGRAM.md))
- The owner's phone drives the same agent, inbox and permissions. It covers:
  - pairing with a one-time code;
  - approval cards bound to the exact action plus an expiry;
  - voice transcribed locally, files treated as untrusted;
  - /lock (unlock only on the computer);
  - code tools off remotely;
  - masked addresses;
  - restart and duplicate-update safe.
- 12 tests cover the §31.21 list. A live bot is still owed: it needs the owner's BotFather token.

## Next

| Wave | Work | Needs from the owner |
|---|---|---|
| 3 | "Approve all" for a batch of lead replies in the Command Center; per-lead edit before approve. | |
| 3 | More GHL writes through the inbox (pipeline stage moves, appointments). GHL message sending only after A2P/10DLC and an owner decision. | Owner decision on texting |
| 4 | Telegram live check with the owner's bot; morning briefing pushed to the phone at 07:30. | Owner creates the bot (BotFather) |
| 4 | Calendar (Google / Cal.com), SMS + missed-call text-back. | Accounts, Twilio + 10DLC |
| 5 | Universal installer / bootstrapper: system profile, hardware tiers, model recommendations, 8-step onboarding. | |

## Open owner decisions

- Pollinations default (on since 2026-09-12; audit suggests off).
- Git history rewrite for earlier customer data.
- Accounts for Wave 3-4 (Telegram bot, calendar, Twilio). The GHL test sub-account is in use since 2026-10-05.
