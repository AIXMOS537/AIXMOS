#!/usr/bin/env node
'use strict';
/**
 * SETUP — turn a bare client machine into a working AIXMOS install, then PROVE it.
 *
 * WHY THIS REPLACES THE OLD BANNER. `install-mac.sh` copied files, ran npm install, printed
 * a green success box, and then told the operator to go install Ollama themselves and
 * `ollama pull llama3.1:8b` — a tag that exists on none of the fleet's machines. Nothing
 * had asked the brain a question, validated a key, or watched a single gate refuse. The
 * install "succeeded" in exactly the way the silent-bleed doctrine warns about.
 *
 * This installs the dependencies, wires the connections, and then hands the whole thing to
 * lib/doctor.js, which probes every wire. **If the doctor is not READY, this exits non-zero
 * and does not print a success banner.** An install that cannot prove itself is not an
 * install; it is a directory of files.
 *
 * WHAT IT WILL NOT DO. It does not enable auto-send, and there is no flag that does. Drafts
 * queue for a human. That is not a limitation waiting to be lifted — sending unreviewed
 * machine-written messages from a client's own number is how a client gets a TCPA problem,
 * and the gates in this pack exist precisely so the owner's approval is the last step.
 *
 *   node setup.js                 full interactive setup
 *   node setup.js --yes           non-interactive, defaults, no prompts
 *   node setup.js --doctor        verify only, change nothing
 *   node setup.js --autostart     (re)install the background service
 */

const fs = require('fs');
const os = require('os');
const path = require('path');
const readline = require('readline');
const crypto = require('crypto');
const { execSync, spawnSync } = require('child_process');

const ROOT = __dirname;
const CFG = path.join(ROOT, 'config');
const ENV_FILE = path.join(CFG, 'aixmos.env');
const PROFILE_FILE = path.join(CFG, 'business-profile.json');

const C = {
  b: '\x1b[1m', d: '\x1b[2m', g: '\x1b[32m', y: '\x1b[33m', r: '\x1b[31m', c: '\x1b[36m', x: '\x1b[0m',
};
const say = (s = '') => console.log(s);
const step = (n, t) => say(`\n${C.b}[${n}]${C.x} ${t}`);
const okline = (s) => say(`    ${C.g}✓${C.x} ${s}`);
const warn = (s) => say(`    ${C.y}!${C.x} ${s}`);
const fail = (s) => say(`    ${C.r}✗${C.x} ${s}`);

const ARGS = new Set(process.argv.slice(2));
const AUTO = ARGS.has('--yes') || ARGS.has('-y');

let rl;
function ask(q, dflt = '') {
  if (AUTO) return Promise.resolve(dflt);
  rl = rl || readline.createInterface({ input: process.stdin, output: process.stdout });
  return new Promise(res => rl.question(`    ${C.c}${q}${dflt ? ` [${dflt}]` : ''}: ${C.x}`,
    a => res(a.trim() || dflt)));
}

function sh(cmd, opts = {}) {
  try { return execSync(cmd, { stdio: ['ignore', 'pipe', 'pipe'], ...opts }).toString().trim(); }
  catch { return null; }
}
function has(bin) {
  return !!sh(process.platform === 'win32' ? `where ${bin}` : `command -v ${bin}`);
}

/* ─────────────────────── 1. runtime dependencies ─────────────────────── */

function installDeps() {
  step(1, 'Dependencies');
  const major = parseInt(process.versions.node.split('.')[0], 10);
  if (major < 18) {
    fail(`Node ${process.versions.node} is too old. Install Node 18+ first.`);
    if (process.platform === 'win32') say(`      bundled installer: ${path.join(ROOT, '_installers')}`);
    process.exit(1);
  }
  okline(`Node ${process.versions.node}`);

  if (fs.existsSync(path.join(ROOT, 'node_modules', '@anthropic-ai', 'sdk'))) {
    okline('npm dependencies already present');
    return;
  }
  say(`    ${C.d}running npm install (needs internet once)…${C.x}`);
  const r = spawnSync('npm', ['install', '--no-audit', '--no-fund'], { cwd: ROOT, stdio: 'inherit', shell: true });
  if (r.status !== 0) {
    fail('npm install failed — the pack cannot reach Claude without @anthropic-ai/sdk.');
    fail('The local (Ollama) lane will still work once a model is installed.');
  } else okline('npm dependencies installed');
}

