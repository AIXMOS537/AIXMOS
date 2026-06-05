#!/usr/bin/env node
/**
 * Retry payment reminders that failed on the last bulk run.
 * Uses customer route (iMessage then GHL) and prints detailed errors.
 */
const { loadAixmosEnv } = require('./lib/env');
loadAixmosEnv();

const { fetchOverdueAlerts } = require('./lib/supabase-ops');
const { sendMessage, toE164 } = require('./lib/sender');
const state = require('./state');

const FAILED_PHONES = [
  '+10000000000', // [customer]
  '+10000000000', // [customer]
  '+10000000000', // [customer]
  '+10000000000', // [customer]
  '+10000000000', // [customer]
  '+10000000000', // [customer]
];

function firstName(f) { return String(f || '').trim().split(/\s+/)[0] || 'there'; }
function renderAmount(amt, name) {
  if (/^[customer]/i.test(name || '')) return '[amount redacted]';
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
  const doSend = process.argv.includes('--send');
  const force = process.argv.includes('--force');
  const today = state.reminderDayKey();
  const pays = (await fetchOverdueAlerts()).filter(x => x.type === 'payment_overdue');
  const byPhone = new Map();
  for (const p of pays) {
    const phone = toE164(p.phone);
    if (phone) byPhone.set(phone, p);
  }

  console.log(`\n${doSend ? 'RETRY SEND' : 'DRY RUN'} — ${FAILED_PHONES.length} failed numbers\n`);
  let sent = 0, failed = 0;

  for (const phone of FAILED_PHONES) {
    const row = byPhone.get(phone);
    if (!row) {
      console.log(`  SKIP  ${phone} — not in overdue list`);
      continue;
    }
    const amount = renderAmount(row.amount, row.customer);
    if (!amount) {
      console.log(`  HOLD  ${phone}  ${row.customer} — no amount`);
      continue;
    }
    const text = message(row.customer, amount);
    if (!doSend) {
      console.log(`  [dry] ${phone}  ${row.customer}`);
      continue;
    }
    if (!force && state.wasRemindedToday(phone, today)) {
      console.log(`  SKIP  ${phone}  ${row.customer}  — already reminded today`);
      continue;
    }

    // Try customer route first (iMessage blue bubble, then GHL), then alert-only GHL
    for (const route of ['customer', 'alert']) {
      const r = await sendMessage({ to: phone, text, route, fallback: true });
      if (r.ok) {
        sent++;
        state.recordReminder(phone, { name: row.customer, channel: r.channel, id: r.id || '' });
        console.log(`  SENT  ${phone}  ${row.customer}  via ${r.channel} (${route}) id=${r.id}`);
        break;
      }
      if (route === 'alert') {
        failed++;
        console.log(`  FAIL  ${phone}  ${row.customer}`);
        console.log('        ' + JSON.stringify(r.attempts || r.error));
      }
    }
  }

  console.log(`\nDone. sent=${sent} failed=${failed}\n`);
}

main().catch(e => { console.error('ERROR:', e.message); process.exit(1); });
