#!/usr/bin/env node
/**
 * Shared interactive CLI for infrastructure agents.
 */

const readline = require('readline');
const { execSync } = require('child_process');
const { loadAixmosEnv } = require('./env');
const prompts = require('../agents/prompts');

loadAixmosEnv();
const state = require('../state');
const { runAgent } = require('./runner');

const c = {
  reset: '\x1b[0m',
  bold: '\x1b[1m',
  dim: '\x1b[2m',
  cyan: '\x1b[36m',
  green: '\x1b[32m',
  blue: '\x1b[34m',
  magenta: '\x1b[35m',
  yellow: '\x1b[33m',
  red: '\x1b[31m',
};

function println(t = '') {
  console.log(t);
}

function ask(rl, q) {
  return new Promise(r => rl.question(q, a => r(a.trim())));
}

function copyToClipboard(text) {
  try {
    if (process.platform === 'win32') execSync('clip', { input: text });
    else if (process.platform === 'darwin') execSync('pbcopy', { input: text });
    else execSync('xclip -selection clipboard', { input: text });
    return true;
  } catch {
    return false;
  }
}

const HANDOFF_ROUTES = {
  chummo: { tag: 'MOOSE_HANDOFF', to: 'moose' },
  moose: { tag: 'CAPTAIN_HANDOFF', to: 'captain' },
  captain: { tag: 'WONDERWOMAN_HANDOFF', to: 'wonder_woman' },
  tank: { tag: 'BOB_HANDOFF', to: 'bob' },
  sticks: { tag: 'CAPTAIN_HANDOFF', to: 'captain' },
  fly_guy: { tag: 'CHUMMO_HANDOFF', to: 'chummo' },
};

async function runInteractiveAgent(agentKey, options = {}) {
  const displayNames = {
    chummo: 'C.H.U.M.M.O',
    moose: 'M.O.O.S.E',
    captain: 'CAPTAIN',
    wonder_woman: 'WONDERWOMAN',
    vision: 'VISION',
    tank: 'TANK',
    fly_guy: 'FLY GUY',
    bob: 'BOB',
    sticks: 'STICKS',
    jarvis: 'JARVIS',
  };

  const system = prompts[agentKey];
  if (!system) throw new Error(`Unknown agent: ${agentKey}`);

  const rl = readline.createInterface({ input: process.stdin, output: process.stdout });
  println();
  println(`${c.bold}${displayNames[agentKey] || agentKey.toUpperCase()} — ACTIVE${c.reset}`);
  println(`${c.dim}${options.hint || 'Describe the situation. Be specific.'}${c.reset}`);
  println();

  let userPrompt = options.prefill || '';
  if (!userPrompt) {
    userPrompt = await ask(rl, `${c.cyan}Request: ${c.reset}`);
  }
  if (!userPrompt) {
    println(`${c.yellow}No input — exiting.${c.reset}`);
    rl.close();
    return null;
  }

  println();
  printRunning(displayNames[agentKey] || agentKey);

  let output;
  try {
    output = await runAgent({ system, userPrompt: `${userPrompt}\n\nExecute now. No hesitation on reversible internal steps.` });
  } catch (e) {
    println(`\n${c.red}Error: ${e.message}${c.reset}`);
    rl.close();
    return null;
  }

  println('\n');
  println('═'.repeat(56));
  println(output);
  println('═'.repeat(56));

  if (copyToClipboard(output)) println(`\n${c.green}✓ Copied to clipboard${c.reset}`);

  const route = HANDOFF_ROUTES[agentKey];
  if (route) {
    const raw = output.match(new RegExp(`${route.tag}:\\s*([\\s\\S]+)`, 'i'));
    const content = raw ? raw[1].trim() : null;
    if (content) {
      state.setHandoff(agentKey, route.to, content, `${agentKey} → ${route.to}`);
    }
  }

  state.updateAgent(agentKey, {
    last_mode: options.mode || 'interactive',
    last_output: output.substring(0, 800),
  });

  rl.close();
  return output;
}

function printRunning(name) {
  process.stdout.write(`  ${c.cyan}${name} running${c.reset}`);
  const id = setInterval(() => process.stdout.write('.'), 300);
  setTimeout(() => clearInterval(id), 1200);
}

module.exports = { runInteractiveAgent, ask, println, c };
