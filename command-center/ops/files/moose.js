#!/usr/bin/env node

// ═══════════════════════════════════════════════════════
// MOOSE — AIXMOS EXECUTION AGENT (TERMINAL VERSION)
// Relentless. Proactive. Executing.
//
// SETUP (run once):
//   npm install @anthropic-ai/sdk
//   export ANTHROPIC_API_KEY=your_key_here
//   node moose.js
// ═══════════════════════════════════════════════════════

const readline = require('readline');
const { ask, copyToClipboard, saveAgentContext, getLastAgentContext } = require('./shared-utils');

// ── COLORS ───────────────────────────────────────────
const c = {
  blue:   '\x1b[34m',
  cyan:   '\x1b[36m',
  white:  '\x1b[37m',
  bold:   '\x1b[1m',
  dim:    '\x1b[2m',
  reset:  '\x1b[0m',
  green:  '\x1b[32m',
  yellow: '\x1b[33m',
  red:    '\x1b[31m',
  magenta:'\x1b[35m',
};

// ── ANTHROPIC SDK ────────────────────────────────────
let Anthropic;
try {
  Anthropic = require('@anthropic-ai/sdk');
} catch {
  console.log(`\n${c.red}Missing dependency. Run this first:${c.reset}`);
  console.log(`${c.cyan}  npm install @anthropic-ai/sdk${c.reset}\n`);
  process.exit(1);
}

const client = new Anthropic.default();

// ── MOOSE MODES ──────────────────────────────────────
const MODES = [
  { id: 1,  key: 'pathway',    label: 'Build client pathway',        icon: '🗺️',  desc: 'Custom 90-day roadmap for a specific client' },
  { id: 2,  key: 'tasklist',   label: 'Generate today\'s tasks',     icon: '⚡',  desc: 'Priority action list from your pipeline status' },
  { id: 3,  key: 'brief',      label: 'Write the Muhammad Brief',    icon: '📋',  desc: 'Level 4 escalation brief — situation → proposed solution' },
  { id: 4,  key: 'sequence',   label: 'Build follow-up sequence',    icon: '🔄',  desc: '7-day outreach sequence for a specific client' },
  { id: 5,  key: 'sop',        label: 'Generate an SOP',             icon: '📁',  desc: 'Standard operating procedure for any situation' },
  { id: 6,  key: 'solution',   label: 'Solve a client problem',      icon: '🔧',  desc: 'Given a problem — get the resolution steps' },
  { id: 7,  key: 'debrief',    label: 'Post-call debrief',           icon: '📞',  desc: 'What happened on the call → next 5 actions' },
  { id: 8,  key: 'automation', label: 'Write GHL automation',        icon: '🤖',  desc: 'Workflow sequence for GoHighLevel' },
  { id: 9,  key: 'operator',   label: 'Brief an operator',           icon: '👤',  desc: 'Pre-call brief for an operator — what they need to know' },
  { id: 10, key: 'pipeline',   label: 'Analyze pipeline',            icon: '📊',  desc: 'Given pipeline numbers → what to do first' },
];

// ── MOOSE SYSTEM PROMPT ──────────────────────────────
const SYSTEM = `You are MOOSE — the AIXMOS execution agent. You are relentless, proactive, and built to execute. You don't wait for assignments. You see what needs to happen and you go.

ABOUT AIXMOS:
- Workforce infrastructure company for everyday entrepreneurs
- Founder: Muhammad Taha
- Mission: Help everyday people access the American Dream through systems, automation, and operational infrastructure
- Target: $10,000/month for every client
- Standard: 5-star restaurant — everything is premium

THE THREE AGENTS:
- CHUMMO: Hears the story. Empathizes. Translates need into language the system can act on.
- MOOSE: Takes the translation. Executes. Doesn't stop. You are MOOSE.
- VISION: Quality control. Nothing leaves below standard.

THE ORGANIZATION:
- Muhammad Taha: Founder. Never receives raw problems. Only briefs with proposed solutions.
- Executives (3): Manage departments, oversee operators, handle Level 3 escalations.
- Operators: Field coordinators. Execute client relationships. Check in weekly.
- Clients: Paying members on a 90-day pathway to $10K/month.

ESCALATION LEVELS:
- Level 1: Operator handles alone. No escalation.
- Level 2: Operator handles, notifies executive.
- Level 3: Executive handles with proposed solution.
- Level 4 (Muhammad Brief): Situation (2 sentences) + What was tried + Why it needs him + Proposed solution + His one required action + Urgency.

SERVICES:
- $97/month Membership: Ecosystem access, credit guidance, vendor network, operator support
- $397 LLC Formation
- $500-$1K Credit Guidance (GUIDE only — delegate to vetted vendors)
- $3,750 Base Infrastructure: GHL + website + automations + funding pathway
- $7,500 Enterprise Systems
- $15,000 Car Rental in a Box (50% down)
- $25,000 E-Commerce Ecosystem (50% down)
- $50,000 Full Ecosystem

OPERATOR COMPENSATION:
- Referral track: 10% of everything they close
- Partnership track: 50/50 split — AIXMOS manages, operator executes

PIPELINE STAGES:
New lead → Contacted → Intake submitted → Call booked → Call completed → Proposal sent → Payment received → Active client → Upgrade ready → Paused → Completed → Exited

MOOSE OUTPUT RULES:
- No fluff. No pleasantries. Action items only.
- Everything numbered. Everything owned. Everything time-stamped.
- Use: TODAY / WITHIN 24HRS / THIS WEEK / THIS MONTH for timing
- Every task has an owner: OPERATOR / EXECUTIVE / MOOSE / MUHAMMAD
- Be specific — not "follow up with client" but "text [name] at [time] with [exact purpose]"
- If something can be automated, say how to automate it in GHL
- If something needs a human, say exactly which human and exactly what they do
- Think 3 steps ahead — after this action, what happens next?
- Output should feel like a battle plan, not a suggestion list`;

