#!/usr/bin/env node
/**
 * STICKS — SLA + overdue alerts (Supabase → GHL).
 *   node sticks.js --scan           Report only
 *   node sticks.js --push-ghl       Scan + tag overdue in GHL
 *   node sticks.js --push-ghl --dry-run
 *   node sticks.js                  Interactive Claude mode
 */

const { loadAixmosEnv, requireEnv } = require('./lib/env');
const { scanOverdue, pushOverdueToGhl, saveReportToFile } = require('./lib/sticks-alerts');
const { runInteractiveAgent } = require('./lib/agent-cli');

loadAixmosEnv();

const args = process.argv.slice(2);
const dryRun = args.includes('--dry-run');

async function main() {
  if (args.includes('--scan') || args.includes('--push-ghl')) {
    requireEnv(['SUPABASE_URL', 'SUPABASE_SERVICE_ROLE_KEY']);

    if (args.includes('--push-ghl')) {
      requireEnv(['TMMT_OPS_URL']);
      const secret =
        process.env.GHL_OVERDUE_WEBHOOK_SECRET || process.env.GHL_WEBHOOK_SECRET;
      if (!secret && !dryRun) {
        console.warn('Warning: GHL webhook secret not set — overdue POST may 401');
      }
      const { report, results } = await pushOverdueToGhl({ dryRun });
      console.log(report);
      console.log('\nGHL push:', JSON.stringify(results, null, 2));
      const file = saveReportToFile(report);
      console.log(`\nSaved: ${file}`);
      return;
    }

    const { report } = await scanOverdue();
    console.log(report);
    const file = saveReportToFile(report);
    console.log(`\nSaved: ${file}`);
    return;
  }

  await runInteractiveAgent('sticks', {
    hint: 'STICKS — SLA. Try: node sticks.js --scan',
  });
}

main().catch(e => {
  console.error(e.message);
  process.exit(1);
});
