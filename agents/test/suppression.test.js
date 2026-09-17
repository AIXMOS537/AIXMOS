'use strict';
const { test, describe, beforeEach, afterEach } = require('node:test');
const assert = require('node:assert');
const fs = require('fs');
const os = require('os');
const path = require('path');

// Point the gate at a scratch dir so tests never touch a real install's list.
const TMP = fs.mkdtempSync(path.join(os.tmpdir(), 'aixmos-dnc-'));
process.env.AIXMOS_STATE_DIR = TMP;

const S = require('../lib/suppression');
const { sendMessage } = require('../lib/sender');

const LIST = path.join(TMP, 'do-not-contact.json');
beforeEach(() => { try { fs.unlinkSync(LIST); } catch {} });
afterEach(() => { try { fs.unlinkSync(LIST); } catch {} });

describe('number matching survives formatting', () => {
  test('the same number in five formats is one entry', () => {
    S.suppress('+1 (571) 555-0101');
    for (const v of ['5715550101', '571-555-0101', '(571) 555 0101', '+15715550101', '1 571 555 0101']) {
      assert.equal(S.isSuppressed(v), true, `${v} should be suppressed`);
    }
  });
  test('an unrelated number is not suppressed', () => {
    S.suppress('5715550101');
    assert.equal(S.isSuppressed('5715550102'), false);
  });
});

describe('STOP is honoured, START releases', () => {
  test.each = undefined;
  for (const word of ['STOP', 'stop', 'Stop.', 'STOPALL', 'unsubscribe', 'CANCEL', 'quit', 'END']) {
    test(`"${word}" opts the sender out`, () => {
      const r = S.handleInbound({ from: '5715550101', text: word });
      assert.equal(r.kind, 'opt_out');
      assert.equal(S.isSuppressed('5715550101'), true);
    });
  }
  test('START puts them back', () => {
    S.handleInbound({ from: '5715550101', text: 'STOP' });
    assert.equal(S.isSuppressed('5715550101'), true);
    S.handleInbound({ from: '5715550101', text: 'START' });
    assert.equal(S.isSuppressed('5715550101'), false);
  });
});

describe('free-text stop is flagged for a human, never guessed', () => {
  for (const t of ['stop texting me', 'take me off your list', 'remove me', 'please leave me alone']) {
    test(`"${t}" needs a human and does NOT auto-suppress`, () => {
      const r = S.handleInbound({ from: '5715550101', text: t });
      assert.equal(r.kind, 'stop_like');
      assert.equal(r.needsHuman, true);
      // Guessing wrong in either direction is bad; a person decides.
      assert.equal(S.isSuppressed('5715550101'), false);
    });
  }
  test('an ordinary reply is not an opt-out', () => {
    assert.equal(S.handleInbound({ from: '5715550101', text: 'ok thanks, stopping by tomorrow' }).kind, 'none');
    assert.equal(S.isSuppressed('5715550101'), false);
  });
});

describe('the gate fails CLOSED', () => {
  test('an unreadable list throws rather than reading as "nobody opted out"', () => {
    fs.mkdirSync(TMP, { recursive: true });
    fs.writeFileSync(LIST, '{ this is not json');
    assert.throws(() => S.isSuppressed('5715550101'), /unreadable/);
  });
  test('a list that is an array, not an object, is also refused', () => {
    fs.writeFileSync(LIST, '["5715550101"]');
    assert.throws(() => S.isSuppressed('5715550101'), /unreadable/);
  });
  test('a genuinely absent list is empty, not an error', () => {
    assert.equal(S.isSuppressed('5715550101'), false);
  });
});

describe('sendMessage refuses a suppressed recipient on every path', () => {
  test('a suppressed number is refused before any provider is tried', async () => {
    S.suppress('5715550101');
    const r = await sendMessage({ to: '+15715550101', text: 'hello' });
    assert.equal(r.ok, false);
    assert.equal(r.suppressed, true);
    assert.match(r.error, /opted out/);
  });

  test('DRY RUN is refused too — a dry run that says "would send" gets copied into a real one', async () => {
    S.suppress('5715550101');
    const r = await sendMessage({ to: '5715550101', text: 'hello', dryRun: true });
    assert.equal(r.ok, false);
    assert.equal(r.suppressed, true);
  });

  test('naming an explicit channel does not route around the gate', async () => {
    S.suppress('5715550101');
    for (const channel of ['ghl', 'quo', 'imessage']) {
      const r = await sendMessage({ to: '5715550101', text: 'hi', channel });
      assert.equal(r.suppressed, true, `${channel} bypassed the gate`);
    }
  });

  test('an unreadable list refuses the send instead of sending', async () => {
    fs.writeFileSync(LIST, 'corrupt');
    const r = await sendMessage({ to: '5715550101', text: 'hello' });
    assert.equal(r.ok, false);
    assert.equal(r.suppressed, true);
    assert.match(r.error, /refusing to send/);
  });

  test('a number nobody opted out of still reaches the provider stage', async () => {
    const r = await sendMessage({ to: '5715559999', text: 'hello', dryRun: true });
    // Either it dry-runs or reports no configured channel — but it is NOT suppressed.
    assert.notEqual(r.suppressed, true);
  });
});

describe('the iMessage relay honours STOP before any other guard', () => {
  const { handleInbound: pipelineInbound } = require('../imessage-relay/lib/pipeline');

  test('an inbound STOP suppresses and stops the pipeline', async () => {
    const r = await pipelineInbound({ from: '+15715550101', text: 'STOP', id: 'm1' }, { config: {} });
    assert.equal(r.action, 'opt_out');
    assert.equal(r.sent, false);
    assert.equal(S.isSuppressed('5715550101'), true);
  });

  test('STOP is honoured even with the kill switch OFF and no config at all', async () => {
    // The point of ordering it first: it works on a day everything else is misconfigured.
    const r = await pipelineInbound({ from: '5715550102', text: 'unsubscribe' }, {});
    assert.equal(r.action, 'opt_out');
    assert.equal(S.isSuppressed('5715550102'), true);
  });

  test('free-text stop is HELD for a human, not auto-suppressed', async () => {
    const r = await pipelineInbound({ from: '5715550103', text: 'stop texting me' }, { config: {} });
    assert.equal(r.action, 'held');
    assert.equal(r.reason, 'stop_like_needs_human');
    assert.equal(S.isSuppressed('5715550103'), false);
  });

  test('START releases them again', async () => {
    await pipelineInbound({ from: '5715550104', text: 'STOP' }, { config: {} });
    assert.equal(S.isSuppressed('5715550104'), true);
    await pipelineInbound({ from: '5715550104', text: 'START' }, { config: {} });
    assert.equal(S.isSuppressed('5715550104'), false);
  });
});
