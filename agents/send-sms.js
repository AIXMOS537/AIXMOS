#!/usr/bin/env node
/**
 * send-sms.js — send a text through GHL / Quo / work-iPhone (auto-routed).
 *
 *   node send-sms.js --status                              show which channels are ready
 *   node send-sms.js --to +15551234567 --text "Hi"         auto-route (SEND_CHANNELS order)
 *   node send-sms.js --to ... --text "..." --channel ghl   force one channel
 *   node send-sms.js --to ... --text "..." --dry           dry run (don't send)
 *   node send-sms.js --to ... --text "..." --no-fallback   don't try the next channel
 */

const { sendMessage, channelStatus, channelOrder, routeOrder } = require('./lib/sender');

function arg(name, def) {
  const i = process.argv.indexOf(`--${name}`);
  return i >= 0 && process.argv[i + 1] && !process.argv[i + 1].startsWith('--') ? process.argv[i + 1] : def;
}
function flag(name) { return process.argv.includes(`--${name}`); }

async function main() {
  if (flag('status') || process.argv.length <= 2) {
    console.log('\n  CHANNEL STATUS  (priority: ' + channelOrder().join(' → ') + ')');
    console.log('  ' + '-'.repeat(60));
    for (const s of channelStatus()) {
      console.log(`  ${s.configured ? '[READY]' : '[ -- ]'}  ${s.channel.padEnd(9)} ${s.detail}`);
    }
    console.log('\n  ROLE ROUTING (by purpose):');
    for (const r of ['customer', 'partner', 'alert', 'reminder']) {
      console.log(`    ${r.padEnd(9)} → ${routeOrder(r).join(' → ')}`);
    }
    console.log('    (quo = manual team use only — not auto-routed)');
    console.log('');
    if (process.argv.length <= 2) {
      console.log('  Usage: node send-sms.js --to +1555... --text "hi"            (default route: customer/blue)');
      console.log('         node send-sms.js --to +1555... --text "hi" --route alert');
      console.log('         node send-sms.js --status\n');
    }
    return;
  }

  const to = arg('to');
  const text = arg('text');
  const channel = arg('channel');
  const route = arg('route', 'customer');
  if (!to || !text) { console.error('ERROR: --to and --text are required.'); process.exit(1); }

  const res = await sendMessage({ to, text, channel, route, fallback: !flag('no-fallback'), dryRun: flag('dry') });
  if (res.dryRun) {
    console.log(`DRY RUN — route "${route}" → [${(res.order || []).join(', ')}], would use "${res.channel}" to ${res.to}`);
  } else if (res.ok) {
    console.log(`SENT via ${res.channel}  (id: ${res.id})  to ${to}`);
  } else {
    console.log(`NOT SENT: ${res.error}`);
    (res.attempts || []).forEach(a => console.log(`   - ${a.channel}: ${a.ok ? 'ok' : a.error}`));
    process.exit(1);
  }
}

main().catch(e => { console.error('ERROR:', e.message); process.exit(1); });
