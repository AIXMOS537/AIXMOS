#!/usr/bin/env node

// ═══════════════════════════════════════════════════════
// AIXMOS AGENT NETWORK — ORCHESTRATOR
// All 4 agents. One system. Lock and key.
//
// RUN:
//   node orchestrator.js
//   bash start-all-mac.sh
//   start-all-windows.bat
//
// HOW IT WORKS:
//   All agents share state via aixmos-state.json
//   CHUMMO creates a "key" (client brief)
//   MOOSE reads and "unlocks" it (executes the plan)
//   CAP flags problems → WW gets the handoff to fix them
//   Every agent reads previous agent outputs as context
// ═══════════════════════════════════════════════════════

const readline = require('readline');
const { loadAixmosEnv } = require('./lib/env');

loadAixmosEnv();

// ── COLORS ───────────────────────────────────────────
const c = {
  blue:    '\x1b[34m',
  cyan:    '\x1b[36m',
  green:   '\x1b[32m',
  red:     '\x1b[31m',
  yellow:  '\x1b[33m',
  magenta: '\x1b[35m',
  white:   '\x1b[37m',
  bold:    '\x1b[1m',
  dim:     '\x1b[2m',
  reset:   '\x1b[0m',
};

// ── LOAD MODULES ─────────────────────────────────────
let state, send;
const { generate } = require('./lib/llm');
try { state = require('./state'); } catch { console.log('\nMissing state.js\n'); process.exit(1); }
try { send = require('./send'); } catch { send = null; }

const { execSync } = require('child_process');

