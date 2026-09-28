#!/usr/bin/env node

// ═══════════════════════════════════════════════════════
// VISION — AIXMOS QUALITY CONTROL AGENT
// Precise. Watchful. Uncompromising.
// Nothing leaves the AIXMOS system below standard.
//
// RUN: node vision.js
// ═══════════════════════════════════════════════════════

const readline = require('readline');
const { execSync } = require('child_process');
const { loadAixmosEnv } = require('./lib/env');

loadAixmosEnv();
const send  = (() => { try { return require('./send');  } catch { return null; } })();
const state = (() => { try { return require('./state'); } catch { return null; } })();

const c = {
  blue:'\x1b[34m', cyan:'\x1b[36m', green:'\x1b[32m', red:'\x1b[31m',
  yellow:'\x1b[33m', bold:'\x1b[1m', dim:'\x1b[2m', reset:'\x1b[0m',
};

const { generate } = require('./lib/llm');

// ── MODES ────────────────────────────────────────────
const MODES = [
  { id:1, key:'review_message',  label:'Review a message before sending',   icon:'✉️',  desc:'Paste any message — VISION approves, flags, or revises it' },
  { id:2, key:'audit_output',    label:'Audit agent output',                icon:'🔍',  desc:'Review what CHUMMO, MOOSE, Cap, or WW generated' },
  { id:3, key:'operator_audit',  label:'Audit operator performance',        icon:'👤',  desc:'Review an operator\'s recent work against AIXMOS standard' },
  { id:4, key:'client_situation',label:'Review a client situation',         icon:'🤝',  desc:'Is this being handled correctly? What\'s being missed?' },
  { id:5, key:'standards_check', label:'Standards check',                   icon:'⭐',  desc:'Does this meet the 5-star restaurant standard?' },
  { id:6, key:'full_audit',      label:'Full system audit',                 icon:'📊',  desc:'Review everything in state — what\'s slipping, what\'s solid' },
  { id:7, key:'communication',   label:'Communication review',              icon:'💬',  desc:'Review a full conversation or thread for tone and effectiveness' },
];

// ── SYSTEM PROMPT ────────────────────────────────────
const SYSTEM = `You are VISION — the AIXMOS quality control agent. Precise. Watchful. Uncompromising. Nothing leaves the AIXMOS system below standard.

WHAT YOU ENFORCE:
The AIXMOS 5-Star Standard — every interaction should feel like a 5-star restaurant experience. Premium. Intentional. Human. On time. No excuses.

CHUMMO VOICE (what you check messages against):
- Friend first. Warm. Direct. Never corporate.
- Opens with person's name. One CTA only. Under 160 chars for SMS.
- Never: "I'm following up" / "circle back" / "as per my last" / "hope this finds you well"
- Never opens with company name or a price.

MOOSE STANDARD:
- Action items. Numbered. Owned. Time-stamped.
- Every task has a specific owner and specific deadline.
- No vague language. "Follow up" is not an action. "Text Marcus at 3pm about the $500 payment" is.

CAPTAIN AMERICA STANDARD:
- Numbers stated exactly. No softening.
- Score given honestly.
- Wonder Woman handoff formatted correctly.

WONDER WOMAN STANDARD:
- Every message ready to send — no placeholders, no brackets.
- Tone matches the business (TMMT = professional, AIXMOS = warm, Ecom = customer-centric).
- Every flagged item has a resolution.

VISION OUTPUT FORMAT:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
VISION REVIEW — [what was reviewed]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
VERDICT: APPROVED ✅ / NEEDS REVISION ⚠️ / REJECTED ❌

ISSUES FOUND:
[numbered list — be specific, not vague]

WHAT'S STRONG:
[what actually works]

REVISED VERSION: (if needed)
[the corrected version, ready to use]

VISION SCORE: X/10

WATCH FOR:
[one thing to monitor going forward]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

VISION RULES:
- Never approve something just to be nice. Earned approval only.
- If a message would embarrass AIXMOS, reject it.
- Revised versions must be complete and ready to use — not outlines.
- Score honestly. 6/10 means something real needs fixing.
- One sentence closing: VISION has spoken.`;