/* ─────────────────────── 2. the local brain ─────────────────────── */

/**
 * Install Ollama and a model that ACTUALLY EXISTS. The old script told people to pull
 * llama3.1:8b, which nothing on the fleet has. We pick from what is installed first, and
 * only pull when there is genuinely nothing.
 */
async function setupBrain(env) {
  step(2, 'Local brain (free lane — $0 per query, works offline)');

  if (!has('ollama')) {
    warn('Ollama is not installed.');
    const want = AUTO ? 'y' : await ask('Install it now? (y/n)', 'y');
    if (want.toLowerCase().startsWith('y')) {
      if (process.platform === 'darwin' && has('brew')) {
        say(`    ${C.d}brew install ollama…${C.x}`);
        spawnSync('brew', ['install', 'ollama'], { stdio: 'inherit' });
      } else if (process.platform === 'win32' && has('winget')) {
        say(`    ${C.d}winget install Ollama.Ollama…${C.x}`);
        spawnSync('winget', ['install', '-e', '--id', 'Ollama.Ollama', '--accept-package-agreements',
          '--accept-source-agreements'], { stdio: 'inherit', shell: true });
      } else {
        warn('No package manager found. Install from https://ollama.com/download, then re-run.');
        return;
      }
    } else { warn('Skipped — this install will depend entirely on Claude.'); return; }
  }
  if (!has('ollama')) { warn('Ollama still not on PATH — open a new terminal and re-run.'); return; }
  okline('Ollama present');

  // Is the server up? Start it if not.
  const host = env.OLLAMA_HOST || 'http://localhost:11434';
  let tags = await probeTags(host);
  if (!tags) {
    say(`    ${C.d}starting ollama serve…${C.x}`);
    try {
      const { spawn } = require('child_process');
      spawn('ollama', ['serve'], { detached: true, stdio: 'ignore' }).unref();
    } catch { /* ignore */ }
    await new Promise(r => setTimeout(r, 3000));
    tags = await probeTags(host);
  }
  if (!tags) { warn(`Ollama not answering at ${host}. Start it with: ollama serve`); return; }

  const installed = tags.map(m => m.name);
  okline(`server up at ${host} · ${installed.length} model(s)`);

  // Prefer something already on disk. Ranked by how well it does agent work.
  const PREFERRED = ['qwen3:14b', 'qwen2.5:14b', 'gpt-oss:20b', 'llama3.1:8b', 'llama3.2:3b', 'phi3:mini'];
  let pick = PREFERRED.find(m => installed.includes(m)) || installed[0];

  if (!installed.length) {
    // Nothing at all — pull one sized to the machine rather than a fixed guess.
    const gb = Math.round(os.totalmem() / 1e9);
    const target = gb >= 24 ? 'qwen3:14b' : gb >= 12 ? 'llama3.1:8b' : 'llama3.2:3b';
    say(`    ${C.d}no models installed · ${gb}GB RAM → pulling ${target} (this takes a while)…${C.x}`);
    spawnSync('ollama', ['pull', target], { stdio: 'inherit' });
    pick = target;
  }
  env.OLLAMA_HOST = host;
  env.OLLAMA_MODEL = pick;
  okline(`model wired: ${pick}`);
}

async function probeTags(host) {
  try {
    const ac = new AbortController();
    const t = setTimeout(() => ac.abort(), 4000);
    const r = await fetch(`${host}/api/tags`, { signal: ac.signal });
    clearTimeout(t);
    const j = await r.json();
    return j.models || [];
  } catch { return null; }
}

/* ─────────────────────── 3. connect to Claude ─────────────────────── */

