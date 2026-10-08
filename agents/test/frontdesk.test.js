'use strict';
/**
 * Front desk orchestration — the order has to hold under test, not just on a good day.
 *
 * These run with a STUB agent runner, so they test the ORCHESTRATION (routing, ordering,
 * halting, gating, queueing) rather than a model's mood. The model is exercised separately,
 * live, against a real install — a test that depends on what a 14B model says today is a
 * test that fails tomorrow for no reason.
 *
 * The cases that matter most are the ones where the desk must NOT do the obvious thing:
 * a STOP must never reach a model, a complaint must never get an auto-reply, and a refused
 * draft must still be queued rather than vanish.
 */

const { test, describe, beforeEach } = require('node:test');
const assert = require('node:assert');
const fs = require('fs');
const os = require('os');
const path = require('path');

const TMP = fs.mkdtempSync(path.join(os.tmpdir(), 'aixfd-'));
process.env.AIXMOS_STATE_DIR = TMP;
process.env.AIXMOS_QUEUE_DIR = path.join(TMP, 'q');

const frontdesk = require('../lib/frontdesk');

const PROFILE = {
  business_name: 'Beltway Mobile Detail',
  what_we_do: 'mobile detailing',
  industry_pack: 'auto_detail',
  lines: [], notes: [],
  rate_card: [{ item: 'Mobile detail', price: '$125' }],
  escalate_to_owner: ['damage claims', 'anything legal'],
  claims: { allow_phrases: [] },
};

/** Records every model call so a test can assert the model was NOT called. */
function stub(reply = 'Drafted reply. $125 for the detail.') {
  const calls = [];
  const run = async ({ system, userPrompt, maxTokens }) => {
    calls.push({ system: String(system).slice(0, 40), userPrompt, maxTokens });
    return typeof reply === 'function' ? reply(calls.length, userPrompt) : reply;
  };
  run.calls = calls;
  return run;
}

const opts = (run) => ({ run, profile: PROFILE, queue: false });

beforeEach(() => { try { fs.rmSync(path.join(TMP, 'q'), { recursive: true, force: true }); } catch {} });

describe('an opt-out never reaches a model', () => {
  test('STOP halts before triage and before any agent', async () => {
    const run = stub();
    const r = await frontdesk.handleInbound({ from: '+15715550001', text: 'STOP' }, opts(run));
    assert.equal(r.status, 'OPTED_OUT');
    assert.equal(run.calls.length, 0, 'no model call may happen on a STOP');
    assert.equal(r.draft, null);
  });

  test('the number is actually suppressed afterwards', async () => {
    await frontdesk.handleInbound({ from: '+15715550002', text: 'stop' }, opts(stub()));
    const { isSuppressed } = require('../lib/suppression');
    assert.equal(isSuppressed('+15715550002'), true);
  });

  test('a stop-LIKE message is held for a human, not guessed at', async () => {
    const run = stub();
    const r = await frontdesk.handleInbound({ from: '+15715550003', text: 'please take me off this list' }, opts(run));
    assert.equal(r.status, 'NEEDS_HUMAN');
    assert.equal(r.escalated, true);
    assert.equal(run.calls.length, 0, 'guessing costs a customer either way — no model call');
  });
});

describe('triage routes deterministically where it can', () => {
  const cases = [
    ['how much to detail a 2019 Tahoe?', 'quote'],
    ['can I book something for Thursday?', 'booking'],
    ['my invoice says I still owe money', 'payment'],
    ['you scratched my hood', 'complaint'],
    ['should we hire a second tech?', 'decision'],
  ];
  for (const [text, lane] of cases) {
    test(`"${text.slice(0, 34)}…" -> ${lane}`, async () => {
      const t = await frontdesk.triage(text, { run: stub() });
      assert.equal(t.lane, lane);
      assert.equal(t.method, 'rule', 'a rule should place this without paying for a model');
    });
  }

  test('a complaint outranks a price question in the same message', async () => {
    const t = await frontdesk.triage('how much to fix the door you damaged?', { run: stub() });
    assert.equal(t.lane, 'complaint', 'getting this backwards costs a customer');
  });

  test('a bare acknowledgement costs nothing and drafts nothing', async () => {
    const run = stub();
    const r = await frontdesk.handleInbound({ from: '+15715550004', text: 'thanks!' }, opts(run));
    assert.equal(r.status, 'NO_ACTION');
    assert.equal(run.calls.length, 0);
  });

  test('an unclassifiable message falls back to the model', async () => {
    const run = stub('quote');
    const t = await frontdesk.triage('the thing for the vehicle, the usual', { run });
    assert.equal(t.method, 'model');
    assert.ok(run.calls.length >= 1);
  });

  test('a model failure still routes — it does not throw', async () => {
    const run = async () => { throw new Error('ollama down'); };
    const t = await frontdesk.triage('the thing for the vehicle, the usual', { run });
    assert.equal(t.lane, 'support', 'safe default: careful reply, no task opened');
  });
});