// ── HELPERS ──────────────────────────────────────────
function println(t='') { console.log(t); }
function hr(ch='─',len=52) { println(`${c.dim}${ch.repeat(len)}${c.reset}`); }
function print(t) { process.stdout.write(t); }
function ask(rl,q) { return new Promise(r=>rl.question(q,a=>r(a.trim()))); }
function copyToClipboard(text) {
  try { execSync('pbcopy',{input:text}); return true; } catch {}
  try { execSync('clip',  {input:text}); return true; } catch {}
  return false;
}

function banner() {
  println();
  println(`${c.cyan}${c.bold}  ╔══════════════════════════════════════╗${c.reset}`);
  println(`${c.cyan}${c.bold}  ║  AIXMOS · VISION                     ║${c.reset}`);
  println(`${c.cyan}${c.bold}  ║  Quality Control Agent               ║${c.reset}`);
  println(`${c.cyan}${c.bold}  ╚══════════════════════════════════════╝${c.reset}`);
  println(`  ${c.dim}Precise. Watchful. Uncompromising.${c.reset}`);
  println(`  ${c.dim}Nothing leaves below standard.${c.reset}`);
  println();
}

async function collectInputs(rl, mode) {
  const inputs = {};
  println(); hr();
  switch(mode.key) {
    case 'review_message':
      println(`${c.bold}  REVIEW MESSAGE${c.reset}`); hr();
      println(`  ${c.dim}Paste the full message — VISION checks it against AIXMOS standards${c.reset}`); println();
      inputs.message  = await ask(rl,`  ${c.cyan}Paste the message: ${c.reset}`);
      inputs.type     = await ask(rl,`  ${c.cyan}Message type (sms/email/whatsapp): ${c.reset}`);
      inputs.business = await ask(rl,`  ${c.cyan}Business (tmmt/aixmos/ecom): ${c.reset}`);
      inputs.purpose  = await ask(rl,`  ${c.cyan}What is this message trying to achieve: ${c.reset}`);
      break;
    case 'audit_output':
      println(`${c.bold}  AUDIT AGENT OUTPUT${c.reset}`); hr();
      inputs.agent    = await ask(rl,`  ${c.cyan}Which agent (chummo/moose/cap/ww): ${c.reset}`);
      inputs.output   = await ask(rl,`  ${c.cyan}Paste the agent output: ${c.reset}`);
      inputs.context  = await ask(rl,`  ${c.cyan}What situation was this for: ${c.reset}`);
      break;
    case 'operator_audit':
      println(`${c.bold}  OPERATOR AUDIT${c.reset}`); hr();
      inputs.operator = await ask(rl,`  ${c.cyan}Operator name: ${c.reset}`);
      inputs.actions  = await ask(rl,`  ${c.cyan}What they did this week: ${c.reset}`);
      inputs.clients  = await ask(rl,`  ${c.cyan}Clients assigned to them: ${c.reset}`);
      inputs.issues   = await ask(rl,`  ${c.cyan}Any complaints or flags: ${c.reset}`);
      break;
    case 'client_situation':
      println(`${c.bold}  CLIENT SITUATION REVIEW${c.reset}`); hr();
      inputs.client   = await ask(rl,`  ${c.cyan}Client name + tier: ${c.reset}`);
      inputs.situation= await ask(rl,`  ${c.cyan}What is happening: ${c.reset}`);
      inputs.actions  = await ask(rl,`  ${c.cyan}What has been done so far: ${c.reset}`);
      inputs.concern  = await ask(rl,`  ${c.cyan}What concerns you about this: ${c.reset}`);
      break;
    case 'standards_check':
      println(`${c.bold}  5-STAR STANDARDS CHECK${c.reset}`); hr();
      inputs.what     = await ask(rl,`  ${c.cyan}What are you checking (message/process/output): ${c.reset}`);
      inputs.content  = await ask(rl,`  ${c.cyan}Paste the content: ${c.reset}`);
      inputs.business = await ask(rl,`  ${c.cyan}Business context: ${c.reset}`);
      break;
    case 'full_audit':
      println(`${c.bold}  FULL SYSTEM AUDIT${c.reset}`); hr();
      if (state) {
        const s = state.getSummary();
        inputs.state_summary = JSON.stringify(s, null, 2);
        println(`  ${c.dim}State loaded automatically.${c.reset}`);
      }
      inputs.period   = await ask(rl,`  ${c.cyan}Period to audit (today/this week): ${c.reset}`);
      inputs.concerns = await ask(rl,`  ${c.cyan}Specific concerns to investigate: ${c.reset}`);
      break;
    case 'communication':
      println(`${c.bold}  COMMUNICATION REVIEW${c.reset}`); hr();
      inputs.thread   = await ask(rl,`  ${c.cyan}Paste the conversation thread: ${c.reset}`);
      inputs.business = await ask(rl,`  ${c.cyan}Business context: ${c.reset}`);
      inputs.goal     = await ask(rl,`  ${c.cyan}What was trying to be achieved: ${c.reset}`);
      break;
  }
  return inputs;
}

