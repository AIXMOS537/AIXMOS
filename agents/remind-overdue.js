#!/usr/bin/env node
/**
 * remind-overdue.js — text every overdue customer a payment reminder,
 * routed through the multi-channel sender (GHL → Quo → iPhone).
 *
 *   node remind-overdue.js                 DRY RUN — prints who/what, sends nothing
 *   node remind-overdue.js --send          actually send (max 1 SMS per phone per day)
 *   node remind-overdue.js --channel ghl   force a channel
 *   node remind-overdue.js --only +1555..  just this one number (for a canary test)
 *   node remind-overdue.js --limit 5       cap how many
 *   node remind-overdue.js --force         bypass today's dedupe guard
 *
 * Holds anyone missing a phone or amount (e.g. Maquela Bell — no amount on file).
 */

const { loadAixmosEnv } = require('./lib/env');
loadAixmosEnv();
const { fetchOverdueAlerts } = require('./lib/supabase-ops');
const { sendMessage, toE164 } = require('./lib/sender');
const state = require('./state');

function arg(name, def) {
  const i = process.argv.indexOf(`--${name}`);
  return i >= 0 && process.argv[i + 1] && !process.argv[i + 1].startsWith('--') ? process.argv[i + 1] : def;
}
const flag = n => process.argv.includes(`--${n}`);

function firstName(f) { return String(f || '').trim().split(/\s+/)[0] || 'there'; }
function renderAmount(amt, name) {
  if (/^reeneshia/i.test(name || '')) return '$1,854 (plus a $534 prior balance)';
  const s = String(amt == null ? '' : amt).trim();
  if (!s) return null;
  const n = parseFloat(s.replace(/[^0-9.]/g, ''));
  if (!isFinite(n)) return null;
  return '$' + n.toFixed(2).replace(/\.00$/, '');
}
function message(name, amount) {
  return `Hi ${firstName(name)}, this is TMMT (Trap Money Moves). Our records show a past-due balance of ${amount} on your rental. Please reply here or give us a call to take care of it or set up a payment plan — happy to work with you. Reply STOP to opt out.`;
}

async function main() {
  const doSend = flag('send');
  const force = flag('force');
  const channel = arg('channel');
  const route = arg('route', 'alert'); // reminders default to the alert route (GHL)
  const only = arg('only') ? toE164(arg('only')) : null;
  const limit = parseInt(arg('limit') || '0', 10);
  const today = state.reminderDayKey();

  const pays = (await fetchOverdueAlerts()).filter(x => x.type === 'payment_overdue');
  let targets = [], held = [], skipped = [];
  for (const p of pays) {
    const amount = renderAmount(p.amount, p.customer);
    const phone = toE164(p.phone);
    if (!amount || !phone) { held.push(`${p.customer} (phone=${p.phone || 'none'}, amount=${p.amount || 'none'})`); continue; }
    if (only && phone !== only) continue;
    if (!force && state.wasRemindedToday(phone, today)) {
      skipped.push(`${p.customer} (${phone})`);
      continue;
    }
    targets.push({ name: p.customer, phone, text: message(p.customer, amount) });
  }
  if (limit > 0) targets = targets.slice(0, limit);

  console.log(`\n${doSend ? 'SENDING' : 'DRY RUN'} — ${targets.length} reminder(s)` +
    (channel ? ` via ${channel}` : ` (route: ${route})`) + (only ? ` [only ${only}]` : ''));
  if (!force) console.log(`Dedupe: max 1 automated reminder per phone per day (${today})`);
  if (skipped.length) console.log(`Already reminded today (${skipped.length}): ${skipped.join('; ')}`);
  console.log('-'.repeat(64));

  const results = { sent: 0, failed: 0, skipped: skipped.length };
  for (const t of targets) {
    if (!doSend) { console.log(`  [dry] ${t.phone}  ${t.name}`); continue; }
    if (!force && state.wasRemindedToday(t.phone, today)) {
      results.skipped += 1;
      console.log(`  SKIP  ${t.phone}  ${t.name}  — already reminded today`);
      continue;
    }
    const r = await sendMessage({ to: t.phone, text: t.text, channel, route });
    if (r.ok) {
      results.sent += 1;
      state.recordReminder(t.phone, { name: t.name, channel: r.channel, id: r.id || '' });
      console.log(`  SENT  ${t.phone}  ${t.name}  (via ${r.channel}, ${r.id})`);
    } else {
      results.failed += 1;
      console.log(`  FAIL  ${t.phone}  ${t.name}  — ${r.error}`);
      if (r.attempts?.length) console.log('        ' + JSON.stringify(r.attempts));
    }
  }

  console.log('-'.repeat(64));
  if (doSend) {
    console.log(`Done. sent=${results.sent} failed=${results.failed} skipped=${results.skipped}`);
  } else {
    console.log(`Dry run only. Re-run with --send to actually text these ${targets.length}.`);
    if (skipped.length) console.log(`(${skipped.length} would be skipped — already reminded today)`);
  }
  if (held.length) console.log(`Held (${held.length}): ${held.join('; ')}`);
}

main().catch(e => { console.error('ERROR:', e.message); process.exit(1); });
