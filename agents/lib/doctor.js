'use strict';
/**
 * DOCTOR — does this install actually work, or does it merely look installed?
 *
 * WHY THIS EXISTS. `install-mac.sh` copied files, ran npm install, printed a green banner,
 * and then told the operator to go install Ollama themselves and `ollama pull llama3.1:8b`
 * — a model tag that exists on none of the fleet's machines. The banner said the install
 * succeeded. Nothing had ever asked the brain a question, checked that a key was valid, or
 * confirmed a single gate would refuse anything.
 *
 * Every check below PROBES. It sends a real request, reads a real file, or asks a real gate
 * to refuse something. None of them infer health from the presence of a binary or a config
 * key, because "the file is there" and "it works" are different claims and only one of them
 * is worth printing.
 *
 * NO GREEN OVER A DEAD STEP. A check that cannot run reports UNKNOWN, never PASS. A required
 * check that fails makes the whole run fail, and the summary says so in the first line
 * rather than the last.
 */

const fs = require('fs');
const path = require('path');
const os = require('os');
const { execSync } = require('child_process');

const REQUIRED_NODE_MAJOR = 18;

/* ─────────────────────────── helpers ─────────────────────────── */

const ok = (name, detail, extra = {}) => ({ name, state: 'PASS', detail, ...extra });
const bad = (name, detail, fix, extra = {}) => ({ name, state: 'FAIL', detail, fix, ...extra });
const unknown = (name, detail, fix, extra = {}) => ({ name, state: 'UNKNOWN', detail, fix, ...extra });
const skip = (name, detail) => ({ name, state: 'SKIP', detail });

function which(bin) {
  try {
    return execSync(process.platform === 'win32' ? `where ${bin}` : `command -v ${bin}`,
      { stdio: ['ignore', 'pipe', 'ignore'] }).toString().trim().split('\n')[0] || null;
  } catch { return null; }
}

async function httpJson(url, opts = {}, timeoutMs = 8000) {
  const ac = new AbortController();
  const t = setTimeout(() => ac.abort(), timeoutMs);
  try {
    const res = await fetch(url, { ...opts, signal: ac.signal });
    const text = await res.text();
    let json = null;
    try { json = JSON.parse(text); } catch { /* not json */ }
    return { status: res.status, ok: res.ok, json, text };
  } finally { clearTimeout(t); }
}

/* ─────────────────────────── checks ─────────────────────────── */

async function checkNode() {
  const major = parseInt(process.versions.node.split('.')[0], 10);
  return major >= REQUIRED_NODE_MAJOR
    ? ok('node', `v${process.versions.node}`)
    : bad('node', `v${process.versions.node} — too old`,
      `install Node ${REQUIRED_NODE_MAJOR}+ (the bundled installer is in _installers/)`);
}

async function checkDeps(root) {
  const p = path.join(root, 'node_modules', '@anthropic-ai', 'sdk');
  return fs.existsSync(p)
    ? ok('dependencies', '@anthropic-ai/sdk present')
    : bad('dependencies', '@anthropic-ai/sdk missing', 'run: npm install   (needs internet once)');
}

async function checkProfile() {
  const { loadProfile } = require('./profile');
  const p = loadProfile();
  if (p.source === 'invalid') {
    return bad('business profile', 'the profile file exists but is not valid JSON',
      'fix config/business-profile.json — a malformed profile silently names nothing');
  }
  if (p.source === 'default') {
    return unknown('business profile', 'NO profile — agents will not know whose business this is',
      'copy config/business-profile.example.json -> config/business-profile.json and fill it in');
  }
  const card = Array.isArray(p.rate_card) ? p.rate_card.length : 0;
  const detail = `${p.business_name || '(unnamed)'} · vertical: ${p.industry_pack || 'none'} · rate card: ${card}`;
  if (!card) {
    return unknown('business profile', `${detail} — with no rate card the agents cannot quote at all`,
      'add "rate_card": [{"item":"…","price":"$0"}] — the claims gate refuses every price without it');
  }
  return ok('business profile', detail);
}

