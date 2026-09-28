#!/usr/bin/env node

// ═══════════════════════════════════════════════════════
// AIXMOS SCHEDULER
// Auto-runs agents on a schedule.
// Runs in the background — keep this terminal open
// or set it up as a system service (see install scripts).
//
// DEFAULT SCHEDULE:
//   7:00 AM  — Morning brief generated + sent
//   9:00 AM  — Reminder: check hot leads
//   6:00 PM  — End of day summary
//
// CONFIGURE: Edit SCHEDULE below, or set in config.json
//
// RUN: node scheduler.js
// ═══════════════════════════════════════════════════════

const fs = require('fs');
const path = require('path');

const c = {
  blue:'\x1b[34m',green:'\x1b[32m',yellow:'\x1b[33m',
  bold:'\x1b[1m',dim:'\x1b[2m',reset:'\x1b[0m',cyan:'\x1b[36m',
};

// ── LOAD CONFIG ───────────────────────────────────────
function loadConfig() {
  try {
    const f = path.join(__dirname,'config.json');
    if(fs.existsSync(f)) return JSON.parse(fs.readFileSync(f,'utf8'));
  } catch {}
  return {};
}

// ── LOAD MODULES ─────────────────────────────────────
const briefing = (() => { try { return require('./briefing'); } catch { return null; } })();
const send     = (() => { try { return require('./send');     } catch { return null; } })();
const state    = (() => { try { return require('./state');    } catch { return null; } })();

// ── SCHEDULE (24-hour format) ─────────────────────────
const SCHEDULE = [
  { hour: 7,  minute: 0,  job: 'morning_brief',   label: '🌅 Morning Brief' },
  { hour: 9,  minute: 0,  job: 'hot_leads',        label: '🔥 Hot Leads Reminder' },
  { hour: 18, minute: 0,  job: 'eod_summary',      label: '🌙 End of Day Summary' },
];

// ── LOG ───────────────────────────────────────────────
const LOG_FILE = path.join(__dirname,'scheduler.log');
function log(msg) {
  const line = `[${new Date().toISOString()}] ${msg}\n`;
  console.log(`  ${c.dim}${line.trim()}${c.reset}`);
  try { fs.appendFileSync(LOG_FILE, line); } catch {}
}

// ── JOBS ─────────────────────────────────────────────
async function runMorningBrief() {
  log('Running morning brief...');
  if (!briefing) { log('briefing.js not found'); return; }
  try { require('./lib/env').requireLLMBackend(); }
  catch (e) { log(`Skipping brief: ${e.message}`); return; }
  try {
    const brief = await briefing.generate(true); // silent=true
    if (!brief) return;
    log('Brief generated.');

    // Send via configured platforms
    const config = loadConfig();
    if (send && config.telegram?.enabled && config.telegram?.bot_token) {
      // Get saved recipients from config
      const recipients = config.scheduler?.morning_brief_recipients || [];
      for (const chatId of recipients) {
        try {
          // Direct telegram call
          const res = await fetch(`https://api.telegram.org/bot${config.telegram.bot_token}/sendMessage`, {
            method:'POST',
            headers:{'Content-Type':'application/json'},
            body: JSON.stringify({ chat_id: chatId, text: brief })
          });
          const data = await res.json();
          if(data.ok) log(`Brief sent to Telegram chat ${chatId}`);
          else log(`Telegram error: ${data.description}`);
        } catch(e) { log(`Send error: ${e.message}`); }
      }
    }
    // Save to state
    if(state) {
      const s = state.load();
      s.last_brief = { generated: new Date().toISOString(), content: brief.substring(0,500) };
      state.save(s);
    }
    log('Morning brief complete.');
  } catch(err) { log(`Morning brief error: ${err.message}`); }
}

async function runHotLeadsReminder() {
  log('Hot leads reminder...');
  const contacts = (() => { try { return require('./contacts'); } catch { return null; } })();
  if (!contacts) return;
  const hot = contacts.list().filter(c =>
    c.stage?.toLowerCase().includes('hot') ||
    c.urgency?.toLowerCase().includes('critical')
  );
  if (hot.length === 0) { log('No hot leads found.'); return; }
  const msg = `🔥 HOT LEADS CHECK — ${new Date().toLocaleTimeString()}\n\n${
    hot.map((c,i)=>`${i+1}. ${c.name} — ${c.business||''} — ${c.tier||''}\n   Stage: ${c.stage||'—'}\n   ${c.situation||''}`).join('\n\n')
  }\n\nThese need contact TODAY.`;
  log(`${hot.length} hot leads flagged.`);
  const config = loadConfig();
  if (config.telegram?.enabled && config.telegram?.bot_token) {
    const recipients = config.scheduler?.morning_brief_recipients || [];
    for (const chatId of recipients) {
      try {
        await fetch(`https://api.telegram.org/bot${config.telegram.bot_token}/sendMessage`,{
          method:'POST', headers:{'Content-Type':'application/json'},
          body:JSON.stringify({chat_id:chatId,text:msg})
        });
      } catch {}
    }
  }
}