describe('the chain runs in order and each agent sees the last', () => {
  test('quote lane runs CHUMMO then MOOSE', async () => {
    const run = stub((n) => (n === 1 ? 'CHUMMO: $125 quoted.' : 'MOOSE: task opened.'));
    const r = await frontdesk.handleInbound({ from: '+15715550005', text: 'how much for a detail?' }, opts(run));
    assert.deepEqual(r.chain, ['chummo', 'moose']);
    assert.equal(run.calls.length, 2);
    assert.match(run.calls[1].userPrompt, /Previous agent output/);
    assert.match(run.calls[1].userPrompt, /CHUMMO: \$125 quoted\./);
  });

  test('VISION can stop the chain with NO-GO', async () => {
    const run = stub((n) => (n === 1 ? 'NO-GO — this does not fit the business.' : 'should not run'));
    const r = await frontdesk.handleInbound({ from: '+15715550006', text: 'should we expand to Maryland?' }, opts(run));
    assert.equal(r.status, 'BLOCKED_BY_VISION');
    assert.equal(run.calls.length, 1, 'CAPTAIN and MOOSE must not run after a NO-GO');
  });

  test('a chain failure is reported, not swallowed', async () => {
    const run = async () => { throw new Error('model exploded'); };
    const r = await frontdesk.handleInbound({ from: '+15715550007', text: 'how much for a detail?' }, opts(run));
    assert.equal(r.status, 'CHAIN_FAILED');
    assert.ok(r.trace.some(s => /FAILED/.test(s.result)));
  });
});

describe('escalation suppresses the customer-facing reply', () => {
  test('a damage claim escalates and asks for an INTERNAL brief', async () => {
    const run = stub('Internal brief for the owner.');
    const r = await frontdesk.handleInbound({ from: '+15715550008', text: 'you damaged my bumper' }, opts(run));
    assert.equal(r.escalated, true);
    assert.equal(r.status, 'ESCALATED_TO_OWNER');
    assert.match(run.calls[0].userPrompt, /INTERNAL brief/);
    assert.match(run.calls[0].userPrompt, /Do NOT write a message to the customer/);
  });

  test('escalation comes from the install\'s own list, not ours', () => {
    const hits = frontdesk.matchesEscalation('I am speaking to my lawyer about this', PROFILE);
    assert.ok(hits.length > 0);
  });

  test('an ordinary message does not escalate', () => {
    assert.equal(frontdesk.matchesEscalation('can I book Thursday?', PROFILE).length, 0);
  });
});

describe('the claims gate is not optional here either', () => {
  test('an invented price marks the draft NEEDS_FIX', async () => {
    const run = stub('Sure — $450 for that.');
    const r = await frontdesk.handleInbound({ from: '+15715550009', text: 'how much for a detail?' }, opts(run));
    assert.equal(r.gate.ok, false);
    assert.equal(r.status, 'NEEDS_FIX');
    assert.equal(r.gate.violations[0].found, '$450');
  });

  test('a rate-card price passes', async () => {
    const run = stub('Mobile detail is $125 — want Thursday?');
    const r = await frontdesk.handleInbound({ from: '+15715550010', text: 'how much for a detail?' }, opts(run));
    assert.equal(r.gate.ok, true, r.gate.summary);
    assert.equal(r.status, 'READY_FOR_APPROVAL');
  });

  test('nothing the front desk produces is ever marked sent', async () => {
    const run = stub('Mobile detail is $125.');
    const r = await frontdesk.handleInbound({ from: '+15715550011', text: 'how much?' }, opts(run));
    assert.equal(r.sent, false);
    assert.notEqual(r.status, 'SENT');
  });
});

