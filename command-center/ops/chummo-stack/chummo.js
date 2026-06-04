#!/usr/bin/env node

// ═══════════════════════════════════════════════════════
// CHUMMO — AIXMOS MESSAGING AGENT (TERMINAL VERSION)
// Runs directly in your Mac terminal.
//
// SETUP (run once):
//   npm install @anthropic-ai/sdk
//   export ANTHROPIC_API_KEY=your_key_here
//   node chummo.js
//
// Or add to your shell profile for permanent key:
//   echo 'export ANTHROPIC_API_KEY=your_key_here' >> ~/.zshrc
//   source ~/.zshrc
// ═══════════════════════════════════════════════════════

const readline = require('readline');
const path = require('path');
const { execSync } = require('child_process');
const { ask, copyToClipboard, saveAgentContext } = require('../files/shared-utils');

// ── COLORS FOR TERMINAL ──────────────────────────────
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
};

const { chatCompletion, requireAiAvailable } = require('../files/llm-client');

// ── MESSAGE TYPES ────────────────────────────────────
const MESSAGE_TYPES = [
  { id: 1,  label: 'First outreach — SMS',           key: 'first_sms' },
  { id: 2,  label: 'First outreach — Email',         key: 'first_email' },
  { id: 3,  label: 'Follow-up — SMS',                key: 'followup_sms' },
  { id: 4,  label: 'Post-call recap — Email',        key: 'postcall_email' },
  { id: 5,  label: 'Payment reminder — SMS',         key: 'payment_sms' },
  { id: 6,  label: 'Upgrade conversation — Email',   key: 'upgrade_email' },
  { id: 7,  label: 'Re-engagement — SMS',            key: 'reengage_sms' },
  { id: 8,  label: 'Referral ask — SMS',             key: 'referral_sms' },
  { id: 9,  label: 'Welcome — after payment',        key: 'welcome_msg' },
  { id: 10, label: 'Operator invite — Email',        key: 'operator_invite' },
];

// ── CHUMMO SYSTEM PROMPT ─────────────────────────────
const SYSTEM = `You are CHUMMO — the AIXMOS messaging agent. You write outreach messages, emails, and follow-ups on behalf of AIXMOS operators and Muhammad Taha, the founder.

ABOUT AIXMOS:
- Workforce infrastructure company for everyday people
- Mission: Help people access the American Dream through systems, automation, and operational infrastructure
- Founder: Muhammad Taha — immigrant, came to America at 6, built car rental ops to $90-100K/month, was betrayed, rebuilt, touched $1M+ in operations
- Tagline: For the people. By the people.
- Target: $10,000/month for every client
- Standard: 5-star restaurant — every interaction is premium

SERVICES: $97/month Membership, $397 LLC Formation, $500-$1K Credit Guidance, $3,750 Base Infrastructure, $7,500 Enterprise Systems, $15,000 Car Rental in a Box, $25,000 E-Commerce Ecosystem, $50,000 Full Ecosystem.

CHUMMO VOICE — NON-NEGOTIABLE:
- Friend first. Always. Before any pitch.
- Warm, direct, human — never corporate or scripted-sounding
- Short sentences. Easy to read on a phone.
- Never say: "I'm following up" / "As per my last" / "I wanted to circle back" / "Hope this finds you well"
- Never open with the company name or a price
- Always open with the person's name and something human
- Lead with empathy, not features
- One clear call to action per message — never two
- SMS: under 160 characters when possible, always conversational
- Email: short paragraphs, no corporate jargon

OUTPUT FORMAT:
- Write ONLY the message — no explanation, no preamble, no "here's a draft"
- Email: Subject line first, blank line, then body
- SMS: just the text
- Keep it human. Keep it real.`;

// ── HELPERS ──────────────────────────────────────────
function print(text) { process.stdout.write(text); }
function println(text = '') { console.log(text); }
function hr() { println(`${c.dim}${'─'.repeat(52)}${c.reset}`); }

// ── BANNER ───────────────────────────────────────────
function banner() {
  println();
  println(`${c.blue}${c.bold}  ╔═══════════════════════════════╗${c.reset}`);
  println(`${c.blue}${c.bold}  ║  AIXMOS · CHUMMO AGENT        ║${c.reset}`);
  println(`${c.blue}${c.bold}  ║  Messaging. Powered by AI.    ║${c.reset}`);
  println(`${c.blue}${c.bold}  ╚═══════════════════════════════╝${c.reset}`);
  println(`  ${c.dim}Friend first. Always.${c.reset}`);
  println();
}