/** The claims gate must be watched REFUSING on THIS install, not asserted to exist. */
async function checkClaimsGate() {
  try {
    const { checkClaims } = require('./claims');
    const mustRefuse = checkClaims('Results guaranteed, and I can do it for $173.50.');
    const mustPass = checkClaims('Happy to help — let me confirm and come right back to you.');
    if (mustRefuse.ok) {
      return bad('claims gate', 'it ALLOWED an invented price and a guarantee',
        'the gate is not working — do not send from this install');
    }
    if (!mustPass.ok) {
      return bad('claims gate', 'it blocked an ordinary reply — it will be switched off in a week',
        'check rate_card / claims.allow_phrases in the business profile');
    }
    return ok('claims gate', `live — refused ${mustRefuse.violations.length} in the probe, allowed a clean reply`);
  } catch (e) {
    return bad('claims gate', `could not run: ${e.message}`, 'lib/claims.js is missing or broken');
  }
}

/** The DNC gate must fail CLOSED on an unreadable list. */
async function checkDncGate() {
  const dir = process.env.AIXMOS_STATE_DIR || path.join(os.homedir(), '.aixmos');
  const file = path.join(dir, 'do-not-contact.json');
  const had = fs.existsSync(file);
  const backup = had ? fs.readFileSync(file) : null;
  try {
    fs.mkdirSync(dir, { recursive: true });
    fs.writeFileSync(file, '{ this is not json');
    const { isSuppressed } = require('./suppression');
    let failedClosed = false;
    try { isSuppressed('+15555550123'); } catch (e) { failedClosed = e.code === 'DNC_UNREADABLE'; }
    return failedClosed
      ? ok('do-not-contact gate', 'fails CLOSED on an unreadable list (probed)')
      : bad('do-not-contact gate', 'an unreadable list did NOT refuse — it reads as "nobody opted out"',
        'lib/suppression.js must throw DNC_UNREADABLE');
  } catch (e) {
    return unknown('do-not-contact gate', `could not probe: ${e.message}`, 'check write access to ' + dir);
  } finally {
    try { if (had) fs.writeFileSync(file, backup); else fs.rmSync(file, { force: true }); } catch { /* best effort */ }
  }
}

/** Ask the configured brain a real question and require a real answer. */
async function checkBrain() {
  const llm = require('./llm');
  const backend = llm.backend();

  if (backend === 'ollama' || backend === 'auto') {
    const host = llm.OLLAMA_HOST();
    const want = llm.DEFAULT_OLLAMA_MODEL();
    let tags;
    try {
      tags = await httpJson(`${host}/api/tags`, {}, 6000);
    } catch (e) {
      const r = bad('local brain (ollama)', `not reachable at ${host}`,
        'start it: ollama serve   (or set OLLAMA_HOST to the machine running it)');
      if (backend === 'auto') r.state = 'UNKNOWN';
      return r;
    }
    const names = (tags.json?.models || []).map(m => m.name);
    if (!names.length) {
      return bad('local brain (ollama)', `reachable at ${host} but NO models installed`,
        `pull one: ollama pull ${want}`);
    }
    if (!names.includes(want)) {
      return bad('local brain (ollama)',
        `OLLAMA_MODEL is "${want}" which is NOT installed. Installed: ${names.slice(0, 6).join(', ')}`,
        `either  ollama pull ${want}   or set OLLAMA_MODEL to one of the installed tags. `
        + 'A tag that is not installed fails silently — the lane just returns nothing.');
    }
    // It exists. Now make it actually answer.
    try {
      const out = await llm.callOllama({ system: 'Reply with the single word: ready',
        prompt: 'Say ready.', maxTokens: 2000 });
      return String(out).trim()
        ? ok('local brain (ollama)', `${want} answered on ${host}`)
        : bad('local brain (ollama)', `${want} returned an EMPTY completion`,
          'raise OLLAMA_MIN_PREDICT — a reasoning model can spend the whole budget thinking');
    } catch (e) {
      return bad('local brain (ollama)', `${want} failed to answer: ${e.message}`,
        'check the model is not mid-download and the host has RAM free');
    }
  }
  return skip('local brain (ollama)', `backend is "${backend}" — local lane not in use`);
}

