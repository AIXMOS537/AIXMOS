#!/usr/bin/env node
'use strict';

/**
 * SEND-OFF CONTAINMENT INVARIANT (2026-09-16).
 *
 * Every way this relay normally starts must resolve to ALLOW_SEND=false and
 * AUTO_SEND_ASSISTANT=false. This is a phase invariant, not product behavior:
 * turning customer-facing send ON is a separately reviewed activation, and that
 * change must update this test on purpose.
 *
 *   node imessage-relay/send-safety-test.js
 */

const assert = require('assert');
const fs = require('fs');
const os = require('os');
const path = require('path');
const { execFileSync } = require('child_process');

const HERE = __dirname;
const REAL_HOME = os.homedir();
const failures = [];
const notes = [];
const check = (name, fn) => {
  try {
    const skipped = fn();
    notes.push(`${skipped === 'skip' ? 'SKIP' : 'PASS'}  ${name}`);
  } catch (err) {
    failures.push(`FAIL  ${name}: ${err.message}`);
  }
};

const tmp = fs.mkdtempSync(path.join(os.tmpdir(), 'imessage-send-safety-'));
process.env.IMESSAGE_ASSISTANT_ROOT = tmp; // empty root: loadConfig falls back to shipped defaults
delete process.env.IMESSAGE_ALLOW_SEND;
delete process.env.IMESSAGE_AUTO_ASSISTANT;
const { loadConfig } = require('./lib/paths');
const { sendState, sendAllowed } = require('./lib/pipeline');

function launcherEnv(file) {
  const env = {};
  for (const line of fs.readFileSync(file, 'utf8').split('\n')) {
    const m = line.match(/^\s*export\s+(IMESSAGE_(?:ALLOW_SEND|AUTO_ASSISTANT))=([^\s#]*)/);
    if (m) env[m[1]] = m[2];
  }
  return env;
}

function plistEnv(file) {
  const json = execFileSync('/usr/bin/plutil', ['-convert', 'json', '-o', '-', file], { encoding: 'utf8' });
  const p = JSON.parse(json);
  return { env: p.EnvironmentVariables || {}, disabled: p.Disabled === true };
}

function assertOff(label, config, env) {
  const s = sendState(config, env);
  assert.strictEqual(s.allow_send, false, `${label}: ALLOW_SEND resolved true`);
  assert.strictEqual(s.auto_send_assistant, false, `${label}: AUTO_SEND_ASSISTANT resolved true`);
  const gate = sendAllowed({ tier: 'T1' }, config, { ...env, IMESSAGE_KILL: '0' });
  assert.strictEqual(gate.ok, false, `${label}: T1 send gate opened`);
}

const shippedConfig = loadConfig();

for (const rel of ['bin/run-live.sh', 'bin/bind-via-terminal.sh', 'bin/bind-via-terminal.command']) {
  check(`launcher ${rel} starts with send OFF`, () => {
    const env = launcherEnv(path.join(HERE, rel));
    assert.strictEqual(env.IMESSAGE_ALLOW_SEND, '0', 'IMESSAGE_ALLOW_SEND export missing or not 0');
    assert.strictEqual(env.IMESSAGE_AUTO_ASSISTANT, '0', 'IMESSAGE_AUTO_ASSISTANT export missing or not 0');
    assertOff(rel, shippedConfig, env);
  });
}

check('repo launchd plist (what install-mac.sh installs) starts with send OFF', () => {
  const { env } = plistEnv(path.join(HERE, 'com.tmmt.imessage-relay.plist'));
  assertOff('repo plist', shippedConfig, env);
});

check('config.example.json + empty config resolve send OFF', () => {
  const ex = JSON.parse(fs.readFileSync(path.join(HERE, 'config.example.json'), 'utf8'));
  assert.notStrictEqual(ex.allow_send, true, 'example allow_send true');
  assert.notStrictEqual(ex.auto_send_assistant, true, 'example auto_send_assistant true');
  assertOff('shipped defaults', shippedConfig, {});
});

// Installed state on THIS Mac — skipped where the relay is not installed.
check('installed launchd plist on this Mac starts with send OFF', () => {
  const f = path.join(REAL_HOME, 'Library', 'LaunchAgents', 'com.tmmt.imessage-relay.plist');
  if (!fs.existsSync(f)) return 'skip';
  const liveCfgFile = path.join(REAL_HOME, '.config', 'tmmt', 'imessage-assistant', 'config.json');
  const liveCfg = fs.existsSync(liveCfgFile) ? JSON.parse(fs.readFileSync(liveCfgFile, 'utf8')) : {};
  assertOff('installed plist + live config.json', liveCfg, plistEnv(f).env);
  return undefined;
});

check('installed bind-term keepalive is disabled or send OFF', () => {
  const f = path.join(REAL_HOME, 'Library', 'LaunchAgents', 'com.tmmt.imessage-bind-term.plist');
  if (!fs.existsSync(f)) return 'skip';
  const { disabled } = plistEnv(f);
  if (!disabled) {
    const env = launcherEnv(path.join(HERE, 'bin', 'bind-via-terminal.sh'));
    assertOff('bind-term enabled', {}, env);
  }
  return undefined;
});

console.log(notes.concat(failures).join('\n'));
fs.rmSync(tmp, { recursive: true, force: true });
if (failures.length) {
  console.error(`\nSEND-SAFETY FAIL — ${failures.length} failing. Send must stay OFF until a reviewed activation.`);
  process.exit(1);
}
console.log('\nSEND-SAFETY PASS — every normal start path resolves ALLOW_SEND=false, AUTO_SEND_ASSISTANT=false');
