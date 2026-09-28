#!/usr/bin/env node

// ═══════════════════════════════════════════════════════
// AIXMOS DAILY BRIEFING
// Muhammad's morning brief — auto-generated.
// Combines state, contacts, and AI analysis.
//
// RUN MANUALLY:  node briefing.js
// AUTO-SCHEDULED: set in scheduler.js
// ═══════════════════════════════════════════════════════

const { loadAixmosEnv } = require('./lib/env');

loadAixmosEnv();

const state    = (() => { try { return require('./state');    } catch { return null; } })();
const contacts = (() => { try { return require('./contacts'); } catch { return null; } })();
const send     = (() => { try { return require('./send');     } catch { return null; } })();
const { execSync } = require('child_process');

const c = {
  blue:'\x1b[34m',cyan:'\x1b[36m',green:'\x1b[32m',yellow:'\x1b[33m',
  red:'\x1b[31m',bold:'\x1b[1m',dim:'\x1b[2m',reset:'\x1b[0m',
};

const { generate: llmGenerate } = require('./lib/llm');

function println(t='') { console.log(t); }
function hr(ch='─',len=52) { println(`${c.dim}${ch.repeat(len)}${c.reset}`); }
function copyToClipboard(text) {
  try { execSync('pbcopy',{input:text}); return true; } catch {}
  try { execSync('clip',  {input:text}); return true; } catch {}
  return false;
}

function today() {
  return new Date().toLocaleDateString('en-US',{weekday:'long',month:'long',day:'numeric',year:'numeric'});
}

function buildBriefingData() {
  const data = { date: today(), time: new Date().toLocaleTimeString('en-US',{hour:'2-digit',minute:'2-digit'}) };

  if (state) {
    const s = state.getSummary();
    data.active_handoffs    = s.active_handoffs?.length || 0;
    data.flagged_payments   = s.flagged_payments?.length || 0;
    data.flagged_payment_list = s.flagged_payments?.slice(0,5).map(p=>`${p.name} — ${p.amount} — ${p.daysLate}d`).join(', ') || 'None';
    data.handoff_list       = s.active_handoffs?.slice(0,5).map(h=>`${h.from}→${h.to}: ${h.label}`).join(' | ') || 'None';
    data.cap_score          = s.captain_score || 'Not run yet';
    data.cap_last           = s.captain_last || 'Never';
    data.total_runs         = s.total_runs || 0;
    data.chummo_last_lead   = s.chummo_lead || '—';
  }

  if (contacts) {
    const all = contacts.list();
    data.total_contacts = all.length;
    const now = Date.now();
    const overdue = all.filter(c => {
      if (!c.last_contact) return true;
      const days = Math.floor((now - new Date(c.last_contact)) / 86400000);
      return days >= 7;
    });
    data.contacts_overdue = overdue.length;
    data.overdue_list = overdue.slice(0,5).map(c=>`${c.name} (${c.business||''}, ${c.stage||''})`).join(', ') || 'None';
    const hot = all.filter(c => c.stage?.toLowerCase().includes('hot') || c.urgency?.toLowerCase().includes('critical'));
    data.hot_leads = hot.length;
    data.hot_list  = hot.slice(0,3).map(c=>c.name).join(', ') || 'None';
  }

  return data;
}

const BRIEF_SYSTEM = `You are generating Muhammad Taha's morning brief for AIXMOS.

Muhammad is the founder of AIXMOS — a workforce infrastructure company. He manages three businesses: TMMT Auto Services, AIXMOS Platform (100+ person pipeline, $97/month members), and Ecommerce.

His organization: 3 overseas executives, an operator network, and 4 AI agents (CHUMMO, MOOSE, VISION, CAP, Wonder Woman).

Generate his morning brief in this exact format:

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
AIXMOS MORNING BRIEF — [DATE]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🌅 GOOD MORNING, MUHAMMAD.

📊 PIPELINE AT A GLANCE
[3-4 lines: key numbers, what's moving, what isn't]

🚨 NEEDS YOUR ATTENTION TODAY
[numbered list — only real priorities, max 5]

💳 PAYMENTS
[overdue payment summary]

📞 CONTACTS GOING COLD
[who hasn't been reached in 7+ days]

⚡ ACTIVE HANDOFFS
[what agents have flagged for each other]

🛡️ CAP'S LAST SCORE: [score]

🎯 TODAY'S 3 NON-NEGOTIABLES
1. [most important action]
2. [second most important]
3. [third]

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Let's go. — MOOSE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Keep it sharp. No fluff. Under 300 words. This is what Muhammad reads in 60 seconds before his day starts.`;

async function generate(silent = false) {
  try { require('./lib/env').requireLLMBackend(); }
  catch (e) { println(`${c.red}${e.message}${c.reset}`); return null; }

  if (!silent) {
    println();
    println(`${c.blue}${c.bold}  AIXMOS DAILY BRIEFING${c.reset}`);
    println(`  ${c.dim}${today()}${c.reset}`);
    println();
  }

  const data = buildBriefingData();
  const prompt = `Generate Muhammad's morning brief using this data:\n\n${
    Object.entries(data).map(([k,v])=>`${k.toUpperCase()}: ${v}`).join('\n')
  }\n\nGenerate the brief now.`;

  if (!silent) process.stdout.write(`  ${c.blue}Generating brief${c.reset}`);
  const dots = silent ? null : setInterval(()=>process.stdout.write(`${c.blue}.${c.reset}`),400);

  let brief = '';
  try {
    brief = await llmGenerate({ system: BRIEF_SYSTEM, prompt, maxTokens: 1000 });
  } catch(err) {
    if(dots) clearInterval(dots);
    println(`\n${c.red}Error: ${err.message}${c.reset}`);
    return null;
  }

  if(dots) { clearInterval(dots); println(); }
  return brief;
}

async function main() {
  const readline = require('readline');
  const rl = readline.createInterface({input:process.stdin,output:process.stdout});
  const ask = (q) => new Promise(r=>rl.question(q,a=>r(a.trim())));

  const brief = await generate();
  if (!brief) { rl.close(); return; }

  println();
  hr('═');
  println(brief);
  hr('═');
  println();

  const copied = copyToClipboard(brief);
  if(copied) println(`  ${c.green}✓ Copied to clipboard${c.reset}`);

  if(send) await send.prompt(rl, brief);

  // Save to state
  if(state) {
    const s = state.load();
    s.last_brief = { generated: new Date().toISOString(), content: brief.substring(0,800) };
    state.save(s);
  }

  println();
  rl.close();
}

if(require.main === module) main().catch(console.error);
module.exports = { generate, buildBriefingData };