function buildPrompt(mode, inputs) {
  const lines = [`VISION MODE: ${mode.label.toUpperCase()}\n`];
  Object.entries(inputs).forEach(([k,v]) => { if(v) lines.push(`${k.replace(/_/g,' ').toUpperCase()}: ${v}`); });
  lines.push(`\nRun the VISION review now. Use your exact output format. Be honest.`);
  return lines.join('\n');
}

async function main() {
  banner();
  try { require('./lib/env').requireLLMBackend(); }
  catch (e) { println(`${c.red}${e.message}${c.reset}\n`); process.exit(1); }
  const rl = readline.createInterface({ input:process.stdin, output:process.stdout });
  let running = true;
  while(running) {
    hr('═');
    println(`${c.bold}  VISION MODES${c.reset}`); hr('═');
    MODES.forEach(m => {
      println(`  ${c.cyan}${m.id}.${c.reset} ${m.icon}  ${c.bold}${m.label}${c.reset}`);
      println(`      ${c.dim}${m.desc}${c.reset}`);
    });
    println();
    const pick = await ask(rl,`${c.cyan}Pick mode (1–7): ${c.reset}`);
    const mode = MODES.find(m=>m.id===parseInt(pick));
    if(!mode) { println(`${c.yellow}Invalid.${c.reset}\n`); continue; }
    const inputs = await collectInputs(rl, mode);
    println(); print(`  ${c.cyan}VISION is reviewing${c.reset}`);
    const dots = setInterval(()=>print(`${c.cyan}.${c.reset}`),350);
    let output='';
    try {
      output = await generate({ system: SYSTEM, prompt: buildPrompt(mode,inputs), maxTokens: 2000 });
    } catch(err) { clearInterval(dots); println(`\n${c.red}Error: ${err.message}${c.reset}\n`); continue; }
    clearInterval(dots); println('\n');
    hr('═'); println(`${c.cyan}${c.bold}  ${mode.icon}  VISION — ${mode.label.toUpperCase()}${c.reset}`); hr('═');
    println(); println(output); println(); hr('═');
    const copied = copyToClipboard(output);
    if(copied) println(`  ${c.green}✓ Copied to clipboard${c.reset}`);
    if(send) await send.prompt(rl, output);
    if(state) state.updateAgent && state.updateAgent('vision', { last_mode:mode.key, last_output:output.substring(0,500) });
    println();
    const next = await ask(rl,`${c.cyan}Another review? (y/n): ${c.reset}`);
    if(next.toLowerCase()!=='y') running=false;
    println();
  }
  println(`${c.cyan}${c.bold}  VISION signing off. Standard maintained.${c.reset}\n`);
  rl.close();
}
main().catch(err=>{console.error(c.red+err.message+c.reset); process.exit(1);});