function ensureInteractiveTerminal() {
  if (process.stdin.isTTY) return;

  const dir = __dirname;
  const env = `export AI_PROVIDER=${process.env.AI_PROVIDER || 'auto'} OLLAMA_BASE_URL=${process.env.OLLAMA_BASE_URL || 'http://127.0.0.1:11434'}`;
  const runCmd = `cd ${JSON.stringify(dir)} && ${env} && node chummo.js`;

  println(
    `${c.yellow}CHUMMO needs an interactive terminal — Cursor agent shells cannot accept input.${c.reset}`
  );

  if (process.platform === 'darwin') {
    try {
      const escaped = runCmd.replace(/\\/g, '\\\\').replace(/"/g, '\\"');
      execSync(
        `osascript -e 'tell application "Terminal" to activate' -e 'tell application "Terminal" to do script "${escaped}"'`,
        { stdio: 'ignore' }
      );
      println(`${c.green}Opened CHUMMO in macOS Terminal. Use that window.${c.reset}\n`);
    } catch {
      println(`${c.cyan}Run in Cursor: Terminal → New Terminal, then:${c.reset}`);
      println(`  ${runCmd}\n`);
    }
  } else {
    println(`${c.cyan}Run:${c.reset}\n  ${runCmd}\n`);
  }
  process.exit(0);
}

// ── MAIN ─────────────────────────────────────────────
async function main() {
  ensureInteractiveTerminal();
  banner();

  const ai = await requireAiAvailable();
  const prov = ai.status.active;
  const modelLabel = prov === 'ollama' ? ai.status.ollamaModel : 'claude (cloud)';
  println(`  ${c.green}AI:${c.reset} ${prov} · ${modelLabel}\n`);

  const rl = readline.createInterface({
    input: process.stdin,
    output: process.stdout,
  });

  let running = true;

  while (running) {
    hr();
    println(`${c.bold}LEAD INFO${c.reset}`);
    hr();

    // Collect lead info
    const name = await ask(rl, `${c.cyan}First name: ${c.reset}`);
    if (!name) { println(`${c.yellow}Name is required.${c.reset}\n`); continue; }

    const situation = await ask(rl, `${c.cyan}Their situation (optional): ${c.reset}`, true);
    const urgency   = await ask(rl, `${c.cyan}Urgency — 1=Critical 2=Warm 3=Cold (optional): ${c.reset}`, true);
    const tier      = await ask(rl, `${c.cyan}Service interest (optional, e.g. Membership $97/mo): ${c.reset}`, true);
    const stage     = await ask(rl, `${c.cyan}Pipeline stage (optional, e.g. New lead): ${c.reset}`, true);
    const extra     = await ask(rl, `${c.cyan}Extra context (optional): ${c.reset}`, true);

    // Map urgency number to text
    const urgencyMap = { '1': 'Critical — needs to move now', '2': 'Warm — within 30 days', '3': 'Cold — just researching' };
    const urgencyText = urgencyMap[urgency] || urgency;

    // Pick message type
    println();
    hr();
    println(`${c.bold}MESSAGE TYPE${c.reset}`);
    hr();
    MESSAGE_TYPES.forEach(m => println(`  ${c.blue}${m.id.toString().padStart(2)}.${c.reset} ${m.label}`));
    println();

    const typeInput = await ask(rl, `${c.cyan}Pick a number (1–10): ${c.reset}`);
    const typeNum   = parseInt(typeInput);
    const msgType   = MESSAGE_TYPES.find(m => m.id === typeNum);

    if (!msgType) {
      println(`${c.yellow}Invalid selection.${c.reset}\n`);
      continue;
    }

    // Build prompt
    const userMsg = `Write a ${msgType.label} message for this lead:
NAME: ${name}
SITUATION: ${situation || 'Not provided'}
URGENCY: ${urgencyText || 'Not provided'}
SERVICE INTEREST: ${tier || 'Not sure yet'}
PIPELINE STAGE: ${stage || 'Not provided'}
EXTRA CONTEXT: ${extra || 'None'}
Write the message now. CHUMMO voice only.`;

    // Call API
    println();
    print(`${c.dim}CHUMMO is writing${c.reset}`);
    const dots = setInterval(() => print(`${c.dim}.${c.reset}`), 400);

    let message = '';
    try {
      const response = await chatCompletion({
        system: SYSTEM,
        userMessage: userMsg,
        maxTokens: 1000,
      });
      message = response.text;
    } catch (err) {
      clearInterval(dots);
      println(`\n${c.red}API error: ${err.message}${c.reset}\n`);
      continue;
    }

    clearInterval(dots);
    println('\n');
    hr();
    println(`${c.blue}${c.bold}  ${msgType.label.toUpperCase()}${c.reset}`);
    hr();
    println();
    println(message);
    println();
    hr();

    // Copy to clipboard
    const copied = copyToClipboard(message);
    if (copied) {
      println(`${c.green}✓ Copied to clipboard${c.reset}`);
    }

    saveAgentContext('CHUMMO', {
      type: msgType.key,
      label: msgType.label,
      lead: name,
      situation,
      urgency: urgencyText,
      tier,
      stage,
      extra,
      message,
    });
    println(`${c.green}✓ Saved CHUMMO context for MOOSE${c.reset}`);

    // What next
    println();
    const next = await ask(rl, `${c.cyan}Generate another? (y/n): ${c.reset}`);
    if (next.toLowerCase() !== 'y') {
      running = false;
    }
    println();
  }

  println(`${c.blue}${c.bold}CHUMMO signing off. Go get those leads.${c.reset}\n`);
  rl.close();
}

main().catch(err => {
  console.error(`${c.red}Fatal error:${c.reset}`, err.message);
  process.exit(1);
});