async function connectClaude(env) {
  step(3, 'Connect to Claude');
  say(`    ${C.d}Two ways. An AIXMOS licence key is the managed route — your provider${C.x}`);
  say(`    ${C.d}runs the account. An Anthropic API key means you own the billing.${C.x}`);

  if (env.AIXMOS_LICENSE_KEY || env.ANTHROPIC_API_KEY) {
    okline('a credential is already configured');
  } else {
    const kind = await ask('Licence key (L) or your own Anthropic API key (A)? (l/a/skip)', 'skip');
    if (kind.toLowerCase().startsWith('l')) {
      const k = await ask('AIXMOS licence key');
      if (k) { env.AIXMOS_LICENSE_KEY = k; env.AIXMOS_GATEWAY_URL = env.AIXMOS_GATEWAY_URL
        || 'https://aixmos-gateway.aixmos.workers.dev'; }
    } else if (kind.toLowerCase().startsWith('a')) {
      const k = await ask('Anthropic API key (sk-ant-…)');
      if (k) env.ANTHROPIC_API_KEY = k;
    } else {
      warn('Skipped — this install will run on the local lane only.');
    }
  }

  // Backend: auto is the right default for a client. Claude when reachable, local when not.
  if (!env.AIXMOS_LLM_BACKEND) {
    env.AIXMOS_LLM_BACKEND = (env.ANTHROPIC_API_KEY || env.AIXMOS_LICENSE_KEY) ? 'auto' : 'ollama';
  }
  env.AIXMOS_MODEL = env.AIXMOS_MODEL || 'claude-opus-5';
  okline(`backend: ${env.AIXMOS_LLM_BACKEND}  (auto = Claude first, local fallback)`);
}

/* ─────────────────────── 4. the business profile ─────────────────────── */

async function setupProfile() {
  step(4, 'Whose business is this? (white-label)');
  if (fs.existsSync(PROFILE_FILE)) {
    const p = JSON.parse(fs.readFileSync(PROFILE_FILE, 'utf8'));
    okline(`profile exists: ${p.business_name || '(unnamed)'} · rate card: ${(p.rate_card || []).length}`);
    return;
  }
  if (AUTO) {
    warn('No profile and --yes given. Agents will name no business until one is written.');
    warn(`Write ${PROFILE_FILE} from config/business-profile.example.json.`);
    return;
  }

  const name = await ask('Business name');
  if (!name) { warn('Skipped — agents will not name any business (safe default).'); return; }
  const what = await ask('What does it do? (one line)');
  const vertical = await ask('Industry pack (auto_detail/home_services/med_spa/real_estate/…)', '');

  say(`    ${C.d}Rate card — the ONLY prices the agents may quote. Anything else is refused${C.x}`);
  say(`    ${C.d}by the claims gate. Blank line when done. Leave empty to forbid all quoting.${C.x}`);
  const rate_card = [];
  for (;;) {
    const item = await ask(`  item ${rate_card.length + 1} name (blank = done)`);
    if (!item) break;
    const price = await ask(`  ${item} price (e.g. $125 or 15%)`);
    if (price) rate_card.push({ item, price });
  }

  const esc = await ask('Escalate to you when… (comma separated)',
    'damage claims, anything legal, an unhappy customer');

  const profile = {
    business_name: name,
    what_we_do: what || null,
    owner_label: 'OWNER',
    industry_pack: vertical || null,
    lines: [],
    rate_card,
    escalate_to_owner: esc.split(',').map(s => s.trim()).filter(Boolean),
    notes: [],
  };
  fs.mkdirSync(CFG, { recursive: true });
  fs.writeFileSync(PROFILE_FILE, JSON.stringify(profile, null, 2));
  okline(`profile written · ${rate_card.length} rate-card item(s)`);
  if (!rate_card.length) warn('No rate card — every price in a draft will be refused. That is the safe default.');
}

/* ─────────────────────── 5. secrets ─────────────────────── */

function setupSecrets(env) {
  step(5, 'Secrets');
  if (!env.AIX_AGENT_TOKEN || env.AIX_AGENT_TOKEN.length < 16) {
    env.AIX_AGENT_TOKEN = crypto.randomBytes(32).toString('hex');
    okline('generated AIX_AGENT_TOKEN (the agent HTTP server refuses to start without one)');
  } else okline('AIX_AGENT_TOKEN already set');
  env.AIX_AGENT_HOST = env.AIX_AGENT_HOST || '127.0.0.1';
  env.AIX_AGENT_PORT = env.AIX_AGENT_PORT || '7777';
}