/** Is the paid lane actually connected — key valid, or gateway licence active? */
async function checkClaude() {
  const key = (process.env.ANTHROPIC_API_KEY || '').trim();
  const gw = (process.env.AIXMOS_GATEWAY_URL || '').trim();
  const lic = (process.env.AIXMOS_LICENSE_KEY || process.env.LICENSE_KEY || '').trim();

  if (gw || lic) {
    const base = gw || 'https://aixmos-gateway.aixmos.workers.dev';
    try {
      const r = await httpJson(`${base}/wallet`, { headers: { 'x-aixmos-auth': lic } }, 10000);
      if (r.status === 200) return ok('Claude (via AIXMOS gateway)', `licence ACTIVE at ${base}`);
      if (r.status === 401) {
        return bad('Claude (via AIXMOS gateway)', `licence REJECTED (401) at ${base}`,
          'the key is missing, wrong, or revoked — contact the provider');
      }
      return unknown('Claude (via AIXMOS gateway)', `gateway returned ${r.status}`, `check ${base}`);
    } catch (e) {
      return unknown('Claude (via AIXMOS gateway)', `gateway unreachable: ${e.message}`,
        'the army keeps working on the local lane; the licence re-checks when the network returns');
    }
  }

  if (!key) {
    return unknown('Claude (direct API key)', 'ANTHROPIC_API_KEY not set',
      'set it in config/aixmos.env, OR connect via an AIXMOS licence key. '
      + 'Without either, only the local lane works.');
  }
  // Cheapest possible real probe: count tokens. Costs nothing, proves the key.
  try {
    const r = await httpJson('https://api.anthropic.com/v1/messages/count_tokens', {
      method: 'POST',
      headers: { 'content-type': 'application/json', 'x-api-key': key, 'anthropic-version': '2023-06-01' },
      body: JSON.stringify({ model: 'claude-opus-5', messages: [{ role: 'user', content: 'hi' }] }),
    }, 12000);
    if (r.status === 200) return ok('Claude (direct API key)', 'key VALID (token-count probe)');
    if (r.status === 401) return bad('Claude (direct API key)', 'key REJECTED (401)', 'the key is wrong or revoked');
    return unknown('Claude (direct API key)', `probe returned ${r.status}: ${String(r.text).slice(0, 120)}`,
      'check the key and the network');
  } catch (e) {
    return unknown('Claude (direct API key)', `could not probe: ${e.message}`, 'offline? the local lane still works');
  }
}

/** Can the front desk actually write to its queue? An unwritable queue loses work silently. */
async function checkQueue() {
  const fd = require('./frontdesk');
  try {
    fs.mkdirSync(fd.QUEUE_DIR, { recursive: true });
    const probe = path.join(fd.QUEUE_DIR, '.doctor-probe');
    fs.writeFileSync(probe, 'probe');
    fs.rmSync(probe);
    const waiting = fd.listQueue().length;
    return ok('front desk queue', `writable · ${waiting} item(s) waiting · ${fd.QUEUE_DIR}`);
  } catch (e) {
    return bad('front desk queue', `NOT writable: ${e.message}`,
      `fix permissions on ${fd.QUEUE_DIR} — an unwritable queue silently loses every draft`);
  }
}

/** Route an inbound through the desk with a stub brain — proves the wiring, not the model. */
async function checkFrontDesk() {
  try {
    const fd = require('./frontdesk');
    const t = await fd.triage('how much to detail a car?', { run: async () => 'quote' });
    if (t.lane !== 'quote') return bad('front desk routing', `a price question routed to "${t.lane}"`, 'lib/frontdesk.js LANES are wrong');
    const stop = await fd.handleInbound({ from: '+15555550199', text: 'STOP' },
      { run: async () => { throw new Error('a STOP must never call a model'); }, queue: false });
    return stop.status === 'OPTED_OUT'
      ? ok('front desk routing', 'triage + STOP short-circuit both verified')
      : bad('front desk routing', `a STOP produced status "${stop.status}"`, 'the opt-out path is broken');
  } catch (e) {
    return bad('front desk routing', `could not run: ${e.message}`, 'lib/frontdesk.js is broken');
  }
}

/** Outbound channels are optional — but say plainly which are live. */
async function checkChannels() {
  try {
    const { channelStatus } = require('./sender');
    // channelStatus() returns an ARRAY of {channel, configured, detail} — not an object.
    // Object.entries() on it would have reported channel "0", "1", "2".
    const st = channelStatus();
    const live = st.filter(c => c.configured).map(c => c.channel);
    return live.length
      ? ok('outbound channels', `configured: ${live.join(', ')} (nothing auto-sends)`)
      : unknown('outbound channels', 'none configured — drafts queue but cannot be delivered',
        'set GHL / Twilio / iMessage credentials in config/aixmos.env when ready');
  } catch (e) {
    return unknown('outbound channels', `could not read: ${e.message}`, '');
  }
}

