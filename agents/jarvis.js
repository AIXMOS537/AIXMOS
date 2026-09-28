#!/usr/bin/env node
/**
 * JARVIS — routes infrastructure work across the full agent council.
 * RUN: node jarvis.js
 *      node jarvis.js "fix n8n and rental comms backlog"
 *      node jarvis.js --vote "deploy hub-brain and enable overdue GHL sync"
 */

const readline = require('readline');
const { loadAixmosEnv, requireEnv, requireLLMBackend } = require('./lib/env');
const prompts = require('./agents/prompts');
const state = require('./state');
const { runAgent, loadRegistry } = require('./lib/runner');
const { runInfraScan } = require('./lib/infra-scan');
const { runProductionVote } = require('./lib/jarvis-votes');
const { println, c, ask } = require('./lib/agent-cli');

loadAixmosEnv();

const MODES = [
  { id: 1, key: 'route', label: 'Route my request (auto-delegate)' },
  { id: 2, key: 'infra', label: 'Infrastructure health + fix plan' },
  { id: 3, key: 'owner', label: 'Owner brief (payouts / business / bottlenecks)' },
  { id: 4, key: 'council', label: 'Full council (VISION → CAPTAIN → execute)' },
  { id: 5, key: 'vote', label: 'Production panel vote (tmmt-os API)' },
];

async function runInfraMode(rl) {
  const checks = await runInfraScan();
  const lines = checks.map(ch => `- ${ch.name}: ${ch.ok ? 'OK' : 'FAIL'} (${ch.detail})`).join('\n');
  const extra = rl
    ? await ask(rl, `${c.cyan}What broke or what do you need fixed? ${c.reset}`)
    : '';
  const prompt = `Infrastructure scan results:\n${lines}\n\nOwner request: ${extra || 'general health and next fixes'}`;
  return runAgent({ system: prompts.jarvis, userPrompt: prompt });
}

async function runCouncil(rl, situation) {
  const sit =
    situation ||
    (rl ? await ask(rl, `${c.cyan}Situation for the council: ${c.reset}`) : '');
  if (!sit) return null;

  println(`\n${c.dim}VISION reviewing…${c.reset}`);
  const visionOut = await runAgent({
    system: prompts.vision,
    userPrompt: `Situation:\n${sit}\n\nGo/no-go and long-term fit.`,
  });

  if (/NO-GO\s*❌/i.test(visionOut)) {
    println('\n' + visionOut);
    return visionOut;
  }

  println(`${c.dim}CAPTAIN routing…${c.reset}`);
  const capOut = await runAgent({
    system: prompts.captain,
    userPrompt: `Situation:\n${sit}\n\nVISION said:\n${visionOut}\n\nRoute the cube.`,
  });

  println(`${c.dim}M.O.O.S.E executing…${c.reset}`);
  const mooseOut = await runAgent({
    system: prompts.moose,
    userPrompt: `Situation:\n${sit}\n\nCAPTAIN said:\n${capOut}\n\nExecute without hesitation.`,
  });

  const combined = `JARVIS COUNCIL RUN\n${'═'.repeat(40)}\n\n## VISION\n${visionOut}\n\n## CAPTAIN\n${capOut}\n\n## M.O.O.S.E\n${mooseOut}`;
  state.updateAgent('jarvis', { last_mode: 'council', last_output: combined.substring(0, 500) });
  return combined;
}

async function runVoteMode(rl, situation) {
  requireEnv(['TMMT_OPS_URL', 'AGENT_WEBHOOK_SECRET', 'ANTHROPIC_API_KEY']);
  const sit =
    situation ||
    (rl ? await ask(rl, `${c.cyan}Situation for production vote: ${c.reset}`) : '');
  if (!sit) return null;

  println(`\n${c.dim}Opening TMMT OS panel + casting 5 votes…${c.reset}`);
  const result = await runProductionVote(sit);
  const session = result.final?.session;
  const lines = [
    'JARVIS PRODUCTION VOTE',
    '═'.repeat(40),
    `Session: ${result.sessionId}`,
    `Subject: ${result.subjectType} / ${result.subjectId}`,
    `Status: ${session?.status ?? 'pending'}`,
    `Decision: ${session?.decision ?? '—'}`,
    '',
    'Votes:',
  ];
  for (const v of result.votes) {
    lines.push(`  ${v.agent}: ${v.vote} — ${v.rationale.slice(0, 120)}`);
  }
  lines.push('', 'JARVIS brief (excerpt):', result.jarvisBrief.slice(0, 800));
  const out = lines.join('\n');
  state.updateAgent('jarvis', { last_mode: 'vote', last_output: out.substring(0, 2000) });
  return out;
}

async function main() {
  try { requireLLMBackend(); }
  catch (e) { println(`${c.red}${e.message}${c.reset}`); process.exit(1); }

  const argv = process.argv.slice(2);
  const voteFlag = argv.includes('--vote');
  const argvSituation = argv.filter(a => a !== '--vote').join(' ').trim();

  if (voteFlag && argvSituation) {
    const out = await runVoteMode(null, argvSituation);
    if (out) println('\n' + out);
    return;
  }

  if (argvSituation && !voteFlag) {
    const out = await runCouncil(null, argvSituation);
    if (out) println('\n' + out);
    return;
  }

  const rl = readline.createInterface({ input: process.stdin, output: process.stdout });
  println();
  println(`${c.bold}JARVIS — AIXMOS Infrastructure Command${c.reset}`);
  println(`${c.dim}Speaks for you. Routes agents. Rentals-first.${c.reset}`);
  println();
  MODES.forEach(m => println(`  ${c.cyan}${m.id}.${c.reset} ${m.label}`));
  println();

  const pick = await ask(rl, `${c.cyan}Mode: ${c.reset}`);
  const mode = MODES.find(m => m.id === parseInt(pick, 10));
  if (!mode) {
    rl.close();
    return;
  }

  let output;
  switch (mode.key) {
    case 'route': {
      const req = await ask(rl, `${c.cyan}What do you need handled? ${c.reset}`);
      output = await runAgent({ system: prompts.jarvis, userPrompt: req });
      break;
    }
    case 'infra':
      output = await runInfraMode(rl);
      break;
    case 'owner': {
      const topic = await ask(
        rl,
        `${c.cyan}Topic (payouts / business / day-to-day / bottlenecks): ${c.reset}`
      );
      output = await runAgent({
        system: prompts.jarvis,
        userPrompt: `Owner brief on: ${topic}. Answer so Muhammad never has to repeat this again.`,
      });
      break;
    }
    case 'council':
      output = await runCouncil(rl);
      break;
    case 'vote':
      output = await runVoteMode(rl);
      break;
    default:
      break;
  }

  if (output) {
    println('\n' + '═'.repeat(56));
    println(output);
    println('═'.repeat(56));
    state.updateAgent('jarvis', { last_mode: mode.key, last_output: output.substring(0, 800) });
  }

  rl.close();
}

main().catch(e => {
  console.error(e.message);
  process.exit(1);
});
