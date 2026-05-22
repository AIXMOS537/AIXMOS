# Executive Agents (all tiers)

Three executives on every Brainiac node (tiers **7 → 1**). **Brainiac 7** is supreme; lower tiers escalate up. See `docs/brainiac-hierarchy.md`.

| Executive | File | Role | Best for |
|-----------|------|------|----------|
| **Oracle** | `oracle.md` | Strategist | Decisions, priorities, risk, "what should I do?" |
| **Operator** | `operator.md` | Operator | Daily processing, tasks, follow-ups, unstuck |
| **Counsel** | `counsel.md` | Counsel | Messages, people, research, tone |

## How to use

1. **Talk or type** in Open WebUI — pick the executive matching your moment.
2. **Voice:** see `docs/voice-executive-guide.md` (mic → Faster-Whisper → chat).
3. **Handoffs:** executives reference each other; you can say "loop in Operator."

## Legacy 12-agent pack

The original specialist agents are archived in `agents/archive/legacy-12/` for reference only. Do not import all twelve into Open WebUI for daily use.

## Models

| Executive | Default model | Why |
|-----------|---------------|-----|
| Oracle | `qwen2.5:7b` | Reasoning |
| Operator | `llama3.2` | Speed for daily check-ins |
| Counsel | `qwen2.5:7b` | Nuanced language |

Optional upgrade (if hardware allows): `qwen2.5:14b` for all three — see `setup/prerequisites.md`.
