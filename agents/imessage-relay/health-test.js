#!/usr/bin/env node
'use strict';

/**
 * Functional-health tests (2026-09-16, P1-C). Synthetic chat.db in a temp HOME.
 * Never touches Messages.app, the real chat.db, or the production cursor. Never sends.
 *
 *   node imessage-relay/health-test.js
 */

const assert = require('assert');
const fs = require('fs');
const os = require('os');
const path = require('path');
const { execFileSync } = require('child_process');

const BODY = 'PRIVATE BODY zebra-lantern';
const PHONE = '+15715550123';
const NAME = 'Aunt Placeholder';
const FAKE_TOKEN = 'Zq9' + 'x'.repeat(40);

const tmp = fs.mkdtempSync(path.join(os.tmpdir(), 'imessage-health-test-'));
process.env.HOME = tmp;
process.env.IMESSAGE_ASSISTANT_ROOT = path.join(tmp, 'root');
delete process.env.IMESSAGE_KILL;
delete process.env.IMESSAGE_ALLOW_SEND;
delete process.env.IMESSAGE_AUTO_ASSISTANT;
fs.mkdirSync(process.env.IMESSAGE_ASSISTANT_ROOT, { recursive: true });
fs.writeFileSync(path.join(process.env.IMESSAGE_ASSISTANT_ROOT, 'config.json'),
  JSON.stringify({ allow_send: false, auto_send_assistant: false, safe_mode: true, poll_ms: 5000,
    llm: { litellm_url: 'http://127.0.0.1:9', ollama_url: 'http://127.0.0.1:9' } }));

const msgDir = path.join(tmp, 'Library', 'Messages');
fs.mkdirSync(msgDir, { recursive: true });
const CHAT_DB = path.join(msgDir, 'chat.db');
execFileSync('/usr/bin/sqlite3', [CHAT_DB, `
  CREATE TABLE handle (ROWID INTEGER PRIMARY KEY, id TEXT, uncanonicalized_id TEXT);
  CREATE TABLE message (ROWID INTEGER PRIMARY KEY, guid TEXT, text TEXT, attributedBody BLOB, handle_id INTEGER,
    is_from_me INTEGER, item_type INTEGER, is_system_message INTEGER, date INTEGER, service TEXT);
  INSERT INTO handle VALUES (1, '${PHONE}', '${NAME}');
  INSERT INTO message VALUES (1,'g1','${BODY}',NULL,1,0,0,0,800000000000000000,'iMessage');
  INSERT INTO message VALUES (2,'g2','${BODY}',NULL,1,0,0,0,800000001000000000,'iMessage');
  INSERT INTO message VALUES (3,'g3','${BODY}',NULL,1,0,0,0,800000002000000000,'iMessage');
`]);
const CURSOR = path.join(process.env.IMESSAGE_ASSISTANT_ROOT, 'chatdb.cursor');
const setCursor = (n) => fs.writeFileSync(CURSOR, String(n));

/** Fresh module = fresh in-memory poll state. */
function freshPollstate() {
  delete require.cache[require.resolve('./lib/pollstate')];
  return require('./lib/pollstate');
}

const outputs = [];
const failures = [];
const notes = [];
async function check(name, fn) {
  try {
    await fn();
    notes.push(`PASS  ${name}`);
  } catch (err) {
    failures.push(`FAIL  ${name}: ${err.message}`);
  }
}

const T0 = Date.parse('2026-09-16T20:00:00Z');