async function runEODSummary() {
  log('Running end of day summary...');
  if (!state) return;
  const s = state.getSummary();
  const msg = `🌙 AIXMOS EOD SUMMARY — ${new Date().toLocaleDateString()}\n\n` +
    `Agent runs today: ${s.total_runs}\n` +
    `Active handoffs: ${s.active_handoffs?.length || 0}\n` +
    `Flagged payments: ${s.flagged_payments?.length || 0}\n` +
    `Cap's score: ${s.captain_score}\n\n` +
    `Last CHUMMO: ${s.chummo_last} (${s.chummo_lead})\n` +
    `Last MOOSE: ${s.moose_last}\n\n` +
    `Tomorrow: run morning brief at 7am.`;
  const config = loadConfig();
  if (config.telegram?.enabled && config.telegram?.bot_token) {
    const recipients = config.scheduler?.morning_brief_recipients || [];
    for (const chatId of recipients) {
      try {
        await fetch(`https://api.telegram.org/bot${config.telegram.bot_token}/sendMessage`,{
          method:'POST', headers:{'Content-Type':'application/json'},
          body:JSON.stringify({chat_id:chatId,text:msg})
        });
      } catch {}
    }
  }
  log('EOD summary complete.');
}

// ── JOB RUNNER ────────────────────────────────────────
async function runJob(job) {
  switch(job) {
    case 'morning_brief': await runMorningBrief(); break;
    case 'hot_leads':     await runHotLeadsReminder(); break;
    case 'eod_summary':   await runEODSummary(); break;
  }
}

// ── SCHEDULER LOOP ────────────────────────────────────
function getNextRun(hour, minute) {
  const now  = new Date();
  const next = new Date();
  next.setHours(hour, minute, 0, 0);
  if (next <= now) next.setDate(next.getDate() + 1);
  return next;
}

function scheduleAll() {
  SCHEDULE.forEach(item => {
    const next = getNextRun(item.hour, item.minute);
    const delay = next - Date.now();
    console.log(`  ${c.green}✓${c.reset} ${item.label} scheduled for ${next.toLocaleTimeString()} (in ${Math.round(delay/60000)}m)`);
    setTimeout(async () => {
      log(`Running job: ${item.job}`);
      await runJob(item.job);
      // Reschedule for tomorrow
      setInterval(() => { log(`Running job: ${item.job}`); runJob(item.job); }, 86400000);
    }, delay);
  });
}

// ── MAIN ─────────────────────────────────────────────
async function main() {
  console.log();
  console.log(`${c.blue}${c.bold}  ╔══════════════════════════════════════╗${c.reset}`);
  console.log(`${c.blue}${c.bold}  ║  AIXMOS SCHEDULER — RUNNING          ║${c.reset}`);
  console.log(`${c.blue}${c.bold}  ╚══════════════════════════════════════╝${c.reset}`);
  console.log(`  ${c.dim}Keep this terminal open to maintain schedule.${c.reset}`);
  console.log();

  const config = loadConfig();
  const recipients = config.scheduler?.morning_brief_recipients;
  if (!recipients || recipients.length === 0) {
    console.log(`  ${c.yellow}⚠ No Telegram recipients configured.${c.reset}`);
    console.log(`  ${c.dim}Add to config.json: scheduler.morning_brief_recipients: ["your_chat_id"]${c.reset}`);
  }

  console.log();
  scheduleAll();
  console.log();
  console.log(`  ${c.dim}Scheduler active. Press Ctrl+C to stop.${c.reset}`);
  console.log();

  // Keep alive
  setInterval(() => {}, 60000);

  // Handle Ctrl+C
  process.on('SIGINT', () => {
    console.log(`\n${c.blue}${c.bold}  Scheduler stopped.${c.reset}\n`);
    process.exit(0);
  });
}

if(require.main===module) main().catch(console.error);
module.exports = { runJob, scheduleAll };