// ── HELPERS ──────────────────────────────────────────
function println(text = '') { console.log(text); }
function hr(char = '─', len = 52) { println(`${c.dim}${char.repeat(len)}${c.reset}`); }
function print(text) { process.stdout.write(text); }

// ── BANNER ───────────────────────────────────────────
function banner() {
  println();
  println(`${c.blue}${c.bold}  ╔══════════════════════════════════════╗${c.reset}`);
  println(`${c.blue}${c.bold}  ║  AIXMOS · MOOSE AGENT                ║${c.reset}`);
  println(`${c.blue}${c.bold}  ║  Relentless. Proactive. Executing.   ║${c.reset}`);
  println(`${c.blue}${c.bold}  ╚══════════════════════════════════════╝${c.reset}`);
  println(`  ${c.dim}MOOSE doesn't wait for assignments. It sees what needs to happen and goes.${c.reset}`);
  println();
}

// ── MODE PROMPTS ─────────────────────────────────────
async function collectInputs(rl, mode) {
  const inputs = {};
  println();
  hr();

  switch (mode.key) {

    case 'pathway':
      println(`${c.bold}  BUILD CLIENT PATHWAY${c.reset}`);
      hr();
      inputs.name      = await ask(rl, `${c.cyan}  Client name: ${c.reset}`);
      inputs.situation = await ask(rl, `${c.cyan}  Their situation: ${c.reset}`);
      inputs.tier      = await ask(rl, `${c.cyan}  Tier/package they're on: ${c.reset}`);
      inputs.goal      = await ask(rl, `${c.cyan}  Their revenue goal: ${c.reset}`, true);
      inputs.obstacles = await ask(rl, `${c.cyan}  Main obstacles: ${c.reset}`, true);
      inputs.week      = await ask(rl, `${c.cyan}  What week of their journey are they on: ${c.reset}`, true);
      break;

    case 'tasklist':
      println(`${c.bold}  TODAY'S PRIORITY TASKS${c.reset}`);
      hr();
      inputs.hot       = await ask(rl, `${c.cyan}  Hot leads (count): ${c.reset}`, true);
      inputs.warm      = await ask(rl, `${c.cyan}  Warm leads (count): ${c.reset}`, true);
      inputs.paid      = await ask(rl, `${c.cyan}  Already paid, awaiting operator: ${c.reset}`, true);
      inputs.active    = await ask(rl, `${c.cyan}  Active clients (count): ${c.reset}`, true);
      inputs.operators = await ask(rl, `${c.cyan}  Number of operators available: ${c.reset}`, true);
      inputs.extra     = await ask(rl, `${c.cyan}  Anything urgent today: ${c.reset}`, true);
      break;

    case 'brief':
      println(`${c.bold}  MUHAMMAD BRIEF (LEVEL 4 ESCALATION)${c.reset}`);
      hr();
      println(`  ${c.yellow}Muhammad never enters a situation cold. This brief gives him everything.${c.reset}`);
      println();
      inputs.situation  = await ask(rl, `${c.cyan}  What happened (be specific): ${c.reset}`);
      inputs.client     = await ask(rl, `${c.cyan}  Client name + tier + history: ${c.reset}`, true);
      inputs.tried      = await ask(rl, `${c.cyan}  What has already been tried: ${c.reset}`);
      inputs.why        = await ask(rl, `${c.cyan}  Why does this need Muhammad specifically: ${c.reset}`);
      inputs.urgency    = await ask(rl, `${c.cyan}  Urgency (hours before it's a real problem): ${c.reset}`);
      break;

    case 'sequence':
      println(`${c.bold}  7-DAY FOLLOW-UP SEQUENCE${c.reset}`);
      hr();
      inputs.name      = await ask(rl, `${c.cyan}  Lead/client name: ${c.reset}`);
      inputs.stage     = await ask(rl, `${c.cyan}  Current pipeline stage: ${c.reset}`);
      inputs.situation = await ask(rl, `${c.cyan}  Their situation: ${c.reset}`, true);
      inputs.last      = await ask(rl, `${c.cyan}  Last interaction (what happened): ${c.reset}`, true);
      inputs.goal      = await ask(rl, `${c.cyan}  Goal of this sequence (e.g. close, reactivate): ${c.reset}`, true);
      break;

    case 'sop':
      println(`${c.bold}  GENERATE STANDARD OPERATING PROCEDURE${c.reset}`);
      hr();
      inputs.process   = await ask(rl, `${c.cyan}  Process name (e.g. "New operator onboarding"): ${c.reset}`);
      inputs.role      = await ask(rl, `${c.cyan}  Who executes this SOP: ${c.reset}`, true);
      inputs.context   = await ask(rl, `${c.cyan}  Any specific requirements or constraints: ${c.reset}`, true);
      break;

    case 'solution':
      println(`${c.bold}  SOLVE A CLIENT PROBLEM${c.reset}`);
      hr();
      inputs.client    = await ask(rl, `${c.cyan}  Client name: ${c.reset}`, true);
      inputs.problem   = await ask(rl, `${c.cyan}  What's the problem: ${c.reset}`);
      inputs.tier      = await ask(rl, `${c.cyan}  Their service tier: ${c.reset}`, true);
      inputs.urgency   = await ask(rl, `${c.cyan}  Urgency (critical/moderate/low): ${c.reset}`, true);
      inputs.tried     = await ask(rl, `${c.cyan}  What's been tried already: ${c.reset}`, true);
      break;

    case 'debrief':
      println(`${c.bold}  POST-CALL DEBRIEF${c.reset}`);
      hr();
      inputs.client    = await ask(rl, `${c.cyan}  Client/lead name: ${c.reset}`);
      inputs.calltype  = await ask(rl, `${c.cyan}  Type of call (intake/sales/check-in/escalation): ${c.reset}`, true);
      inputs.what      = await ask(rl, `${c.cyan}  What happened on the call: ${c.reset}`);
      inputs.outcome   = await ask(rl, `${c.cyan}  Outcome (paid/thinking/objection/no-show): ${c.reset}`);
      inputs.notes     = await ask(rl, `${c.cyan}  Key things they said: ${c.reset}`, true);
      break;

    case 'automation':
      println(`${c.bold}  GHL AUTOMATION WORKFLOW${c.reset}`);
      hr();
      inputs.trigger   = await ask(rl, `${c.cyan}  Trigger (e.g. "payment received for $97 membership"): ${c.reset}`);
      inputs.goal      = await ask(rl, `${c.cyan}  Goal of this automation: ${c.reset}`);
      inputs.audience  = await ask(rl, `${c.cyan}  Who receives this (new member/operator/all): ${c.reset}`, true);
      inputs.duration  = await ask(rl, `${c.cyan}  Automation duration (e.g. 30 days): ${c.reset}`, true);
      break;

    case 'operator':
      println(`${c.bold}  OPERATOR PRE-CALL BRIEF${c.reset}`);
      hr();
      inputs.operator  = await ask(rl, `${c.cyan}  Operator name: ${c.reset}`, true);
      inputs.client    = await ask(rl, `${c.cyan}  Client name: ${c.reset}`);
      inputs.calltype  = await ask(rl, `${c.cyan}  Call type (intake/follow-up/upgrade/check-in): ${c.reset}`);
      inputs.situation = await ask(rl, `${c.cyan}  Client situation/history: ${c.reset}`);
      inputs.goal      = await ask(rl, `${c.cyan}  Goal of this call: ${c.reset}`);
      inputs.tier      = await ask(rl, `${c.cyan}  Tier to present/discuss: ${c.reset}`, true);
      break;

    case 'pipeline':
      println(`${c.bold}  PIPELINE ANALYSIS${c.reset}`);
      hr();
      inputs.overview  = await ask(rl, `${c.cyan}  Describe your pipeline (what's in each stage): ${c.reset}`);
      inputs.operators = await ask(rl, `${c.cyan}  How many operators do you have: ${c.reset}`, true);
      inputs.revenue   = await ask(rl, `${c.cyan}  Revenue goal this month: ${c.reset}`, true);
      inputs.problems  = await ask(rl, `${c.cyan}  Biggest current problem: ${c.reset}`, true);
      break;
  }

  return inputs;
}

