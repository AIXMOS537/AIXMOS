# AIXMOS permissions

Maximum useful autonomy inside explicit authority. Every tool call is checked against data in
`super-agent/aixmos/registry.py`, not against if-statements scattered through the code.

## Risk levels

| Risk | Meaning | Examples |
|---|---|---|
| LOW | read, search, analyse | list/read/search files, web fetch/search, research, knowledge search, recall, list leads |
| MEDIUM | changes local records or creates drafts | write a workspace file, remember, add/update a lead, book in the local CRM, start a sequence, draft an email, generate media |
| HIGH | talks to people, runs code, deletes, spends, commits | send email, run a command, run Python |

## Approval modes

| Mode | What happens | Where nobody can answer (MCP, /v1) |
|---|---|---|
| AUTO | runs | runs |
| SESSION | asks once per run ("allow commands for the rest of this run?") | refused, unless the MCP server was started with `--allow-shell` (the owner's yes at launch) |
| ALWAYS | asks for every call; tools with an inbox (send_email) queue an approval item instead of asking | refused / queued |
| BLOCKED | never runs, and is not offered to the model | same |

Defaults come from the authority class of each tool (ported from the private line's authority model):

| Authority class | Decision | Default mode |
|---|---|---|
| read_machine, read_web, read_business_data, write_product_workspace, write_local_business_data, use_media_service | ALLOWED | AUTO |
| use_customer_connector_read | AUTHORIZED_SCOPE | AUTO (when connected) |
| run_code | CONDITIONAL | SESSION |
| send_customer_communication, publish_content, activate_automation, use_customer_connector_write | APPROVAL | ALWAYS |
| spend_money, sign_agreement, create_external_account | HUMAN | BLOCKED |
| delete_unique_data, production_deploy | RESTRICTED / RELEASE | BLOCKED |

The owner can change any tool in **Command Center -> Permissions** (stored in prefs `tool_policy`). Choosing
the default again removes the override. Turning a non-AUTO tool to AUTO asks for confirmation.

## Layers that always apply

1. **Autonomy level** (`safe` / `builder` / `full`): which tools are offered at all. MCP and `/v1` default to `safe`.
2. **Untrusted content.** After a run reads web pages, CRM records or mail, every writing tool that is HIGH risk,
   runs code, writes workspace files, starts an automation or comes from a skill needs a yes for that exact call.
   The content itself is wrapped as `UNTRUSTED ... CONTENT` for the model.
3. **Spend budget.** Paid tools and automatic cloud model calls are charged before they run and stop at
   `spend_daily_usd` (default $2). A person clicking in the app is never blocked.
4. **Rails at send time.** Opt-outs, do-not-contact, quiet hours for texts, daily caps. The owner writing an email by
   hand is not held to the caps; opt-outs hold for everyone.
5. **Owner-only actions.** Approving, autopilot, permissions, privacy and memory changes need the app page's
   per-launch token (`X-AIXMOS-UI`). `POST /api/email/send` without it only queues the email for approval.

## Autopilot

Off for every skill until the owner turns it on in the Command Center, per skill. Autopilot skips the inbox for
that skill's sends; the rails above still apply. The agent's own emails use the skill name `agent`.

## Audit

Every tool call writes a `tool.call` event: run id, risk, mode, source (core or skill), result or error, duration,
whether the run was tainted, and arguments with long values cut and anything named like a key or token masked.
Approvals, sends, blocks, spend refusals, fallbacks and policy changes have their own events.
