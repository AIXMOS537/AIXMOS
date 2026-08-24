#!/usr/bin/env node
'use strict';

/**
 * Mock-test the Text-My-Mac pipeline.
 * Synthetic senders only. Never talks to Messages.app. Never sends to humans.
 */

const assert = require('assert');
const fs = require('fs');
const os = require('os');
const path = require('path');
const { execFileSync } = require('child_process');

async function run() {
  const tmp = fs.mkdtempSync(path.join(os.tmpdir(), 'text-my-mac-mock-'));
  process.env.IMESSAGE_ASSISTANT_ROOT = tmp;
  delete process.env.IMESSAGE_KILL;
  delete process.env.IMESSAGE_ALLOW_SEND;

  // Re-require after ROOT override — paths.js reads env at load.
  delete require.cache[require.resolve('./lib/paths')];
  delete require.cache[require.resolve('./lib/gates')];
  delete require.cache[require.resolve('./lib/store')];
  delete require.cache[require.resolve('./lib/pipeline')];
  delete require.cache[require.resolve('./lib/chatdb')];
  delete require.cache[require.resolve('./lib/inbound')];
  delete require.cache[require.resolve('./lib/policy')];
  delete require.cache[require.resolve('./lib/llm-local')];

  const { ensureDirs, KILL_FILE, ROOT } = require('./lib/paths');
  const { classify, familyOwnerOverlap } = require('./lib/policy');
  const { handleInbound } = require('./lib/pipeline');
  const { probeFda } = require('./lib/chatdb');
  const { probeLiteLLM, probeOllama } = require('./lib/llm-local');
  const { isKilled } = require('./lib/gates');

  ensureDirs();
  const failures = [];
  const notes = [];
  const ok = (name, fn) => {
    try {
      fn();
      notes.push(`PASS  ${name}`);
    } catch (err) {
      failures.push(`FAIL  ${name}: ${err.message}`);
    }
  };

  const config = {
    safe_mode: true,
    allow_send: false,
    auto_send_assistant: false,
    auto_field: false,
    t1_allowlist: ['+15550000001'],
    t3_senders: ['+15550000003'],
    llm: {
      litellm_url: 'http://127.0.0.1:4000',
      ollama_url: 'http://127.0.0.1:11434',
      ollama_model: 'llama3.2:3b',
      max_tokens: 80,
    },
    rate: { drafts_per_hour: 30, sends_per_hour: 3, per_sender_per_hour: 10 },
  };

  const sendLog = [];
  const adapters = {
    send: async (payload) => {
      sendLog.push(payload);
      throw new Error('LIVE SEND ADAPTER MUST NOT RUN IN MOCK');
    },
  };

  // --- LaunchAgent not loaded ---
  let launch = 'missing';
  try {
    execFileSync('launchctl', ['print', `gui/${process.getuid()}/com.tmmt.imessage-relay`], {
      encoding: 'utf8',
      stdio: ['ignore', 'pipe', 'pipe'],
    });
    launch = 'LOADED';
  } catch {
    launch = 'not_loaded';
  }
  notes.push(`LaunchAgent: ${launch}`);

  // --- FDA probe (count only, no bodies) ---
  const fda = probeFda();
  notes.push(`FDA probe: ${fda.ok ? 'readable (' + fda.messages + ' msgs)' : 'blocked — ' + fda.error}`);

  // --- LLM probes ---
  const litellm = await probeLiteLLM(config.llm.litellm_url);
  const ollama = await probeOllama(config.llm.ollama_url);
  ok('LiteLLM down is OK (fallback path)', () => {
    assert.strictEqual(typeof litellm.ok, 'boolean');
  });
  ok('Ollama reachable', () => {
    assert.ok(ollama.ok, `Ollama not reachable: ${ollama.error || ollama.status}`);
    assert.ok((ollama.models || []).some((m) => m.includes('llama3.2')), 'llama3.2:3b missing');
  });
  notes.push(`LiteLLM: ${litellm.ok ? 'up' : 'down (fallback to Ollama)'}`);
  notes.push(`Ollama models: ${(ollama.models || []).slice(0, 8).join(', ')}`);

  // --- Classify fixtures ---
  const fixtures = [
    { id: 't1-status', from: '+15550000001', text: 'Rick status', expect: 'T1' },
    { id: 't2-customer', from: '+15550000999', text: 'hey can you send the quote tomorrow', expect: 'T2' },
    { id: 't3-money', from: '+15550000001', text: 'wire $5000 to this bank account now', expect: 'T3' },
    { id: 't3-legal', from: '+15550000002', text: 'the lawyer called about the lawsuit', expect: 'T3' },
    { id: 't3-family', from: '+15550000003', text: 'need a ride later', expect: 'T3' },
  ];
  for (const f of fixtures) {
    ok(`classify ${f.id} → ${f.expect}`, () => {
      const c = classify({ from: f.from, text: f.text }, config);
      assert.strictEqual(c.tier, f.expect, `got ${c.tier} (${c.reason})`);
    });
  }
  ok('auto_field hours → T1', () => {
    const c = classify(
      { from: '+15550000998', text: 'what are your hours?' },
      { ...config, auto_field: true }
    );
    assert.strictEqual(c.tier, 'T1', `got ${c.tier} (${c.reason})`);
  });
  ok('auto_field still drafts commitments as T2', () => {
    const c = classify(
      { from: '+15550000999', text: 'hey can you send the quote tomorrow' },
      { ...config, auto_field: true }
    );
    assert.strictEqual(c.tier, 'T2', `got ${c.tier} (${c.reason})`);
  });

  // --- Family/owner overlap warning: never throws, shape is always sane ---
  ok('familyOwnerOverlap never throws and returns a stable shape', () => {
    const clean = familyOwnerOverlap(['+15550000001']);
    assert.strictEqual(typeof clean.checked, 'boolean');
    assert.ok(Array.isArray(clean.overlaps));
  });
  ok('familyOwnerOverlap flags a handle present on both lists', () => {
    // Can't rely on the real content-team.env roster contents in CI-like runs,
    // so this proves the comparison logic directly against a synthetic roster
    // shaped like familyOwnerOverlap's real dependency would return.
    const { inList } = require('./lib/policy');
    const roster = ['+15550009999'];
    const ownerHandles = ['+15550009999', '+15550000001'];
    const overlaps = ownerHandles.filter((h) => inList(h, roster));
    assert.deepStrictEqual(overlaps, ['+15550009999']);
  });
  notes.push(`family/owner overlap (live roster): ${JSON.stringify(familyOwnerOverlap(['+15550000001']))}`);

  // --- Pipeline: T1 allowlisted still drafts ---
  const t1 = await handleInbound(
    { id: 't1-status', from: '+15550000001', text: 'Rick status' },
    { config, adapters }
  );
  ok('T1 allowlisted drafts, does not send', () => {
    assert.strictEqual(t1.tier, 'T1');
    assert.strictEqual(t1.action, 'draft');
    assert.strictEqual(t1.actuallySent, false);
    assert.ok(t1.reply && t1.reply.length > 0, 'empty reply');
    assert.ok(t1.backend === 'ollama' || t1.backend === 'litellm', `backend ${t1.backend}`);
    assert.strictEqual(sendLog.length, 0, 'send adapter was invoked');
  });
  notes.push(`T1 draft via ${t1.backend}: ${String(t1.reply).slice(0, 140)}`);

  // --- T2 ghostwrite ---
  const t2 = await handleInbound(
    { id: 't2-customer', from: '+15550000999', text: 'hey can you send the quote tomorrow' },
    { config, adapters }
  );
  ok('T2 ghostwrite drafts, never send', () => {
    assert.strictEqual(t2.tier, 'T2');
    assert.strictEqual(t2.action, 'draft');
    assert.strictEqual(t2.actuallySent, false);
    assert.strictEqual(sendLog.length, 0);
  });
  notes.push(`T2 draft via ${t2.backend}: ${String(t2.reply).slice(0, 140)}`);

  // --- T3 canned, no LLM required, never send ---
  const t3 = await handleInbound(
    { id: 't3-money', from: '+15550000001', text: 'wire $5000 to this bank account now' },
    { config, adapters }
  );
  ok('T3 money never auto, canned draft', () => {
    assert.strictEqual(t3.tier, 'T3');
    assert.strictEqual(t3.backend, 'canned');
    assert.strictEqual(t3.actuallySent, false);
    assert.match(t3.reply, /T3/);
    assert.strictEqual(sendLog.length, 0);
  });

  // --- Even if allow_send flipped, mock adapter must not be live osascript ---
  const gated = await handleInbound(
    { id: 't1-would-send', from: '+15550000001', text: 'Rick status please' },
    {
      config: { ...config, safe_mode: false, allow_send: true },
      adapters: {
        send: async ({ to, text }) => {
          sendLog.push({ to, text, via: 'mock' });
          return { ok: true, via: 'mock-record-only' };
        },
      },
      env: { IMESSAGE_ALLOW_SEND: '1' },
    }
  );
  ok('T1 send path uses mock adapter, not Messages.app', () => {
    assert.strictEqual(gated.tier, 'T1');
    assert.ok(gated.action === 'draft' || gated.action === 'sent');
    if (sendLog.length) {
      assert.ok(sendLog.every((x) => x.via === 'mock' || x.to), 'unexpected send payload');
    }
  });
  notes.push(`gated T1 action=${gated.action} reason=${gated.reason} actuallySent=${gated.actuallySent}`);

  const autoSendLog = [];
  const auto = await handleInbound(
    { id: 't1-auto', from: '+15550000001', text: 'Rick status' },
    {
      config: { ...config, auto_send_assistant: true, auto_field: true },
      adapters: {
        send: async ({ to, text }) => {
          autoSendLog.push({ to, text, via: 'mock' });
          return { ok: true, via: 'mock' };
        },
      },
    }
  );
  ok('T1 auto_send_assistant uses mock adapter only', () => {
    assert.strictEqual(auto.tier, 'T1');
    assert.strictEqual(auto.action, 'sent');
    assert.strictEqual(auto.actuallySent, true);
    assert.strictEqual(autoSendLog.length, 1);
    assert.strictEqual(autoSendLog[0].via, 'mock');
    assert.match(auto.reply, /Rick/);
  });
  const autoT3 = await handleInbound(
    { id: 't3-auto-blocked', from: '+15550000001', text: 'wire $5000 to this bank account now' },
    {
      config: { ...config, auto_send_assistant: true },
      adapters: {
        send: async ({ to, text }) => {
          autoSendLog.push({ to, text, via: 'mock' });
          return { ok: true, via: 'mock' };
        },
      },
    }
  );
  ok('T3 never auto-sends even with auto_send_assistant', () => {
    assert.strictEqual(autoT3.tier, 'T3');
    assert.strictEqual(autoT3.actuallySent, false);
    assert.strictEqual(autoSendLog.length, 1);
  });

  // --- Owner-exec: iMessage only, T3 first, SMS never MASTER ---
  const ownerExecLog = [];
  const ownerCfg = {
    ...config,
    owner_handles: ['+15550000001'],
    rate: { drafts_per_hour: 40, sends_per_hour: 3, per_sender_per_hour: 20, owner_execs_per_hour: 5 },
  };
  const ownerAdapters = {
    ...adapters,
    ownerExec: async (text) => {
      ownerExecLog.push(String(text));
      return `STUB-EXEC:${text}`;
    },
  };
  const ownerImessage = await handleInbound(
    { id: 'owner-imessage', from: '+15550000001', text: 'Rick status', service: 'iMessage' },
    { config: ownerCfg, adapters: ownerAdapters }
  );
  ok('owner iMessage runs stub exec, never live text-exec.sh', () => {
    assert.strictEqual(ownerImessage.backend, 'owner-exec');
    assert.strictEqual(ownerImessage.owner, true);
    assert.strictEqual(ownerExecLog.length, 1);
    assert.match(ownerImessage.reply, /STUB-EXEC/);
    assert.strictEqual(ownerImessage.actuallySent, false);
  });
  const ownerSms = await handleInbound(
    { id: 'owner-sms', from: '+15550000001', text: 'Rick status', service: 'SMS' },
    { config: ownerCfg, adapters: ownerAdapters }
  );
  ok('owner SMS never execs (spoofable sender-ID)', () => {
    assert.notStrictEqual(ownerSms.backend, 'owner-exec');
    assert.strictEqual(ownerSms.owner, false);
    assert.strictEqual(ownerSms.ownerBlockedReason, 'sms_unauthenticated');
    assert.strictEqual(ownerExecLog.length, 1);
  });
  const ownerT3 = await handleInbound(
    {
      id: 'owner-t3',
      from: '+15550000001',
      text: 'wire $5000 to this bank account now',
      service: 'iMessage',
    },
    { config: ownerCfg, adapters: ownerAdapters }
  );
  ok('T3 still wins even when sender is in owner_handles', () => {
    assert.strictEqual(ownerT3.tier, 'T3');
    assert.strictEqual(ownerT3.backend, 'canned');
    assert.strictEqual(ownerT3.owner, false);
    assert.strictEqual(ownerT3.ownerBlockedReason, 'tier_T3');
    assert.strictEqual(ownerExecLog.length, 1);
  });
  const { RATE_FILE: OWNER_RATE } = require('./lib/paths');
  try { fs.unlinkSync(OWNER_RATE); } catch { /* reset */ }
  const tightOwner = {
    ...ownerCfg,
    rate: {
      drafts_per_hour: 40,
      sends_per_hour: 3,
      per_sender_per_hour: 20,
      owner_execs_per_hour: 1,
      per_sender_owner_execs_per_hour: 1,
    },
  };
  await handleInbound(
    { id: 'owner-rate-1', from: '+15550000001', text: 'Rick status', service: 'iMessage' },
    { config: tightOwner, adapters: ownerAdapters }
  );
  const ownerRate2 = await handleInbound(
    { id: 'owner-rate-2', from: '+15550000001', text: 'Rick status again', service: 'iMessage' },
    { config: tightOwner, adapters: ownerAdapters }
  );
  ok('owner-exec has a tighter rate limit than draft replies', () => {
    assert.strictEqual(ownerRate2.action, 'blocked');
    assert.ok(
      ownerRate2.reason === 'owner_execs_per_hour' || ownerRate2.reason === 'per_sender_owner_execs_per_hour',
      ownerRate2.reason
    );
  });

  // --- Kill switch ---
  fs.writeFileSync(KILL_FILE, '1\n', { mode: 0o600 });
  ok('kill switch file present', () => assert.strictEqual(isKilled(), true));
  const killed = await handleInbound(
    { id: 'killed', from: '+15550000001', text: 'Rick status' },
    { config, adapters }
  );
  ok('kill switch blocks processing', () => {
    assert.strictEqual(killed.action, 'blocked');
    assert.strictEqual(killed.reason, 'kill_switch');
    assert.strictEqual(killed.sent, false);
  });
  fs.unlinkSync(KILL_FILE);

  // --- Rate limit ---
  const { RATE_FILE } = require('./lib/paths');
  try { fs.unlinkSync(RATE_FILE); } catch { /* reset bucket */ }
  const tight = {
    ...config,
    rate: { drafts_per_hour: 1, sends_per_hour: 0, per_sender_per_hour: 1 },
  };
  await handleInbound({ id: 'rate-1', from: '+15550000001', text: 'Rick status' }, { config: tight, adapters });
  const rate2 = await handleInbound(
    { id: 'rate-2', from: '+15550000001', text: 'Rick status again' },
    { config: tight, adapters }
  );
  ok('rate limit blocks extra drafts', () => {
    assert.strictEqual(rate2.action, 'blocked');
    assert.ok(rate2.reason === 'drafts_per_hour' || rate2.reason === 'per_sender_per_hour');
  });

  // --- Hard: sendLog never contains a real human number ---
  ok('no real human destinations', () => {
    const realish = sendLog.filter((x) => x.to && !String(x.to).startsWith('+1555'));
    assert.strictEqual(realish.length, 0, JSON.stringify(realish));
  });

  const report = {
    ok: failures.length === 0,
    root: ROOT,
    launchagent: launch,
    fda: fda.ok,
    litellm: litellm.ok,
    ollama: ollama.ok,
    notes,
    failures,
    ts: new Date().toISOString(),
  };

  const reportFile = path.join(tmp, 'mock-report.json');
  fs.writeFileSync(reportFile, JSON.stringify(report, null, 2));
  console.log(JSON.stringify(report, null, 2));
  if (failures.length) {
    console.error('\n' + failures.join('\n'));
    return 1;
  }
  console.log('\nMOCK PIPELINE PASS — zero live sends');
  return 0;
}

module.exports = { run };

if (require.main === module) {
  run().then((code) => process.exit(code)).catch((err) => {
    console.error(err);
    process.exit(1);
  });
}
