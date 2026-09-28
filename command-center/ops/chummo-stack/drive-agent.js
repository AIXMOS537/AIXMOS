#!/usr/bin/env node
const fs = require('fs');
const path = require('path');
const child_process = require('child_process');
const readline = require('readline');

const root = __dirname;
const filesRoot = path.join(root, '..', 'files');
const mooseRoot = path.join(root, '..', 'MOOSECLAUDEOS');
const driveRoot = path.join(root, '..');

function exists(filePath) {
  try { return fs.existsSync(filePath); } catch { return false; }
}

function installed(dir) {
  return exists(path.join(dir, 'node_modules'));
}

function safeRun(command, args, cwd) {
  try {
    child_process.execFileSync(command, args, { stdio: 'inherit', cwd, shell: true });
    return true;
  } catch (err) {
    console.error(`\n✖ Failed to run ${command} ${args.join(' ')} in ${cwd}`);
    return false;
  }
}

function printHeader() {
  console.log('\n=== AIXMOS DRIVE AGENT ===');
  console.log(`USB root: ${driveRoot}`);
  console.log('Coordinates CHUMMO, files/, and BRAIN workflows from this drive.');
  console.log('===========================================\n');
}

async function ollamaOk() {
  const base = (process.env.OLLAMA_BASE_URL || 'http://127.0.0.1:11434').replace(/\/$/, '');
  try {
    const res = await fetch(`${base}/api/tags`, { signal: AbortSignal.timeout(3000) });
    return res.ok;
  } catch {
    return false;
  }
}

function getStatus(ollamaReachable) {
  return {
    nodeVersion: process.version,
    ollamaReachable,
    hasAnthropicKey: !!process.env.ANTHROPIC_API_KEY,
    chummoInstalled: installed(root),
    filesInstalled: installed(filesRoot),
    mooseExists: exists(path.join(filesRoot, 'moose.js')),
    brainExists: exists(path.join(filesRoot, 'brain.js')),
    serveExists: exists(path.join(root, 'serve.js')),
    chummoExists: exists(path.join(root, 'chummo.js')),
    mooseRootExists: exists(mooseRoot),
  };
}

function describePlan(status) {
  console.log('ORDERED EXECUTION PLAN');
  console.log('------------------------');
  console.log('1) Confirm your environment:');
  console.log(`   - Node.js version: ${status.nodeVersion}`);
  console.log('   - Recommended: Node 18 or newer.');
  console.log('2) Install dependencies if needed:');
  console.log(`   - CHUMMO root: ${installed(root) ? 'OK' : 'Missing node_modules'}`);
  console.log(`   - files root: ${installed(filesRoot) ? 'OK' : 'Missing node_modules'}`);
  if (status.ollamaReachable) {
    console.log('3) Ollama: ready (local AI first — no API key required)');
  } else if (!status.hasAnthropicKey) {
    console.log('3) Start Ollama: ollama serve — or set ANTHROPIC_API_KEY for cloud fallback');
  } else {
    console.log('3) Anthropic API key: present (cloud fallback)');
  }
  console.log('4) Run the local brain orchestrator to synthesize strategy and delegation:');
  console.log('   - node files/brain.js');
  console.log('5) Use CHUMMO for messaging when you need outreach copy:');
  console.log('   - node chummo.js');
  console.log('5b) Batch all pipelines (CSV/GHL export):');
  console.log('   - node chummo-run.js --source data/leads.example.csv');
  console.log('   - See CHUMMO_PIPELINE.md');
  console.log('6) Use the portal when you want the web interface:');
  console.log('   - node serve.js  # then open http://localhost:3000');
  console.log('7) Use MOOSE as the execution agent for operational tasks:');
  console.log('   - node files/moose.js');
  if (status.mooseRootExists) {
    console.log('8) MOOSE launcher folder (same engine as files/moose.js):');
    console.log(`   - ${path.join(mooseRoot, 'moose.js')}`);
  }
  console.log('\nNotes:');
  console.log('- Run setup before anything else if node_modules are missing.');
  console.log('- Ollama is used first when running (AI_PROVIDER=auto). Anthropic key is optional fallback.');
  console.log('- Start with BRAIN first if you want a single coordinated plan.');
}

function prompt(question) {
  const rl = readline.createInterface({ input: process.stdin, output: process.stdout });
  return new Promise(resolve => rl.question(question, answer => { rl.close(); resolve(answer.trim()); }));
}

async function main() {
  printHeader();
  const status = getStatus(await ollamaOk());
  describePlan(status);

  const answer = await prompt('\nWould you like the agent to run setup now? (y/n): ');
  if (answer.toLowerCase() === 'y') {
    if (!status.chummoInstalled) {
      console.log('\nInstalling dependencies in CHUMMO root...');
      safeRun('npm', ['install'], root);
    }
    if (!status.filesInstalled) {
      console.log('\nInstalling dependencies in files root...');
      safeRun('npm', ['install'], filesRoot);
    }
    console.log('\nSetup completed. Re-run this script if you want to launch an action.');
    return;
  }

  const next = await prompt('Choose next action: [1] Brain  [2] CHUMMO  [3] Portal  [4] MOOSE  [5] Quit: ');
  switch (next.trim()) {
    case '1':
      console.log('\nLaunching the brain orchestrator...');
      safeRun('node', ['brain.js'], filesRoot);
      break;
    case '2':
      console.log('\nLaunching CHUMMO messaging agent...');
      safeRun('node', ['chummo.js'], root);
      break;
    case '3':
      if (!status.serveExists) {
        console.log('\nserve.js is not present in CHUMMO root.');
      } else {
        console.log('\nLaunching portal server...');
        safeRun('node', ['serve.js'], root);
      }
      break;
    case '4':
      if (!status.mooseExists) {
        console.log('\nmoose.js is not present in files root.');
      } else {
        console.log('\nLaunching MOOSE execution agent...');
        safeRun('node', ['moose.js'], filesRoot);
      }
      break;
    default:
      console.log('\nDone. Use this agent again to review and run the next step.');
  }
}

main().catch(err => {
  console.error('Agent error:', err.message);
  process.exit(1);
});