describe('the queue keeps what a human must see', () => {
  test('a REFUSED draft is queued, never silently dropped', async () => {
    const run = stub('Sure — $450, guaranteed.');
    const r = await frontdesk.handleInbound(
      { from: '+15715550012', text: 'how much for a detail?' },
      { run, profile: PROFILE },
    );
    assert.equal(r.status, 'NEEDS_FIX');
    assert.ok(r.queued && fs.existsSync(r.queued), 'a vanished draft teaches operators to bypass the queue');
    const saved = JSON.parse(fs.readFileSync(r.queued, 'utf8'));
    assert.equal(saved.status, 'NEEDS_FIX');
    assert.ok(saved.gate.violations.length > 0);
  });

  test('the trace explains every decision', async () => {
    const run = stub('Mobile detail is $125.');
    const r = await frontdesk.handleInbound({ from: '+15715550013', text: 'how much?' }, opts(run));
    const steps = r.trace.map(s => s.step);
    assert.ok(steps.includes('suppression'));
    assert.ok(steps.includes('triage'));
    assert.ok(steps.includes('claims_gate'));
  });

  test('listQueue reads back what was written', async () => {
    await frontdesk.handleInbound({ from: '+15715550014', text: 'how much?' }, { run: stub('$125 please'), profile: PROFILE });
    const q = frontdesk.listQueue();
    assert.ok(q.length >= 1);
    assert.ok(q[0].status);
  });
});

/* ── regressions found by running it live, 2026-09-19 ───────────────────────── */

describe('regressions from the live run', () => {
  const booking = [
    'can you do thursday morning?',
    'you free tomorrow?',
    'how about saturday',
    'anything at 9am?',
    'next week sometime',
  ];
  for (const text of booking) {
    test(`"${text}" routes to booking, not support`, async () => {
      const t = await frontdesk.triage(text, { run: stub() });
      assert.equal(t.lane, 'booking', 'people say a DAY, not "I would like to book an appointment"');
      assert.equal(t.method, 'rule');
    });
  }

  test('the approved draft is the CUSTOMER reply, not the internal task note', async () => {
    const run = stub((n) => (n === 1
      ? 'Thursday works! Mobile detail is $125.'
      : 'Task opened for Thursday.\nCAPTAIN_HANDOFF: audit the schedule.'));
    const r = await frontdesk.handleInbound(
      { from: '+15715550020', text: 'how much for a detail?' }, opts(run),
    );
    assert.equal(r.draft_from, 'chummo');
    assert.match(r.draft, /Thursday works/);
    assert.ok(!/CAPTAIN_HANDOFF/.test(r.draft), 'the human must not approve a work ticket by mistake');
    assert.match(r.internal.moose, /Task opened/, 'the task note is kept, just not as the draft');
  });

  test('an invented price in the INTERNAL note also fails the gate', async () => {
    const run = stub((n) => (n === 1 ? 'Mobile detail is $125.' : 'Quote him $950 instead.'));
    const r = await frontdesk.handleInbound(
      { from: '+15715550021', text: 'how much for a detail?' }, opts(run),
    );
    assert.equal(r.gate.ok, false);
    assert.ok(r.gate.violations.some(v => v.where === 'internal:moose'));
  });

  test('an escalated brief is still the artefact a human sees', async () => {
    const run = stub('Owner brief: customer alleges hood damage.');
    const r = await frontdesk.handleInbound(
      { from: '+15715550022', text: 'you scratched my hood' }, opts(run),
    );
    assert.equal(r.escalated, true);
    assert.match(r.draft, /Owner brief/);
  });
});

describe('routing markers never reach a customer', () => {
  test('MOOSE_HANDOFF is stripped from the customer draft and kept', async () => {
    const run = stub('Thursday works! Mobile detail is $125.\nMOOSE_HANDOFF: confirm the slot.');
    const r = await frontdesk.handleInbound({ from: '+15715550030', text: 'thursday?' }, opts(run));
    assert.ok(!/HANDOFF/.test(r.draft), 'the pack must not text a customer its own routing');
    assert.match(r.draft, /Thursday works/);
    assert.match(r.handoff, /MOOSE_HANDOFF: confirm the slot\./);
  });

  test('an escalated owner brief KEEPS its markers — it is internal already', async () => {
    const run = stub('Brief for owner.\nWONDERWOMAN_HANDOFF: BUSINESS|X|damage|HIGH');
    const r = await frontdesk.handleInbound({ from: '+15715550031', text: 'you scratched my hood' }, opts(run));
    assert.match(r.draft, /WONDERWOMAN_HANDOFF/);
  });
});