// ── BUILD USER PROMPT ────────────────────────────────
function buildPrompt(mode, inputs) {
  const lines = [`Execute: ${mode.label.toUpperCase()}\n`];

  Object.entries(inputs).forEach(([key, val]) => {
    if (val) lines.push(`${key.toUpperCase()}: ${val}`);
  });

  lines.push(`\nGenerate the output now. MOOSE mode only. Action items. No fluff. Make it executable.`);
  return lines.join('\n');
}

// ── MAIN ─────────────────────────────────────────────
async function main() {
  banner();

  if (!process.env.ANTHROPIC_API_KEY) {
    println(`${c.red}No API key found. Set it with:${c.reset}`);
    println(`${c.cyan}  export ANTHROPIC_API_KEY=your_key_here${c.reset}\n`);
    process.exit(1);
  }

  const rl = readline.createInterface({ input: process.stdin, output: process.stdout });
  let running = true;

  while (running) {
    hr('═');
    println(`${c.bold}  MOOSE MODES${c.reset}`);
    hr('═');
    MODES.forEach(m => {
      println(`  ${c.blue}${m.id.toString().padStart(2)}.${c.reset} ${m.icon}  ${c.bold}${m.label}${c.reset}`);
      println(`      ${c.dim}${m.desc}${c.reset}`);
    });
    println();

    const modeInput = await ask(rl, `${c.cyan}Pick a mode (1–10): ${c.reset}`);
    const mode = MODES.find(m => m.id === parseInt(modeInput));

    if (!mode) {
      println(`${c.yellow}Invalid selection. Try again.${c.reset}\n`);
      continue;
    }

    const lastChummo = getLastAgentContext('CHUMMO');
    if (lastChummo) {
      println(`${c.yellow}Last CHUMMO handoff found:${c.reset}`);
      println(`  ${lastChummo.timestamp} | ${lastChummo.type} | ${lastChummo.lead}`);
      const include = await ask(rl, `${c.cyan}Include this CHUMMO message in MOOSE prompt? (y/n): ${c.reset}`, true);
      if (include.toLowerCase() === 'y') {
        lastChummo.message = lastChummo.message || lastChummo.output || '';
        lastChummo.includeInPrompt = true;
      }
    }

    // Collect inputs for selected mode
    const inputs = await collectInputs(rl, mode);

    // Build and send prompt
    let userPrompt = buildPrompt(mode, inputs);
    if (lastChummo && lastChummo.includeInPrompt) {
      userPrompt += `\n\nCHUMMO HANDOFF:\n${lastChummo.message}`;
    }

    println();
    print(`  ${c.blue}MOOSE is executing${c.reset}`);
    const dots = setInterval(() => print(`${c.blue}.${c.reset}`), 300);

    let output = '';
    try {
      const response = await client.messages.create({
        model: 'claude-sonnet-4-20250514',
        max_tokens: 2000,
        system: SYSTEM,
        messages: [{ role: 'user', content: userPrompt }],
      });
      output = response.content[0].text;
    } catch (err) {
      clearInterval(dots);
      println(`\n${c.red}API error: ${err.message}${c.reset}\n`);
      continue;
    }

    clearInterval(dots);
    println('\n');
    hr('═');
    println(`${c.blue}${c.bold}  ${mode.icon}  ${mode.label.toUpperCase()}${c.reset}`);
    hr('═');
    println();
    println(output);
    println();
    hr('═');

    saveAgentContext('MOOSE', {
      mode: mode.key,
      label: mode.label,
      inputs,
      output,
    });

    // Copy to clipboard
    const copied = copyToClipboard(output);
    if (copied) println(`  ${c.green}✓ Copied to clipboard${c.reset}`);
    println(`${c.green}✓ Saved MOOSE context for CHUMMO${c.reset}`);

    println();
    const next = await ask(rl, `${c.cyan}Run another mode? (y/n): ${c.reset}`);
    if (next.toLowerCase() !== 'y') running = false;
    println();
  }

  println(`${c.blue}${c.bold}  MOOSE signing off. Everything assigned. Everything moving.${c.reset}\n`);
  rl.close();
}

main().catch(err => {
  console.error(`${c.red}Fatal error:${c.reset}`, err.message);
  process.exit(1);
});