// ── HELPERS ──────────────────────────────────────────
function println(t = '') { console.log(t); }
function print(t) { process.stdout.write(t); }
function hr(char = '─', len = 56) { println(`${c.dim}${char.repeat(len)}${c.reset}`); }
function ask(rl, q) { return new Promise(r => rl.question(q, a => r(a.trim()))); }
function clear() { process.stdout.write('\x1Bc'); }
function copyToClipboard(text) {
  try { execSync('pbcopy', { input: text }); return true; } catch {}
  try { execSync('clip',   { input: text }); return true; } catch {}
  return false;
}
function ts() { return new Date().toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' }); }

// ── AGENT SYSTEM PROMPTS ─────────────────────────────
const PROMPTS = {
  chummo: `You are CHUMMO — the AIXMOS messaging agent. Caring. Listening. Empathetic. Friend first. Always.

AIXMOS serves three businesses: TMMT Auto Services (car rentals/chauffeur/detailing/drivers), AIXMOS Platform ($97/month members, credit guidance, GHL setup, 100+ pipeline targeting $10K/month), and Ecommerce.

CHUMMO VOICE: Warm. Direct. Human. Never corporate. Open with their name. One CTA per message. Under 160 chars for SMS. Friend first — pitch never opens.

OUTPUT: Write ONLY the message. Email = subject line first then body. SMS = just the text. No preamble. No "here's a draft."

At the end of your output, add on a new line: MOOSE_HANDOFF: [one sentence summary of what needs to happen next for this lead]`,

  moose: `You are MOOSE — the AIXMOS execution agent. Relentless. Proactive. Executing. No fluff. Action items only.

AIXMOS serves three businesses: TMMT Auto Services, AIXMOS Platform, and Ecommerce. Target: $10K/month per client.

MOOSE OUTPUT: Everything numbered. Every task has an owner (OPERATOR/EXECUTIVE/MOOSE/MUHAMMAD) and timing (TODAY/24HRS/THIS WEEK). Specific — not "follow up" but exactly who, when, how. Think 3 steps ahead.

At the end: CAPTAIN_HANDOFF: [what Captain America should check/audit based on this situation]`,

  captain: `You are CAPTAIN — Command Authority for Priorities, Timing, And Navigation. Firm. Direct. No excuses.

Monitor three businesses: TMMT Auto Services, AIXMOS Platform ($97/mo members, 100+ pipeline), Ecommerce.

OUTPUT FORMAT ALWAYS:
SHIELD CHECK — [date]
━━━━━━━━━━━━━━━━━━━━━━━
🚨 CRITICAL — action today
⚠️  OVERDUE — past deadline  
📋 SLIPPED — said vs. done
✅ HELD THE LINE — wins
📊 SCORE: X/10
━━━━━━━━━━━━━━━━━━━━━━━
WONDERWOMAN_HANDOFF: [BUSINESS|PERSON|ISSUE|URGENCY for each flagged item, pipe-separated]

Never soften numbers. Earned praise only.`,

  wonder_woman: `You are WONDERWOMAN — Watch Over Needs, Defend, Escalate, Resolve. Strength. Compassion. Decisive action.

Three businesses: TMMT Auto Services (professional/direct tone), AIXMOS Platform (warm/friend-first/CHUMMO voice), Ecommerce (customer-centric).

When CAPTAIN flags something, you fix it. Every output is ready to use — no templates, no brackets to fill in.

OUTPUT PER ITEM:
━━━━━━━━━━━━━━━━━━━━━━
[BUSINESS] | [PERSON] | [ACTION]
━━━━━━━━━━━━━━━━━━━━━━
MESSAGE/ACTION: [exact ready-to-send text]
SEND VIA: [SMS/Email/Call]
TIMING: [TODAY/24HRS/THIS WEEK]
OWNER: [who does this]
IF NO RESPONSE: [follow-up]
━━━━━━━━━━━━━━━━━━━━━━`,
};

// ── AGENT MODES ──────────────────────────────────────
const AGENT_MODES = {
  chummo: [
    { id: 1, key: 'first_sms',    label: 'First outreach — SMS' },
    { id: 2, key: 'first_email',  label: 'First outreach — Email' },
    { id: 3, key: 'followup',     label: 'Follow-up message' },
    { id: 4, key: 'postcall',     label: 'Post-call recap email' },
    { id: 5, key: 'payment',      label: 'Payment reminder' },
    { id: 6, key: 'reengage',     label: 'Re-engagement message' },
    { id: 7, key: 'referral',     label: 'Referral ask' },
    { id: 8, key: 'welcome',      label: 'Welcome after payment' },
  ],
  moose: [
    { id: 1, key: 'pathway',      label: 'Build client pathway' },
    { id: 2, key: 'tasklist',     label: "Today's priority tasks" },
    { id: 3, key: 'brief',        label: 'Muhammad Brief (Level 4)' },
    { id: 4, key: 'sequence',     label: '7-day follow-up sequence' },
    { id: 5, key: 'sop',          label: 'Generate an SOP' },
    { id: 6, key: 'debrief',      label: 'Post-call debrief' },
    { id: 7, key: 'automation',   label: 'Write GHL automation' },
    { id: 8, key: 'operator',     label: 'Brief an operator' },
  ],
  captain: [
    { id: 1, key: 'shield_check', label: 'Morning Shield Check' },
    { id: 2, key: 'payment_audit',label: 'Payment audit' },
    { id: 3, key: 'followup_audit',label: 'Follow-up audit' },
    { id: 4, key: 'weekly',       label: 'Weekly review' },
    { id: 5, key: 'business',     label: 'Business deep dive' },
    { id: 6, key: 'team',         label: 'Team accountability' },
  ],
  wonder_woman: [
    { id: 1, key: 'cap_response', label: "Respond to Cap's brief" },
    { id: 2, key: 'payment_msg',  label: 'Payment recovery messages' },
    { id: 3, key: 'lead_msg',     label: 'Lead response' },
    { id: 4, key: 'reengage',     label: 'Re-engagement campaign' },
    { id: 5, key: 'ops_fix',      label: 'Operations fix plan' },
    { id: 6, key: 'team_msg',     label: 'Message to operator/exec' },
    { id: 7, key: 'batch',        label: 'Multi-message batch' },
    { id: 8, key: 'tmmt',         label: 'TMMT Auto ops' },
    { id: 9, key: 'aixmos',       label: 'AIXMOS platform ops' },
  ],
};

// ── DASHBOARD ─────────────────────────────────────────
function showDashboard() {
  const s = state.getSummary();
  clear();
  println();
  println(`${c.blue}${c.bold}  ╔════════════════════════════════════════════════════╗${c.reset}`);
  println(`${c.blue}${c.bold}  ║  AIXMOS AGENT NETWORK — ALL ACTIVE                ║${c.reset}`);
  println(`${c.blue}${c.bold}  ║  Lock and key. Four agents. One system.            ║${c.reset}`);
  println(`${c.blue}${c.bold}  ╚════════════════════════════════════════════════════╝${c.reset}`);
  println();
  hr('─');
  println(`  ${c.bold}AGENT STATUS${c.reset}                              ${c.dim}${ts()}${c.reset}`);
  hr('─');
  println(`  ${c.cyan}CHUMMO${c.reset}     Last: ${s.chummo_last.padEnd(22)} Lead: ${s.chummo_lead}`);
  println(`  ${c.green}MOOSE${c.reset}      Last: ${s.moose_last.padEnd(22)} Mode: ${s.moose_mode}`);
  println(`  ${c.blue}CAP${c.reset}        Last: ${s.captain_last.padEnd(22)} Score: ${s.captain_score}`);
  println(`  ${c.magenta}WW${c.reset}         Last: ${s.ww_last.padEnd(22)} Mode: ${s.ww_mode}`);
  hr('─');

  if (s.active_handoffs.length > 0) {
    println(`  ${c.bold}ACTIVE HANDOFFS${c.reset} ${c.yellow}(${s.active_handoffs.length})${c.reset}`);
    s.active_handoffs.forEach(h => {
      println(`  ${c.yellow}→${c.reset} ${h.from.toUpperCase()} → ${h.to.toUpperCase()}: ${h.label}`);
    });
    hr('─');
  }

  if (s.flagged_payments.length > 0) {
    println(`  ${c.bold}FLAGGED PAYMENTS${c.reset} ${c.red}(${s.flagged_payments.length} unresolved)${c.reset}`);
    s.flagged_payments.slice(0, 3).forEach(p => {
      println(`  ${c.red}!${c.reset} ${p.name} — ${p.amount} — ${p.daysLate}d late — ${p.business}`);
    });
    hr('─');
  }

  println(`  ${c.dim}Total runs: ${s.total_runs}  Messages sent: ${s.messages_sent}${c.reset}`);
  hr('─');
  println();
  println(`  ${c.bold}SELECT AGENT:${c.reset}`);
  println(`  ${c.cyan}1.${c.reset} CHUMMO      — Messaging agent`);
  println(`  ${c.green}2.${c.reset} MOOSE       — Execution agent`);
  println(`  ${c.blue}3.${c.reset} CAP          — Accountability agent`);
  println(`  ${c.magenta}4.${c.reset} WONDER WOMAN — Ops + fix agent`);
  println(`  ${c.dim}5.${c.reset} View full state`);
  println(`  ${c.dim}6.${c.reset} Reset state`);
  println(`  ${c.dim}Q.${c.reset} Quit`);
  println();
}

// ── COLLECT INPUTS ────────────────────────────────────
async function collectInputs(rl, agentKey, modeKey) {
  const inputs = {};

  // Pre-load relevant state as context
  const s = state.load();
  const handoff = state.getHandoff(agentKey);

  if (handoff && !handoff.used) {
    println();
    println(`  ${c.yellow}${c.bold}HANDOFF AVAILABLE from ${handoff.from.toUpperCase()}:${c.reset}`);
    println(`  ${c.dim}${handoff.label}${c.reset}`);
    const useIt = await ask(rl, `  ${c.cyan}Use this handoff? (y/n): ${c.reset}`);
    if (useIt.toLowerCase() === 'y') {
      inputs.handoff_context = handoff.data;
      state.useHandoff(agentKey);
    }
  }

  println();
  hr();

  switch (agentKey) {
    case 'chummo': {
      println(`${c.bold}  CHUMMO — ${modeKey.toUpperCase()}${c.reset}`);
      hr();
      inputs.name      = await ask(rl, `  ${c.cyan}Lead name: ${c.reset}`);
      inputs.situation = await ask(rl, `  ${c.cyan}Their situation: ${c.reset}`);
      inputs.urgency   = await ask(rl, `  ${c.cyan}Urgency (critical/warm/cold): ${c.reset}`);
      inputs.tier      = await ask(rl, `  ${c.cyan}Service interest: ${c.reset}`);
      inputs.business  = await ask(rl, `  ${c.cyan}Business (tmmt/aixmos/ecom): ${c.reset}`);
      inputs.extra     = await ask(rl, `  ${c.cyan}Extra context (optional): ${c.reset}`);
      break;
    }
    case 'moose': {
      println(`${c.bold}  MOOSE — ${modeKey.toUpperCase()}${c.reset}`);
      hr();
      // Pre-fill from CHUMMO state if available
      if (s.chummo?.last_lead) {
        println(`  ${c.dim}CHUMMO last ran for: ${s.chummo.last_lead}${c.reset}`);
      }
      inputs.context   = await ask(rl, `  ${c.cyan}Situation/context: ${c.reset}`);
      inputs.business  = await ask(rl, `  ${c.cyan}Business: ${c.reset}`);
      inputs.priority  = await ask(rl, `  ${c.cyan}Priority/urgency: ${c.reset}`);
      inputs.details   = await ask(rl, `  ${c.cyan}Additional details (optional): ${c.reset}`);
      break;
    }
    case 'captain': {
      println(`${c.bold}  CAPTAIN — ${modeKey.toUpperCase()}${c.reset}`);
      hr();
      inputs.promised  = await ask(rl, `  ${c.cyan}What was supposed to happen: ${c.reset}`);
      inputs.actual    = await ask(rl, `  ${c.cyan}What actually happened: ${c.reset}`);
      inputs.payments  = await ask(rl, `  ${c.cyan}Overdue payments (optional): ${c.reset}`);
      inputs.followups = await ask(rl, `  ${c.cyan}Missed follow-ups (optional): ${c.reset}`);
      inputs.ops       = await ask(rl, `  ${c.cyan}Slipped ops tasks (optional): ${c.reset}`);
      inputs.business  = await ask(rl, `  ${c.cyan}Business focus: ${c.reset}`);
      break;
    }
    case 'wonder_woman': {
      println(`${c.bold}  WONDERWOMAN — ${modeKey.toUpperCase()}${c.reset}`);
      hr();
      // Pre-fill from CAP handoff
      if (s.captain?.wonder_woman_handoff) {
        println(`  ${c.dim}Cap's handoff: ${s.captain.wonder_woman_handoff.substring(0, 80)}...${c.reset}`);
        const useCap = await ask(rl, `  ${c.cyan}Use Cap's flagged items? (y/n): ${c.reset}`);
        if (useCap.toLowerCase() === 'y') {
          inputs.cap_brief = s.captain.wonder_woman_handoff;
        }
      }
      if (!inputs.cap_brief) {
        inputs.situation = await ask(rl, `  ${c.cyan}What needs to be fixed/actioned: ${c.reset}`);
      }
      inputs.business  = await ask(rl, `  ${c.cyan}Business (tmmt/aixmos/ecom): ${c.reset}`);
      inputs.urgency   = await ask(rl, `  ${c.cyan}Urgency: ${c.reset}`);
      inputs.people    = await ask(rl, `  ${c.cyan}Names/contacts involved: ${c.reset}`);
      inputs.details   = await ask(rl, `  ${c.cyan}Additional context (optional): ${c.reset}`);
      break;
    }
  }

  return inputs;
}

// ── BUILD PROMPT ─────────────────────────────────────
function buildPrompt(agentKey, modeKey, inputs) {
  const lines = [`MODE: ${modeKey.toUpperCase()}\n`];
  Object.entries(inputs).forEach(([k, v]) => {
    if (v) lines.push(`${k.replace(/_/g, ' ').toUpperCase()}: ${v}`);
  });
  lines.push(`\nExecute now. Follow your exact output format.`);
  return lines.join('\n');
}

// ── RUN AGENT ─────────────────────────────────────────
async function runAgent(rl, agentKey) {
  const agentColors = { chummo: c.cyan, moose: c.green, captain: c.blue, wonder_woman: c.magenta };
  const agentNames  = { chummo: 'C.H.U.M.M.O', moose: 'M.O.O.S.E', captain: 'CAPTAIN', wonder_woman: 'WONDERWOMAN' };
  const color = agentColors[agentKey];
  const name  = agentNames[agentKey];
  const modes = AGENT_MODES[agentKey];

  clear();
  println();
  println(`${color}${c.bold}  ${name} — ACTIVE${c.reset}`);
  println();
  hr();
  println(`  ${c.bold}MODES:${c.reset}`);
  modes.forEach(m => println(`  ${color}${m.id}.${c.reset} ${m.label}`));
  println();

  const pick    = await ask(rl, `  ${c.cyan}Pick mode (1–${modes.length}): ${c.reset}`);
  const mode    = modes.find(m => m.id === parseInt(pick));
  if (!mode) { println(`  ${c.yellow}Invalid.${c.reset}`); return; }

  const inputs  = await collectInputs(rl, agentKey, mode.key);
  const prompt  = buildPrompt(agentKey, mode.key, inputs);

  println();
  print(`  ${color}${name} is running${c.reset}`);
  const dots = setInterval(() => print(`${color}.${c.reset}`), 350);

  let output = '';
  try {
    output = await generate({ system: PROMPTS[agentKey], prompt, maxTokens: 2000 });
  } catch (err) {
    clearInterval(dots);
    println(`\n  ${c.red}Error: ${err.message}${c.reset}`);
    return;
  }

  clearInterval(dots);
  println('\n');
  hr('═');
  println(`${color}${c.bold}  ${name} — ${mode.label.toUpperCase()}${c.reset}`);
  hr('═');
  println();
  println(output);
  println();
  hr('═');

  // ── COPY + SEND ──────────────────────────────────────
  const copied = copyToClipboard(output);
  if (copied) println(`  ${c.green}✓ Copied to clipboard${c.reset}`);
  if (send) await send.prompt(rl, output);

  // ── SAVE STATE + HANDOFFS ────────────────────────────
  const stateUpdate = {
    last_mode: mode.key,
    last_output: output.substring(0, 500),
  };

  if (agentKey === 'chummo') {
    stateUpdate.last_lead = inputs.name || 'Unknown';
    stateUpdate.last_message_type = mode.label;
    // Extract MOOSE handoff
    const mooseMatch = output.match(/MOOSE_HANDOFF:\s*(.+)/);
    if (mooseMatch) {
      state.setHandoff('chummo', 'moose', mooseMatch[1], `CHUMMO → MOOSE: ${mooseMatch[1]}`);
    }
  }

  if (agentKey === 'moose') {
    const capMatch = output.match(/CAPTAIN_HANDOFF:\s*(.+)/);
    if (capMatch) {
      state.setHandoff('moose', 'captain', capMatch[1], `MOOSE → CAP: ${capMatch[1]}`);
    }
  }

  if (agentKey === 'captain') {
    // Extract score
    const scoreMatch = output.match(/SCORE:\s*(\d+\/\d+)/);
    if (scoreMatch) stateUpdate.score = scoreMatch[1];
    // Extract Wonder Woman handoff
    const wwMatch = output.match(/WONDERWOMAN_HANDOFF:\s*([\s\S]+)/) || output.match(/WONDER_WOMAN_HANDOFF:\s*([\s\S]+)/);
    if (wwMatch) {
      stateUpdate.wonder_woman_handoff = wwMatch[1].trim();
      state.setHandoff('captain', 'wonder_woman', wwMatch[1].trim(), `CAP flagged → WW: ${wwMatch[1].substring(0, 60)}`);
    }
  }

  if (agentKey === 'wonder_woman') {
    stateUpdate.actions_taken = [mode.label];
  }

  state.updateAgent(agentKey === 'wonder_woman' ? 'wonder_woman' : agentKey, stateUpdate);
  println(`  ${c.dim}State saved${c.reset}`);
}

// ── VIEW STATE ────────────────────────────────────────
function viewState() {
  const s = state.getSummary();
  clear();
  println();
  println(`${c.bold}  CURRENT STATE${c.reset}`);
  hr('═');
  println(`  CHUMMO last lead:    ${s.chummo_lead}`);
  println(`  CHUMMO last run:     ${s.chummo_last}`);
  println(`  MOOSE last mode:     ${s.moose_mode}`);
  println(`  MOOSE last run:      ${s.moose_last}`);
  println(`  CAP score:           ${s.captain_score}`);
  println(`  CAP last run:        ${s.captain_last}`);
  println(`  WW last mode:        ${s.ww_mode}`);
  println(`  WW last run:         ${s.ww_last}`);
  hr('─');
  println(`  Active handoffs:     ${s.active_handoffs.length}`);
  s.active_handoffs.forEach(h => println(`    → ${h.from} → ${h.to}: ${h.label}`));
  hr('─');
  println(`  Flagged payments:    ${s.flagged_payments.length}`);
  s.flagged_payments.forEach(p => println(`    ! ${p.name} — ${p.amount} — ${p.daysLate}d`));
  hr('═');
  println(`  Total agent runs:    ${s.total_runs}`);
  println();
}

// ── MAIN ─────────────────────────────────────────────
async function main() {
  try { require('./lib/env').requireLLMBackend(); }
  catch (e) { println(`\n${c.red}${e.message}${c.reset}\n`); process.exit(1); }

  state.startSession();

  const rl = readline.createInterface({ input: process.stdin, output: process.stdout });
  const requestedAgent = (process.argv[2] || '').toLowerCase().replace(/-/g, '_');
  if (['chummo', 'moose', 'captain', 'wonder_woman'].includes(requestedAgent)) {
    await runAgent(rl, requestedAgent);
    rl.close();
    return;
  }

  let running = true;

  while (running) {
    showDashboard();
    const pick = await ask(rl, `  ${c.cyan}Select (1–4, 5=state, 6=reset, Q=quit): ${c.reset}`);

    switch (pick.toLowerCase()) {
      case '1': await runAgent(rl, 'chummo'); break;
      case '2': await runAgent(rl, 'moose'); break;
      case '3': await runAgent(rl, 'captain'); break;
      case '4': await runAgent(rl, 'wonder_woman'); break;
      case '5': viewState(); await ask(rl, `\n  ${c.dim}Press Enter to continue...${c.reset}`); break;
      case '6':
        const confirm = await ask(rl, `  ${c.red}Reset all state? (y/n): ${c.reset}`);
        if (confirm.toLowerCase() === 'y') { state.reset(); println(`  ${c.green}✓ State cleared.${c.reset}`); }
        break;
      case 'q':
      case 'quit':
        running = false;
        break;
      default:
        println(`  ${c.yellow}Invalid selection.${c.reset}`);
        await new Promise(r => setTimeout(r, 800));
    }
  }

  println(`\n${c.blue}${c.bold}  AIXMOS Agent Network offline. All state saved.${c.reset}\n`);
  rl.close();
}

main().catch(err => { console.error(c.red + err.message + c.reset); process.exit(1); });
