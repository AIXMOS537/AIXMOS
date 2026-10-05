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

## Next

| Wave | Work | Needs from the owner |
|---|---|---|
| 2 | Brand Profile (structured: voice, services, prices, policies, prohibited claims) feeding the Verifier. | |
| 3 | Lead-response skill: "Handle my new leads" end to end (find, read history, draft in brand voice, verify claims, one approval, send, update CRM, schedule follow-up, report). Replies go out by email through the inbox; GHL texting waits for A2P/10DLC and an owner decision. | |
| 3 | More GHL writes through the inbox (pipeline stage moves, appointments). GHL message sending only after A2P/10DLC and an owner decision. | Owner decision on texting |
| 4 | Telegram owner command center: own bot per install, owner pairing, approvals with buttons bound to an action hash, LOCK AIXMOS. Same orchestrator, not a separate bot. | Owner creates the bot |
| 4 | Calendar (Google / Cal.com), SMS + missed-call text-back. | Accounts, Twilio + 10DLC |
| 5 | Universal installer / bootstrapper: system profile, hardware tiers, model recommendations, 8-step onboarding. | |

## Open owner decisions

- Pollinations default (on since 2026-09-12; audit suggests off).
- Git history rewrite for earlier customer data.
- Accounts for Wave 3-4 (Telegram bot, calendar, Twilio). The GHL test sub-account is in use since 2026-10-05.
