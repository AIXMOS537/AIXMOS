#!/usr/bin/env node
/**
 * Non-interactive smoke test for the full AIXMOS agent network.
 * RUN: node test-all-agents.js
 *      node test-all-agents.js --live   (call Claude API per agent)
 */

const fs = require('fs');
const path = require('path');
const { execSync } = require('child_process');

const { loadAixmosEnv } = require('./lib/env');
const { runAgent, loadRegistry } = require('./lib/runner');
const prompts = require('./agents/prompts');
const state = require('./state');

loadAixmosEnv();

const ROOT = __dirname;
const LIVE = process.argv.includes('--live');
const results = [];

function pass(name, detail = '') {
  results.push({ name, ok: true, detail });
}
function fail(name, detail = '') {
  results.push({ name, ok: false, detail });
}

function checkSyntax(file) {
  const rel = path.relative(ROOT, file);
  try {
    execSync(`node --check "${file}"`, { stdio: 'pipe' });
    pass(`syntax:${rel}`);
  } catch (e) {
    fail(`syntax:${rel}`, (e.stderr || e.message || '').toString().slice(0, 200));
  }
}

function checkRequire(mod, label) {
  try {
    require(mod);
    pass(`require:${label}`);
  } catch (e) {
    fail(`require:${label}`, e.message);
  }
}

async function testStateRoundtrip() {
  try {
    const backup = fs.existsSync(path.join(ROOT, 'aixmos-state.json'))
      ? fs.readFileSync(path.join(ROOT, 'aixmos-state.json'), 'utf8')
      : null;
    state.reset();
    state.startSession();
    state.updateAgent('chummo', { last_lead: 'TEST_SMOKE', last_mode: 'smoke' });
    state.setHandoff('chummo', 'moose', 'smoke handoff', 'test');
    const s = state.getSummary();
    if (s.chummo_lead !== 'TEST_SMOKE') throw new Error('chummo_lead mismatch');
    if (!s.active_handoffs.length) throw new Error('handoff not saved');
    if (backup) fs.writeFileSync(path.join(ROOT, 'aixmos-state.json'), backup);
    else state.reset();
    pass('state:roundtrip');
  } catch (e) {
    fail('state:roundtrip', e.message);
  }
}

const LIVE_CASES = [
  { id: 'chummo', prompt: 'MODE: SMOKE_TEST\nNAME: Test Lead\nCHANNEL: SMS\nWrite a 1-line welcome SMS only.' },
  { id: 'moose', prompt: 'MODE: SMOKE_TEST\nList exactly 2 numbered internal tasks for today. Keep under 80 words.' },
  { id: 'captain', prompt: 'MODE: SMOKE_TEST\nSituation: routine rental check-in. One-line COMMAND BRIEF only.' },
  { id: 'wonder_woman', prompt: 'MODE: SMOKE_TEST\nSituation: customer upset about late pickup. One ACTION line only.' },
  { id: 'vision', prompt: 'MODE: SMOKE_TEST\nProposal: send bulk discount SMS tonight. Verdict only (GO/HOLD/NO-GO).' },
  { id: 'tank', prompt: 'MODE: SMOKE_TEST\nQuestion: what is hub-brain? Answer in 2 sentences.' },
  { id: 'fly_guy', prompt: 'MODE: SMOKE_TEST\nDraft one rental reminder sentence, friend-first.' },
  { id: 'bob', prompt: 'MODE: SMOKE_TEST\nOne audit bullet for a smoke test run.' },
  { id: 'sticks', prompt: 'MODE: SMOKE_TEST\nOne SLA rule for overdue rental follow-ups.' },
  { id: 'jarvis', prompt: 'MODE: SMOKE_TEST\nRoute: who owns a routine booking status update? One sentence.' },
];

