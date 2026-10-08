#!/usr/bin/env node
'use strict';
/**
 * claims-check — run the claims gate over a draft, a file, or a whole outbox.
 *
 * The gate itself runs automatically inside lib/sender.js. This is the human-facing side:
 * a way to check a draft before you approve it, and a way to audit what an install has
 * been producing. A review queue where someone is approving fifty drafts a week is exactly
 * where an invented price slips through — this makes the violation visible instead.
 *
 *   node claims-check.js "Marcus, $175 to detail your Tahoe."
 *   node claims-check.js --file drafts/reply-0912.txt
 *   node claims-check.js --dir  ~/SORK-CONTROL/outbox/front-desk
 *   node claims-check.js --self-test
 *
 * Exit code is 0 when everything checked is clean, 1 when anything was refused — so it can
 * gate a script or a pre-send hook, not just print.
 */

const fs = require('fs');
const path = require('path');
const { checkClaims, explain } = require('./lib/claims');
const { loadProfile } = require('./lib/profile');

const args = process.argv.slice(2);

function report(label, text) {
  const r = checkClaims(text);
  if (r.ok) {
    console.log(`  ✅ ${label}`);
    return 0;
  }
  console.log(`  ⛔ ${label}`);
  for (const v of r.violations) console.log(`       ${v.found}  —  ${v.why}`);
  return 1;
}

function header() {
  const p = loadProfile();
  const card = Array.isArray(p.rate_card) ? p.rate_card.length : 0;
  console.log(`claims gate — profile: ${p.source}`
    + ` | business: ${p.business_name || '(unnamed)'}`
    + ` | vertical: ${p.industry_pack || '(none)'}`
    + ` | rate card: ${card} item${card === 1 ? '' : 's'}`);
  if (!card) {
    console.log('  ⚠️  No rate card on this install — ANY price in a draft will be refused.');
    console.log('     Add "rate_card": [{"item":"…","price":"$0"}] to the business profile.');
  }
  console.log('');
}

function selfTest() {
  // Proves the gate is live on THIS install, with THIS install's rate card — not that the
  // library works in the abstract. Run it after an install, before trusting a draft.
  console.log('self-test — the gate must REFUSE the first and ALLOW the second:\n');
  const bad = 'Results guaranteed, and I can do it for $173.50.';
  const good = 'Happy to help — let me confirm the details and come right back to you.';
  const b = checkClaims(bad);
  const g = checkClaims(good);
  console.log(`  refuses an invented price + guarantee : ${b.ok ? '❌ FAILED — it allowed it' : '✅'}`);
  if (!b.ok) for (const v of b.violations) console.log(`       ${v.found} — ${v.why}`);
  console.log(`  allows an ordinary reply              : ${g.ok ? '✅' : '❌ FAILED — ' + explain(g)}`);
  const pass = !b.ok && g.ok;
  console.log(`\n  ${pass ? '✅ gate is live on this install' : '❌ GATE IS NOT WORKING — do not send from this install'}`);
  return pass ? 0 : 1;
}

function main() {
  if (!args.length || args[0] === '--help' || args[0] === '-h') {
    console.log(fs.readFileSync(__filename, 'utf8')
      .split('\n').slice(2, 19).map(l => l.replace(/^ \*ю?\s?/, '').replace(/^ \*\/?/, '')).join('\n'));
    return 0;
  }

  header();

  if (args[0] === '--self-test') return selfTest();

  if (args[0] === '--file') {
    const f = args[1];
    if (!f || !fs.existsSync(f)) { console.error(`no such file: ${f}`); return 1; }
    return report(path.basename(f), fs.readFileSync(f, 'utf8'));
  }

  if (args[0] === '--dir') {
    const d = args[1];
    if (!d || !fs.existsSync(d)) { console.error(`no such directory: ${d}`); return 1; }
    const files = fs.readdirSync(d)
      .filter(f => /\.(md|txt|json)$/i.test(f))
      .map(f => path.join(d, f))
      .filter(f => fs.statSync(f).isFile());
    if (!files.length) { console.log('  (nothing to check)'); return 0; }
    let bad = 0;
    for (const f of files) bad += report(path.basename(f), fs.readFileSync(f, 'utf8'));
    console.log(`\n  ${files.length - bad}/${files.length} clean` + (bad ? ` · ${bad} REFUSED` : ''));
    return bad ? 1 : 0;
  }

  return report('draft', args.join(' '));
}

process.exit(main());
