#!/usr/bin/env node
/**
 * Simple status — ON/OFF + how many customers need attention.
 */

const { loadAixmosEnv } = require('./lib/env');
const { dockerAvailable, composePs } = require('./lib/tank-docker');
const { loadRegistry } = require('./lib/runner');

loadAixmosEnv();

async function customerCount() {
  try {
    const { fetchOverdueAlerts } = require('./lib/supabase-ops');
    const alerts = await fetchOverdueAlerts();
    const urgent = alerts.filter(a => a.severity === 'critical').length;
    return { total: alerts.length, urgent };
  } catch {
    return null;
  }
}

async function main() {
  console.log('');
  console.log('  AIXMOS AI BRAIN — STATUS');
  console.log('  ========================');
  console.log('');

  const dockerOk = dockerAvailable();
  let brainOn = false;
  if (dockerOk) {
    try {
      const ps = composePs(loadRegistry());
      brainOn = ps.ok && /n8n|open-webui|Up/i.test(ps.stdout || '');
    } catch {
      brainOn = false;
    }
  }

  if (brainOn) {
    console.log('  Brain:  ON  (helpers are running)');
  } else if (dockerOk) {
    console.log('  Brain:  OFF (pick "Turn Brain ON" from the menu)');
  } else {
    console.log('  Brain:  OFF (start Docker Desktop first)');
  }

  const counts = await customerCount();
  if (counts) {
    console.log('');
    console.log(`  People needing attention: ${counts.total}`);
    if (counts.urgent > 0) {
      console.log(`  Urgent right now:         ${counts.urgent}`);
    }
  } else {
    console.log('');
    console.log('  Customer check: not set up yet (need Supabase in .env)');
  }

  console.log('');
}

main().catch(e => {
  console.log('  Error:', e.message);
  process.exit(1);
});
