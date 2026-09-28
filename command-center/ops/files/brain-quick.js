#!/usr/bin/env node
/**
 * Non-interactive BRAIN for SMS/Telegram router.
 * Usage: node brain-quick.js "help me get cars earning today"
 * Prints one JSON line: { ok, summary, team_message, raw }
 */
const { chatCompletion, requireAiAvailable } = require('./llm-client');

const SYSTEM = `You are BRAIN for AIXMOS/TMMT. Produce a SHORT mobile-friendly plan.

Output exactly this structure (keep TEAM MESSAGE under 400 chars):
1) SCOPE: one sentence.
2) DELIVERABLES: three bullet lines max.
3) TASKS: three numbered tasks max (owner + action).
4) TEAM MESSAGE: one broadcast text the owner can iMessage to the team.
5) IF iMessage delivery is enabled, indicate the recipient handles or roles.`;

function extractTeamMessage(brainOutput) {
  const m =
    brainOutput.match(/4\)\s*TEAM MESSAGE:\s*([\s\S]*?)(?=\n\s*5\)\s|$)/i) ||
    brainOutput.match(/TEAM MESSAGE:\s*([\s\S]*?)(?=\n\s*5\)\s|$)/i);
  return m ? m[1].trim() : brainOutput.trim().slice(0, 400);
}

async function main() {
  const problem =
    process.argv.slice(2).join(' ').trim() || process.env.TMMT_BRAIN_PROBLEM || '';
  if (!problem) {
    console.error('usage: node brain-quick.js "<problem>"');
    process.exit(1);
  }
  await requireAiAvailable();
  const response = await chatCompletion({
    system: SYSTEM,
    userMessage: `Problem: ${problem}\nUrgency: critical\nGoal: revenue and cars moving today.`,
    maxTokens: 900,
  });
  const raw = response.text;
  const team = extractTeamMessage(raw);
  const out = {
    ok: true,
    summary: team || raw.slice(0, 200),
    team_message: team,
    raw,
  };
  console.log(JSON.stringify(out));
}

main().catch((err) => {
  console.log(JSON.stringify({ ok: false, summary: err.message, team_message: '', raw: '' }));
  process.exit(1);
});
