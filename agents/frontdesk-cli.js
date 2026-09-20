#!/usr/bin/env node
'use strict';
/**
 * frontdesk — hand the desk one inbound, or read what is waiting for a human.
 *
 *   node frontdesk-cli.js "+15715550101" "how much to detail a Tahoe?"
 *   node frontdesk-cli.js --queue
 *
 * Nothing here sends. The desk triages, runs the lane's agents, gates the draft and
 * queues it. Approving and sending stays a human action, by design.
 */
const fd = require('./lib/frontdesk');
const { loadProfile } = require('./lib/profile');

const a = process.argv.slice(2);

async function main() {
  const p = loadProfile();
  console.log(`front desk — ${p.business_name || '(unnamed install)'}`
    + ` · vertical: ${p.industry_pack || 'none'}`
    + ` · rate card: ${(p.rate_card || []).length}\n`);

  if (a[0] === '--queue' || a[0] === '-q') {
    const q = fd.listQueue();
    if (!q.length) return console.log('  queue is empty');
    for (const it of q.slice(0, 25)) {
      const flag = it.status === 'NEEDS_FIX' ? '⛔' : it.escalated ? '⚠️ ' : '  ';
      console.log(`${flag} ${it.at || ''}  ${String(it.lane).padEnd(14)} ${String(it.status).padEnd(20)} ${String(it.from || '')}`);
      if (it.status === 'NEEDS_FIX' && it.gate) console.log(`     ${it.gate.summary}`);
    }
    console.log(`\n  ${q.length} total · ${fd.QUEUE_DIR}`);
    return;
  }

  if (a.length < 1) {
    console.log('usage: frontdesk "<from>" "<message>"   |   frontdesk --queue');
    process.exitCode = 1;
    return;
  }
  const from = a.length > 1 ? a[0] : null;
  const text = a.length > 1 ? a.slice(1).join(' ') : a[0];

  const r = await fd.handleInbound({ from, text, channel: 'cli' });
  console.log(`  lane    ${r.lane}   chain: ${r.chain.join(' → ') || '(none)'}`);
  for (const s of r.trace) console.log(`  ·       ${s.step}: ${s.result}`);
  console.log(`  status  ${r.status}${r.escalated ? '  ⚠️ ESCALATED' : ''}   sent=${r.sent}`);
  if (r.gate && !r.gate.ok) console.log(`  gate    ⛔ ${r.gate.summary}`);
  if (r.draft) {
    console.log(`\n  ── draft (${r.draft_from}) ──`);
    console.log('  ' + r.draft.replace(/\n/g, '\n  '));
  }
  if (r.handoff) console.log(`\n  handoff: ${r.handoff}`);
  if (r.queued) console.log(`\n  queued: ${r.queued}`);
}

main().catch(e => { console.error('front desk failed:', e.message); process.exit(1); });