/* ─────────────────────── 6. owner notifications ─────────────────────── */

/**
 * The old setup.js existed only to write this, and scheduler.js still reads it —
 * config.telegram.{enabled,bot_token} and config.scheduler.morning_brief_recipients.
 * Dropping it would have silently killed the morning brief on every install, so it is
 * folded in here rather than replaced.
 *
 * This is the half of autonomy people forget: a desk that works all night is no use if
 * nobody is told there is something to approve.
 */
async function setupNotifications() {
  step(6, 'How you get told there is something to approve');
  const file = path.join(ROOT, 'config.json');
  const cfg = fs.existsSync(file) ? JSON.parse(fs.readFileSync(file, 'utf8')) : {};
  cfg.telegram = cfg.telegram || {};
  cfg.scheduler = cfg.scheduler || {};

  if (cfg.telegram.enabled && cfg.telegram.bot_token) {
    okline('Telegram already configured');
  } else if (AUTO) {
    warn('Skipped (--yes). Drafts still queue; you just will not be pinged.');
  } else {
    const want = await ask('Get a Telegram ping when a draft is ready? (y/n)', 'n');
    if (want.toLowerCase().startsWith('y')) {
      cfg.telegram.enabled = true;
      cfg.telegram.bot_token = await ask('Telegram bot token');
      const chat = await ask('Your chat id');
      cfg.scheduler.morning_brief_recipients = chat ? [chat] : [];
      // Prove it before claiming it works — a token that 401s is worse than none.
      if (cfg.telegram.bot_token) {
        try {
          const r = await fetch(`https://api.telegram.org/bot${cfg.telegram.bot_token}/getMe`);
          const j = await r.json();
          if (j.ok) okline(`Telegram bot verified: @${j.result.username}`);
          else { fail(`Telegram rejected the token: ${j.description || r.status}`); cfg.telegram.enabled = false; }
        } catch (e) { warn(`could not reach Telegram (${e.message}) — saved, verify later`); }
      }
    } else {
      cfg.telegram.enabled = false;
      okline('no push — check the queue with: npm run frontdesk -- --queue');
    }
  }
  fs.writeFileSync(file, JSON.stringify(cfg, null, 2));
}

/* ─────────────────────── 7. autostart ─────────────────────── */

function setupAutostart() {
  step(7, 'Run on its own (survives reboot)');
  const node = process.execPath;
  const daemon = path.join(ROOT, 'frontdesk-daemon.js');
  const logs = path.join(ROOT, 'logs');
  fs.mkdirSync(logs, { recursive: true });

  if (process.platform === 'darwin') {
    const plist = path.join(os.homedir(), 'Library', 'LaunchAgents', 'com.aixmos.frontdesk.plist');
    const xml = `<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict>
  <key>Label</key><string>com.aixmos.frontdesk</string>
  <key>ProgramArguments</key><array>
    <string>${node}</string><string>${daemon}</string>
  </array>
  <key>WorkingDirectory</key><string>${ROOT}</string>
  <key>RunAtLoad</key><true/>
  <key>KeepAlive</key><dict><key>SuccessfulExit</key><false/></dict>
  <key>StandardOutPath</key><string>${path.join(logs, 'frontdesk.log')}</string>
  <key>StandardErrorPath</key><string>${path.join(logs, 'frontdesk.err.log')}</string>
</dict></plist>`;
    fs.mkdirSync(path.dirname(plist), { recursive: true });
    fs.writeFileSync(plist, xml);
    sh(`launchctl unload ${JSON.stringify(plist)}`);
    const r = sh(`launchctl load ${JSON.stringify(plist)}`);
    const loaded = (sh('launchctl list') || '').includes('com.aixmos.frontdesk');
    // "installed" and "loaded" are different claims. Only report what launchctl confirms.
    if (loaded) okline('com.aixmos.frontdesk installed AND loaded');
    else fail(`plist written but launchctl did not load it${r ? `: ${r}` : ''}`);
    return;
  }

  if (process.platform === 'win32') {
    const cmd = `schtasks /create /tn "AIXMOS Front Desk" /tr "\\"${node}\\" \\"${daemon}\\"" /sc onlogon /rl highest /f`;
    const r = sh(cmd);
    const check = sh('schtasks /query /tn "AIXMOS Front Desk"');
    if (check) okline('scheduled task "AIXMOS Front Desk" installed (runs at logon)');
    else fail(`could not create the scheduled task${r ? `: ${r}` : ''}`);
    return;
  }
  warn(`autostart not implemented for ${process.platform} — run: node frontdesk-daemon.js`);
}

