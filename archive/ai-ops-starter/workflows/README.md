# Workflows

Human-readable workflow descriptions. Automated versions live in `n8n/*.json` on **Brainiac 7**.

## 1. Team question → SOP answer

1. Team posts question (webhook or form)
2. n8n calls Ollama with **Counsel** prompt (SOP / knowledge)
3. Response returned; if `DOC_GAP`, file gap on NAS for review

## 2. Chat message → task assignment

1. Chat webhook receives message
2. **Operator** parses JSON task
3. Append to `life/tasks/` on NAS or local log

## 3. Meeting transcript → action items

1. Upload transcript to webhook
2. **Operator** formats action table
3. Save to `NAS/life/meetings/actions/` and notify owners

## 4. Unanswered → escalate Taha

1. Schedule every 4h
2. Find questions older than SLA
3. **Operator** summary → Slack/email to Taha

## 5. Daily recap

1. Weekdays 5pm cron
2. Aggregate tasks
3. **Operator** writes `daily-recap-YYYY-MM-DD.md` to NAS `life/journal/recaps/`

Import JSON files from n8n UI after Brainiac 7 stack is up.
