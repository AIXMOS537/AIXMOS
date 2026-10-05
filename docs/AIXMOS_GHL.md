# AIXMOS GoHighLevel connector

`super-agent/aixmos/ghl.py`. Official API v2 (`https://services.leadconnectorhq.com`), Private Integration Token of
one sub-account. Verified live on 2026-10-05 against a test sub-account (reads, three approved writes, clean-up).

## Setup (owner)

1. In the sub-account: Settings -> Private Integrations -> new integration.
   - Read: contacts, conversations, opportunities, calendars, locations (tags, custom fields).
   - Write: contacts (notes, tasks, tags).
   - No message-sending scopes are needed. AIXMOS never sends through GoHighLevel.
2. AIXMOS -> Integrations -> GoHighLevel: paste the token and the Location ID.
   - The token goes to the OS keystore. `settings.json` keeps a marker only.
   - The token is never written to logs, prompts, the inbox or the audit trail.
3. The GHL tools appear to the agent only after both values are saved.

## What the agent can do

| Tool | Risk | Mode | API |
|---|---|---|---|
| `ghl_find_contacts` | LOW, untrusted output | AUTO | `POST /contacts/search` |
| `ghl_contact` (contact + notes + tasks + opportunities + latest messages) | LOW, untrusted output | AUTO | `GET /contacts/{id}`, `/notes`, `/tasks`, `GET /opportunities/search`, `GET /conversations/search`, `GET /conversations/{id}/messages` |
| `ghl_conversations` | LOW, untrusted output | AUTO | `GET /conversations/search` |
| `ghl_pipelines`, `ghl_calendars` | LOW | AUTO | `GET /opportunities/pipelines`, `GET /calendars/` |
| `ghl_add_note`, `ghl_add_task`, `ghl_add_tags` | MEDIUM | ALWAYS, via the inbox (`ghl.write`) | `POST /contacts/{id}/notes`, `/tasks`, `/tags` |

API versions:
- `2021-07-28` for most calls.
- `2021-04-15` for conversations and calendars.

Contact text (names, notes, messages) is wrapped as `UNTRUSTED CRM CONTENT`. After reading it, risky tools need a
person's yes for that exact call.

## Errors

| Status | Kind | Meaning shown to the owner |
|---|---|---|
| 401 | `auth` | Token wrong or revoked: paste a new one. |
| 403 | `scope` | The token lacks that permission: add the scope. |
| 404 | `not_found` | |
| 400 / 422 | `bad_request` | |
| 429 | `rate_limited` | Retried twice, honouring `Retry-After`. |
| 5xx / network | `server` / `offline` | GET retried once. |

Ids are validated before any call.

## Deliberately not built

- Sending SMS, email or WhatsApp.
- Deleting contacts or opportunities.
- Workflows (not creatable via the API).
- Payments.

Each of these needs its own reviewed step, an owner decision and, for texting, A2P/10DLC registration.

## Tests

- `tests/test_wave2_ghl.py`: a recorded fake transport, no network. It covers:
  - token storage
  - headers and versions
  - error classes
  - hidden-until-connected tools
  - untrusted CRM content
  - inbox-only writes with dedupe and exactly-once execution
  - no send capability
  - token absent from the audit trail