(async () => {
  await check('process healthy + db readable + poll advancing -> HEALTHY', () => {
    setCursor(3);
    const ps = freshPollstate();
    ps.recordPoll({ ok: true, processed: 1, sent: 0 }, T0);
    const h = ps.functionalHealth({ now: T0 + 1000 });
    outputs.push(h);
    assert.strictEqual(h.state, 'HEALTHY', JSON.stringify(h.reasons));
    assert.strictEqual(h.source_db_accessible, true);
    assert.strictEqual(h.poll_loop_advancing, true);
    assert.strictEqual(h.working_copy_accessible, true);
    assert.strictEqual(h.unprocessed_inbound, 0);
  });

  await check('process running + working copy fails once -> DEGRADED', () => {
    setCursor(3);
    const ps = freshPollstate();
    ps.recordPoll({ ok: true, processed: 0 }, T0);
    ps.recordPoll({ ok: false, error: `unable to open database file for ${PHONE}` }, T0 + 5000);
    const h = ps.functionalHealth({ now: T0 + 6000 });
    outputs.push(h);
    assert.strictEqual(h.state, 'DEGRADED');
    assert.ok(h.reasons.includes('recent_poll_failure'));
  });

  await check('process running + working copy fails 3x -> FAILED', () => {
    setCursor(3);
    const ps = freshPollstate();
    for (let i = 0; i < 3; i++) {
      ps.recordPoll({ ok: false, error: `unable to open database file ${PHONE} someone@example.com ${FAKE_TOKEN}` }, T0 + i * 5000);
    }
    const h = ps.functionalHealth({ now: T0 + 16000 });
    outputs.push(h);
    assert.strictEqual(h.state, 'FAILED');
    assert.ok(h.reasons.includes('working_copy_or_poll_failing'));
    assert.strictEqual(h.working_copy_accessible, false);
  });

  await check('source db readable + relay cannot process -> NOT HEALTHY after grace', () => {
    setCursor(0); // 3 inbound rows the relay never processed
    const ps = freshPollstate();
    ps.recordPoll({ ok: true, processed: 0 }, T0);
    const early = ps.functionalHealth({ now: T0 + 1000 });
    assert.strictEqual(early.source_db_accessible, true);
    assert.strictEqual(early.unprocessed_inbound, 3);
    ps.recordPoll({ ok: true, processed: 0 }, T0 + 61000);
    const late = ps.functionalHealth({ now: T0 + 62000 });
    outputs.push(early, late);
    assert.notStrictEqual(late.state, 'HEALTHY');
    assert.ok(late.reasons.includes('inbound_not_processed'), JSON.stringify(late.reasons));
  });

  await check('poll stalled -> HEALTHY inside 60s threshold, FAILED past it', () => {
    setCursor(3);
    const ps = freshPollstate();
    ps.recordPoll({ ok: true, processed: 0 }, T0);
    const inside = ps.functionalHealth({ now: T0 + 59000 });
    const past = ps.functionalHealth({ now: T0 + 60001 });
    outputs.push(inside, past);
    assert.strictEqual(inside.state, 'HEALTHY');
    assert.strictEqual(past.state, 'FAILED');
    assert.ok(past.reasons.includes('poll_loop_not_advancing'));
    assert.strictEqual(past.poll_loop_advancing, false);
  });

  await check('source db unreadable -> FAILED', () => {
    setCursor(3);
    const moved = CHAT_DB + '.away';
    fs.renameSync(CHAT_DB, moved);
    try {
      const ps = freshPollstate();
      ps.recordPoll({ ok: true, processed: 0 }, T0);
      const h = ps.functionalHealth({ now: T0 + 1000 });
      outputs.push(h);
      assert.strictEqual(h.state, 'FAILED');
      assert.ok(h.reasons.includes('source_db_unreadable'));
    } finally {
      fs.renameSync(moved, CHAT_DB);
    }
  });

  await check('/health: send OFF -> reported false (config + env)', async () => {
    setCursor(3);
    delete require.cache[require.resolve('./lib/inbound')];
    const { statusPayload, startupStateLine } = require('./lib/inbound');
    const p = await statusPayload();
    outputs.push(p);
    assert.strictEqual(p.allow_send, false);
    assert.strictEqual(p.auto_send_assistant, false);
    assert.strictEqual(p.functional.send_enabled, false);
    const line = startupStateLine({ allow_send: false, auto_send_assistant: false }, {});
    outputs.push(line);
    assert.ok(/SEND DISABLED/.test(line) && /AUTO-REPLY DISABLED/.test(line), line);
    assert.ok(!/auto-send\b(?! OFF)/i.test(line.replace('AUTO-REPLY DISABLED', '')), line);
  });

  await check('/health cannot report OFF while env turns send ON', async () => {
    process.env.IMESSAGE_ALLOW_SEND = '1';
    process.env.IMESSAGE_AUTO_ASSISTANT = '1';
    try {
      const { statusPayload, startupStateLine } = require('./lib/inbound');
      const p = await statusPayload();
      assert.strictEqual(p.allow_send, true);
      assert.strictEqual(p.auto_send_assistant, true);
      const line = startupStateLine({}, process.env);
      assert.ok(/SEND ENABLED/.test(line) && /AUTO-REPLY ENABLED/.test(line), line);
    } finally {
      delete process.env.IMESSAGE_ALLOW_SEND;
      delete process.env.IMESSAGE_AUTO_ASSISTANT;
    }
  });

  await check('health output carries no body, phone, contact name, or token', () => {
    const blob = JSON.stringify(outputs);
    assert.ok(outputs.length >= 8, `only ${outputs.length} outputs captured`);
    assert.ok(!blob.includes(BODY), 'message body leaked');
    assert.ok(!blob.includes('5715550123'), 'phone number leaked');
    assert.ok(!blob.includes(NAME), 'contact name leaked');
    assert.ok(!blob.includes('someone@example.com'), 'email leaked');
    assert.ok(!blob.includes(FAKE_TOKEN), 'token leaked');
    const fileState = fs.readFileSync(path.join(process.env.IMESSAGE_ASSISTANT_ROOT, 'poll-state.json'), 'utf8');
    assert.ok(!fileState.includes('5715550123') && !fileState.includes(FAKE_TOKEN), 'poll-state.json leaked');
  });

  console.log(notes.concat(failures).join('\n'));
  fs.rmSync(tmp, { recursive: true, force: true });
  if (failures.length) {
    console.error(`\nHEALTH TEST FAIL — ${failures.length} failing`);
    process.exit(1);
  }
  console.log(`\nHEALTH TEST PASS — ${notes.length} checks, zero sends, synthetic db only`);
})();