/** Does the desk come back up by itself after a reboot? */
async function checkAutostart() {
  if (process.platform === 'darwin') {
    const p = path.join(os.homedir(), 'Library', 'LaunchAgents', 'com.aixmos.frontdesk.plist');
    if (!fs.existsSync(p)) return unknown('autostart', 'not installed — the desk will not survive a reboot', 'run: node setup.js --autostart');
    try {
      const loaded = execSync('launchctl list', { stdio: ['ignore', 'pipe', 'ignore'] }).toString();
      return loaded.includes('com.aixmos.frontdesk')
        ? ok('autostart', 'com.aixmos.frontdesk installed AND loaded')
        : bad('autostart', 'plist exists but is NOT loaded — installed is not the same as running',
          'launchctl load ~/Library/LaunchAgents/com.aixmos.frontdesk.plist');
    } catch { return unknown('autostart', 'plist present; could not read launchctl', ''); }
  }
  if (process.platform === 'win32') {
    try {
      const out = execSync('schtasks /query /tn "AIXMOS Front Desk"', { stdio: ['ignore', 'pipe', 'ignore'] }).toString();
      return /AIXMOS Front Desk/.test(out)
        ? ok('autostart', 'scheduled task "AIXMOS Front Desk" present')
        : unknown('autostart', 'task not found', 'run: node setup.js --autostart');
    } catch { return unknown('autostart', 'not installed — the desk will not survive a reboot', 'run: node setup.js --autostart'); }
  }
  return skip('autostart', `not implemented for ${process.platform}`);
}

/* ─────────────────────────── run ─────────────────────────── */

const REQUIRED = new Set(['node', 'dependencies', 'claims gate', 'do-not-contact gate',
  'front desk queue', 'front desk routing']);

async function run(root = path.join(__dirname, '..')) {
  const checks = [];
  const add = async (fn, ...a) => { try { checks.push(await fn(...a)); } catch (e) { checks.push(bad(fn.name, e.message, '')); } };

  await add(checkNode);
  await add(checkDeps, root);
  await add(checkProfile);
  await add(checkClaimsGate);
  await add(checkDncGate);
  await add(checkFrontDesk);
  await add(checkQueue);
  await add(checkBrain);
  await add(checkClaude);
  await add(checkChannels);
  await add(checkAutostart);

  // A brain is required in SOME form: if neither lane works, nothing works.
  const brain = checks.find(c => c.name.startsWith('local brain'));
  const claude = checks.find(c => c.name.startsWith('Claude'));
  const anyBrain = [brain, claude].some(c => c && c.state === 'PASS');
  checks.push(anyBrain
    ? ok('a brain is reachable', 'at least one lane answered')
    : bad('a brain is reachable', 'NEITHER the local lane nor Claude is working',
      'fix one of the two above — with no brain the agents cannot draft anything'));

  const failed = checks.filter(c => c.state === 'FAIL');
  const required = checks.filter(c => REQUIRED.has(c.name) || c.name === 'a brain is reachable');
  const requiredFailed = required.filter(c => c.state !== 'PASS');

  return { checks, failed, requiredFailed, ready: requiredFailed.length === 0 };
}

function render(result) {
  const icon = { PASS: '✅', FAIL: '❌', UNKNOWN: '⚠️ ', SKIP: '·  ' };
  const lines = [];
  lines.push(result.ready
    ? '✅ READY — every required wire verified by probe'
    : `❌ NOT READY — ${result.requiredFailed.length} required check(s) not passing`);
  lines.push('');
  for (const c of result.checks) {
    lines.push(`  ${icon[c.state] || '?'} ${c.name.padEnd(28)} ${c.detail}`);
    if (c.state !== 'PASS' && c.fix) lines.push(`       → ${c.fix}`);
  }
  lines.push('');
  const n = result.checks.length;
  const p = result.checks.filter(c => c.state === 'PASS').length;
  lines.push(`  ${p}/${n} passed · ${result.checks.filter(c => c.state === 'FAIL').length} failed`
    + ` · ${result.checks.filter(c => c.state === 'UNKNOWN').length} unknown`);
  if (!result.ready) {
    lines.push('');
    lines.push('  Nothing is "installed" until these pass. An UNKNOWN is not a PASS.');
  }
  return lines.join('\n');
}

module.exports = { run, render };