/* ─────────────────────── env file ─────────────────────── */

function readEnv() {
  const env = {};
  if (fs.existsSync(ENV_FILE)) {
    for (const line of fs.readFileSync(ENV_FILE, 'utf8').split('\n')) {
      const m = line.match(/^\s*([A-Z0-9_]+)\s*=\s*(.*)$/);
      if (m) env[m[1]] = m[2];
    }
  }
  for (const k of ['ANTHROPIC_API_KEY', 'AIXMOS_LICENSE_KEY', 'AIXMOS_GATEWAY_URL',
    'AIXMOS_LLM_BACKEND', 'OLLAMA_HOST', 'OLLAMA_MODEL', 'AIX_AGENT_TOKEN']) {
    if (process.env[k] && !env[k]) env[k] = process.env[k];
  }
  return env;
}

function writeEnv(env) {
  fs.mkdirSync(CFG, { recursive: true });
  const body = ['# AIXMOS — written by setup.js. Secrets live here, never in git.', '']
    .concat(Object.entries(env).map(([k, v]) => `${k}=${v}`)).join('\n') + '\n';
  fs.writeFileSync(ENV_FILE, body, { mode: 0o600 });
  // Make the values live for the doctor run that follows, so it probes what was just set.
  for (const [k, v] of Object.entries(env)) process.env[k] = v;
}

/* ─────────────────────── main ─────────────────────── */

async function main() {
  say(`${C.b}AIXMOS — setup${C.x}`);
  say(`${C.d}${ROOT}${C.x}`);

  if (ARGS.has('--autostart')) { setupAutostart(); return finish(); }
  if (ARGS.has('--doctor')) { readEnvIntoProcess(); return finish(); }

  const env = readEnv();
  installDeps();
  await setupBrain(env);
  await connectClaude(env);
  setupSecrets(env);
  writeEnv(env);
  okline(`config written: ${ENV_FILE}`);
  await setupProfile();
  await setupNotifications();
  setupAutostart();
  if (rl) rl.close();
  return finish();
}

function readEnvIntoProcess() {
  const env = readEnv();
  for (const [k, v] of Object.entries(env)) if (!process.env[k]) process.env[k] = v;
}

async function finish() {
  step(8, 'Verify — probing every wire');
  const doctor = require('./lib/doctor');
  const result = await doctor.run(ROOT);
  say('');
  say(doctor.render(result));
  say('');
  if (!result.ready) {
    say(`${C.r}${C.b}SETUP INCOMPLETE.${C.x} The checks above are not passing, so this is not`);
    say('a working install. Fix them and re-run:  node setup.js --doctor');
    process.exit(1);
  }
  say(`${C.g}${C.b}READY.${C.x} Every required wire was probed, not assumed.`);
  say('');
  say(`  ${C.b}Give it something to do${C.x}`);
  say(`    npm run frontdesk -- "+15715550100" "how much to detail my car?"`);
  say(`    npm run frontdesk -- --queue        ${C.d}what is waiting for you${C.x}`);
  say(`    npm run claims -- --self-test       ${C.d}prove the gate still refuses${C.x}`);
  say('');
  say(`  ${C.b}It is already running.${C.x} The front desk starts at boot, triages every`);
  say('  inbound, runs the agents, checks every draft, and queues it for you.');
  say(`  ${C.y}Nothing sends without you.${C.x} That is the design, not a setting.`);
  process.exit(0);
}

main().catch(e => { fail(e.message); process.exit(1); });
