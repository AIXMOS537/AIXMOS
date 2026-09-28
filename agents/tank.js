#!/usr/bin/env node
/**
 * TANK — infrastructure execution.
 *   node tank.js --up        Auto-start hub-brain (n8n + Open WebUI)
 *   node tank.js --down      Stop hub-brain
 *   node tank.js --status    docker compose ps
 *   node tank.js --logs      Tail compose logs
 *   node tank.js             Interactive Claude mode
 */

const fs = require('fs');
const path = require('path');
const { loadAixmosEnv } = require('./lib/env');
const { loadRegistry } = require('./lib/runner');
const {
  dockerAvailable,
  composeUp,
  composeDown,
  composePs,
  composeLogs,
  getHubBrainDir,
} = require('./lib/tank-docker');
const { runInteractiveAgent } = require('./lib/agent-cli');

loadAixmosEnv();

const args = process.argv.slice(2);

function println(t = '') {
  console.log(t);
}

async function runDockerCommand(action) {
  const registry = loadRegistry();
  const remote = (process.env.HUB_BRAIN_HOST || '').trim();

  if (remote) {
    println(`TANK → hub-brain (remote: ${remote})`);
  } else {
    const hubDir = getHubBrainDir(registry);
    if (!dockerAvailable()) {
      println('Docker is not running. Start Docker Desktop, then run: node tank.js --up');
      process.exit(1);
    }
    println(`TANK → hub-brain (${hubDir})`);
    if (action === 'up') println('Running: docker compose up -d …');
  }

  let result;
  switch (action) {
    case 'up':   result = composeUp(registry);   break;
    case 'down': result = composeDown(registry); break;
    case 'ps':   result = composePs(registry);   break;
    case 'logs': result = composeLogs(registry); break;
    default: return;
  }

  if (result.stdout) println(result.stdout);
  if (result.stderr) println(result.stderr);
  println(result.ok ? '✓ OK' : `✗ Failed (exit ${result.status})`);
  if (!result.ok) process.exit(result.status || 1);

  if (action === 'up' && !remote) {
    println('\nServices (defaults):');
    println('  n8n         http://localhost:5678');
    println('  Open WebUI  http://localhost:3000  (maps container 8080)');
  }
}

async function main() {
  if (args.includes('--up') || args[0] === 'up') return runDockerCommand('up');
  if (args.includes('--down') || args[0] === 'down') return runDockerCommand('down');
  if (args.includes('--status') || args.includes('--ps') || args[0] === 'ps') {
    return runDockerCommand('ps');
  }
  if (args.includes('--logs')) return runDockerCommand('logs');

  await runInteractiveAgent('tank', {
    hint: 'TANK — Docker, n8n, Supabase, Vercel. Or run: node tank.js --up',
  });
}

main().catch(e => {
  console.error(e.message);
  process.exit(1);
});