async function runLiveApiTests() {
  const backend = (process.env.AIXMOS_LLM_BACKEND || 'claude').toLowerCase();
  const hasClaude = !!process.env.ANTHROPIC_API_KEY;
  const usingOllama = backend === 'ollama' || (backend === 'auto' && !hasClaude);
  if (!hasClaude && !usingOllama) {
    fail('live:api', 'No LLM backend reachable — set ANTHROPIC_API_KEY or AIXMOS_LLM_BACKEND=ollama');
    return;
  }
  pass('live:api', `backend=${usingOllama ? 'ollama' : backend}`);
  for (const tc of LIVE_CASES) {
    const system = prompts[tc.id];
    if (!system) {
      fail(`live:${tc.id}`, 'no prompt in agents/prompts.js');
      continue;
    }
    try {
      const out = await runAgent({ system, userPrompt: tc.prompt, maxTokens: 400 });
      if (!out || out.trim().length < 10) throw new Error('empty or too short response');
      pass(`live:${tc.id}`, `${out.trim().slice(0, 80).replace(/\s+/g, ' ')}…`);
    } catch (e) {
      fail(`live:${tc.id}`, e.message);
    }
  }
}

async function testRegistryScripts() {
  let reg;
  try {
    reg = loadRegistry();
    pass('registry:load');
  } catch (e) {
    fail('registry:load', e.message);
    return;
  }
  for (const [key, agent] of Object.entries(reg.agents || {})) {
    const script = (agent.script || '').split(/\s+/)[0];
    if (!script) {
      fail(`registry:${key}`, 'missing script');
      continue;
    }
    const fp = path.join(ROOT, script);
    if (fs.existsSync(fp)) pass(`registry:${key}:${script}`);
    else fail(`registry:${key}:${script}`, 'file missing');
  }
}

async function testInfraCommands() {
  try {
    const { dockerAvailable } = require('./lib/tank-docker');
    if (dockerAvailable()) pass('tank:docker-available');
    else fail('tank:docker-available', 'Docker not running — TANK --up will fail until Docker Desktop starts');
  } catch (e) {
    fail('tank:docker-check', e.message);
  }

  const sticksKeys = ['SUPABASE_URL', 'SUPABASE_SERVICE_ROLE_KEY'];
  const missingSticks = sticksKeys.filter(k => !(process.env[k] || '').trim());
  if (missingSticks.length) {
    fail('sticks:env', `Missing ${missingSticks.join(', ')} — --scan needs Supabase`);
  } else {
    try {
      const { scanOverdue } = require('./lib/sticks-alerts');
      const { report } = await scanOverdue();
      pass('sticks:scan', report.split('\n')[0] || 'ok');
    } catch (e) {
      fail('sticks:scan', e.message);
    }
  }
}

async function main() {
  const jsFiles = fs
    .readdirSync(ROOT)
    .filter(f => f.endsWith('.js') && f !== 'test-all-agents.js');
  for (const f of jsFiles) checkSyntax(path.join(ROOT, f));
  for (const f of ['lib/runner.js', 'lib/env.js', 'lib/agent-cli.js', 'agents/prompts.js']) {
    checkSyntax(path.join(ROOT, f));
  }

  checkRequire('./state', 'state');
  checkRequire('./agents/prompts', 'prompts');

  await testStateRoundtrip();
  await testRegistryScripts();

  if (LIVE) await runLiveApiTests();
  else pass('live:skipped', 'add --live to call Claude for each agent');

  await testInfraCommands();

  const ok = results.filter(r => r.ok).length;
  const bad = results.filter(r => !r.ok);
  console.log('\n══ AIXMOS AGENT TEST REPORT ══\n');
  for (const r of results) {
    const mark = r.ok ? '✓' : '✗';
    console.log(`  ${mark} ${r.name}${r.detail ? ` — ${r.detail}` : ''}`);
  }
  console.log(`\n  ${ok}/${results.length} checks passed`);
  if (bad.length) {
    console.log(`  ${bad.length} failed — fix before relying on agents in production.\n`);
    process.exit(1);
  }
  console.log('\n  All checks passed.\n');
}

main().catch(e => {
  console.error(e);
  process.exit(1);
});
