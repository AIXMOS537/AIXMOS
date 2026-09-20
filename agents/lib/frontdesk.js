'use strict';
/**
 * FRONT DESK — the local orchestrator that turns a raw inbound into a gated, queued draft.
 *
 * WHY THIS EXISTS. The pack already had the agents and, since 2026-09-19, the gates. What it
 * did not have was anything that put them in order without a human driving. The two entry
 * points were:
 *
 *   orchestrator.js  an interactive TUI — a menu, and "Use this handoff? (y/n)" at every
 *                    step. Real orchestration, but it needs someone sitting at a terminal.
 *   agent-server.js  HTTP, headless — but `/agent/<name>` makes YOU name the agent, and
 *                    BOTH it and `/council` returned raw model output with **no gate at
 *                    all**: not the do-not-contact list, not the claims gate. Every
 *                    protection in this pack lived in lib/sender.js, and neither route
 *                    called it.
 *
 * So on a fresh install nothing answered the actual question — "a text just arrived, what
 * happens to it?" This is that. One inbound in, one gated draft out, nothing sent.
 *
 * THE ORDER IS THE POINT:
 *
 *   1. STOP/START      handled before ANY model sees the message. An opt-out is not a
 *                      conversation to reason about, and paying a model to think about one
 *                      is how a STOP gets answered with a sales pitch.
 *   2. Escalation      matched against the install's own escalate_to_owner list. A damage
 *                      claim or a legal threat produces NO customer-facing draft at all.
 *   3. Triage          deterministic rules first, a model only for what the rules cannot
 *                      place. Routing is not a hard problem and it should not cost a
 *                      round-trip; the model is the fallback, not the front line.
 *   4. Chain           the lane's agents, in order, each one handed the previous output.
 *   5. Gates           claims gate on every draft. Non-optional. A refused draft is QUEUED
 *                      as needs-fix with the violations attached — never silently dropped,
 *                      because a disappeared draft teaches an operator to distrust the
 *                      queue and go around it.
 *   6. Queue           written to disk for a human. NOTHING IS SENT FROM HERE. The COMMS
 *                      HOLD is the whole design, not a setting.
 *
 * Every step is recorded in `trace`, so an operator can see why a message went where it
 * went. An orchestrator you cannot audit is just a black box with opinions.
 */

const fs = require('fs');
const path = require('path');
const os = require('os');

const prompts = require('./../agents/prompts');
const { runAgent } = require('./runner');
const { checkClaims, explain: explainClaims } = require('./claims');
const { loadProfile, ownerLabel } = require('./profile');
const suppression = require('./suppression');

const QUEUE_DIR = process.env.AIXMOS_QUEUE_DIR
  || path.join(process.env.AIXMOS_STATE_DIR || path.join(os.homedir(), '.aixmos'), 'frontdesk');

/* ───────────────────────────── triage ───────────────────────────── */

/**
 * Deterministic lanes, in priority order. First match wins, and order matters: a message
 * that is both a complaint and a price question is a complaint, because getting that one
 * backwards costs a customer.
 */
const LANES = [
  {
    lane: 'complaint',
    re: /\b(damage[ds]?|scratch(?:ed)?|dent(?:ed)?|broke|broken|ruined|terrible|awful|worst|furious|unacceptable|refund|lawyer|attorney|sue|suing|legal action|bbb|charge ?back)\b/i,
    chain: ['wonder_woman'],
    escalate: true,
    why: 'a complaint or a liability signal — a trust-guard matter, never an auto-reply',
  },
  {
    lane: 'payment',
    re: /\b(invoice|bill(?:ing)?|paid|payment|charge[ds]?|receipt|owe|balance|past due|card declined)\b/i,
    chain: ['chummo', 'moose'],
    why: 'money in flight — reply carefully, then open a task',
  },
  {
    lane: 'quote',
    re: /\b(how much|price|pricing|cost|quote|rate|estimate|what do you charge|ballpark)\b/i,
    chain: ['chummo', 'moose'],
    why: 'a price question — the highest-risk lane, which is why the claims gate matters most here',
  },
  {
    lane: 'booking',
    // Found live 2026-09-19: "can you do thursday morning?" fell through to `support`,
    // because the intent words were all here and none of the TIME words were. People do not
    // say "I would like to book an appointment"; they say a day. Days, parts of the day and
    // clock times are how scheduling actually arrives.
    re: new RegExp([
      '\\b(book|booking|schedule|scheduling|appointment|availability|available|slot',
      '|when can|reschedul|cancel my|move my|come out|stop by|fit me in|squeeze me)\\b',
      '|\\b(mon|tues|wednes|thurs|fri|satur|sun)day\\b',
      '|\\b(today|tomorrow|tonight|this week|next week|weekend)\\b',
      '|\\b(morning|afternoon|evening)\\b',
      '|\\b\\d{1,2}\\s?(am|pm)\\b',
    ].join(''), 'i'),
    chain: ['chummo', 'moose'],
    why: 'scheduling intent — draft a reply and open the task',
  },
  {
    lane: 'decision',
    re: /\b(should we|should i|worth it|make sense|strategy|hire|fire|expand|invest|partner(?:ship)?|contract)\b/i,
    chain: ['vision', 'captain', 'moose'],
    why: 'a business decision — governance first, so a bad idea gets blocked before it is planned',
  },
  {
    lane: 'support',
    re: /\b(help|question|problem|issue|not working|how do i|can you|status|update)\b/i,
    chain: ['chummo'],
    why: 'general support — a human-voiced reply, no task needed yet',
  },
];

/** Spam/noise that should never cost a model call. */
const NOISE_RE = /^\s*(?:ok(?:ay)?|k|thanks?|thank you|ty|got it|👍+|\p{Emoji}+)\s*[.!]?\s*$/iu;

/**
 * Route an inbound. Returns { lane, chain, why, method }.
 * `method` is 'rule' or 'model' so an operator can see which decided.
 */
async function triage(text, opts = {}) {
  const t = String(text == null ? '' : text);

  if (NOISE_RE.test(t)) {
    return { lane: 'acknowledgement', chain: [], why: 'a bare acknowledgement — no reply needed', method: 'rule' };
  }
  for (const l of LANES) {
    if (l.re.test(t)) {
      return { lane: l.lane, chain: l.chain, why: l.why, escalate: !!l.escalate, method: 'rule' };
    }
  }

  // Only now is it worth a model. Asked as a closed classification, not an open question.
  const run = opts.run || runAgent;
  let picked = 'support';
  try {
    const out = await run({
      system: 'You are a front-desk router. Reply with EXACTLY ONE word from this list and '
        + 'nothing else: complaint, payment, quote, booking, decision, support.',
      userPrompt: `Inbound message:\n"""${t.slice(0, 600)}"""\n\nOne word:`,
      maxTokens: 2000,
    });
    const m = String(out).toLowerCase().match(/\b(complaint|payment|quote|booking|decision|support)\b/);
    if (m) picked = m[1];
  } catch {
    // A router that cannot reach a model must still route. 'support' is the safe default:
    // it drafts a careful human reply and opens nothing.
    picked = 'support';
  }
  const l = LANES.find(x => x.lane === picked) || LANES[LANES.length - 1];
  return { lane: l.lane, chain: l.chain, why: l.why, escalate: !!l.escalate, method: 'model' };
}

/* ───────────────────────────── escalation ───────────────────────────── */

/**
 * Does this inbound match something the install said it wants a human for? Built from the
 * profile's own escalate_to_owner list, so it is the client's policy being enforced rather
 * than ours.
 *
 * Customers do not use the client's words. An install that says "anything legal" means to
 * catch "I'm calling my lawyer", and literal word-matching misses that entirely — which is
 * a policy the client wrote and the software quietly did not enforce.
 *
 * This is a small, explicit synonym table rather than a model call: escalation must work
 * when the model is down, and it must be auditable. It is not exhaustive and is not meant
 * to be — the complaint LANE catches the same signals independently, so this is the second
 * of two nets, not the only one.
 */
const ESCALATION_SYNONYMS = {
  legal: ['legal', 'lawyer', 'attorney', 'sue', 'suing', 'lawsuit', 'court', 'liable', 'liability', 'subpoena'],
  damage: ['damage', 'damaged', 'scratch', 'scratched', 'dent', 'dented', 'broke', 'broken', 'ruined', 'cracked'],
  insurance: ['insurance', 'claim', 'adjuster', 'policy', 'coverage'],
  refund: ['refund', 'money back', 'charge back', 'chargeback', 'dispute'],
  unhappy: ['unhappy', 'angry', 'furious', 'upset', 'disappointed', 'terrible', 'awful', 'worst'],
  risky: ['weapon', 'threat', 'threaten', 'police', 'emergency'],
};

const STOPWORDS = new Set(['anything', 'over', 'with', 'their', 'from', 'that', 'this', 'matters', 'claims']);

function matchesEscalation(text, profile) {
  const t = String(text || '').toLowerCase();
  const hits = [];
  for (const rule of profile.escalate_to_owner || []) {
    const words = (String(rule).toLowerCase().match(/[a-z]{4,}/g) || [])
      .filter(w => !STOPWORDS.has(w));
    // Each of the client's words expands to the terms a customer would actually use.
    const terms = new Set();
    for (const w of words) {
      terms.add(w);
      for (const [concept, syns] of Object.entries(ESCALATION_SYNONYMS)) {
        if (w.startsWith(concept) || concept.startsWith(w)) syns.forEach(s => terms.add(s));
      }
    }
    for (const term of terms) {
      if (new RegExp(`\\b${term.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')}`, 'i').test(t)) {
        hits.push(rule);
        break;
      }
    }
  }
  return hits;
}

/* ───────────────────────────── the desk ───────────────────────────── */

/**
 * Resolve a persona by name, tolerant of underscores in either direction.
 *
 * The personas are keyed `wonder_woman` and `fly_guy`, but every other surface in the pack
 * spells them `wonderwoman` / `flyguy`. The first version of this looked up `prompts[name]`
 * and then `name.replace(/_/g,'')` — which can only ever REMOVE underscores, so
 * 'wonderwoman' never resolved to 'wonder_woman'. The complaint lane therefore ran ZERO
 * agents and returned an empty draft, silently. Normalising both sides is the fix; the
 * throw is the part that matters, because that is what turns the next such typo into a
 * failure instead of a quiet no-op on the single most sensitive lane in the product.
 */
const PERSONA_BY_NORM = Object.fromEntries(
  Object.keys(prompts).map(k => [k.replace(/_/g, ''), k]),
);

/**
 * Which personas write to the CUSTOMER and which write internal work.
 *
 * Found live 2026-09-19: on the quote lane (chummo -> moose) the record's `draft` held
 * MOOSE's output, because the loop overwrote it every pass. MOOSE writes an internal task
 * note ending "CAPTAIN_HANDOFF: ...", so the operator's review queue showed a work ticket
 * where the customer reply should have been — and CHUMMO's actual reply was gone. An
 * approval queue that shows the wrong artefact is worse than none: the human approves
 * something, and it is not the thing that gets sent.
 */
const CUSTOMER_FACING = new Set(['chummo']);

/**
 * The personas end their output with a routing marker — "MOOSE_HANDOFF: ...",
 * "CAPTAIN_HANDOFF: ..." — which is how the chain passes context along. That marker is
 * INTERNAL. Found live 2026-09-19: the customer-facing draft in the review queue still
 * carried "MOOSE_HANDOFF: Confirm availability and schedule..." on the end, so a human
 * approving it would have texted the customer the pack's own routing instructions.
 * The handoff is kept — it is genuinely useful — just not inside the message.
 */
const HANDOFF_RE = /\n?\s*[A-Z][A-Z_ ]{2,30}_HANDOFF\s*:[\s\S]*$/;

function splitHandoff(text) {
  const t = String(text || '');
  const m = t.match(HANDOFF_RE);
  return {
    message: t.replace(HANDOFF_RE, '').trim(),
    handoff: m ? m[0].replace(/^\s*\n?/, '').trim() : null,
  };
}
const INTERNAL = new Set(['moose', 'captain', 'captain_dispatch', 'vision', 'wonder_woman', 'tank', 'sticks', 'jarvis']);

function agentPrompt(name) {
  const key = PERSONA_BY_NORM[String(name).replace(/_/g, '').toLowerCase()];
  if (!key) {
    const err = new Error(
      `unknown persona '${name}'. known: ${Object.keys(prompts).join(', ')}. `
      + 'A lane naming a persona that does not exist must fail, not run nothing.',
    );
    err.code = 'UNKNOWN_PERSONA';
    throw err;
  }
  return prompts[key];
}

/**
 * Handle one inbound, end to end.
 *
 * @param {object} inbound        { from, text, channel }
 * @param {object} [opts]
 * @param {function} [opts.run]   override runAgent (tests, or a cheaper router model)
 * @param {boolean} [opts.queue]  write to the review queue (default true)
 * @returns {Promise<object>}     the full decision record
 */
async function handleInbound(inbound = {}, opts = {}) {
  const { from = null, text = '', channel = 'sms' } = inbound;
  const profile = opts.profile || loadProfile();
  const run = opts.run || runAgent;
  const trace = [];
  const at = new Date().toISOString();

  const record = {
    at, from, channel, inbound: text,
    lane: null, chain: [], trace,
    draft: null, draft_from: null, handoff: null, outputs: {}, internal: {},
    gate: null, escalated: false, escalations: [],
    status: null, sent: false,   // sent is ALWAYS false here. Nothing in this file sends.
  };

  // ── 1. STOP / START, before any model ──────────────────────────────────────────
  let optOut;
  try {
    optOut = suppression.handleInbound({ from, text });
  } catch (e) {
    // An unreadable DNC list is not a reason to proceed as if nobody opted out.
    record.status = 'HELD_DNC_UNREADABLE';
    trace.push({ step: 'suppression', result: `refused: ${e.message}` });
    return finish(record, opts);
  }
  trace.push({ step: 'suppression', result: optOut.kind });
  if (optOut.kind === 'opt_out') {
    record.status = 'OPTED_OUT';
    record.lane = 'opt_out';
    trace.push({ step: 'halt', result: 'suppressed — no reply drafted, no model called' });
    return finish(record, opts);
  }
  if (optOut.kind === 'stop_like') {
    record.status = 'NEEDS_HUMAN';
    record.lane = 'opt_out_unclear';
    record.escalated = true;
    trace.push({ step: 'halt', result: 'reads like an opt-out but is not a keyword — a human decides, not a guess' });
    return finish(record, opts);
  }

  // ── 2. Escalation policy (the install's own list) ───────────────────────────────
  const esc = matchesEscalation(text, profile);
  if (esc.length) {
    record.escalated = true;
    record.escalations = esc;
    trace.push({ step: 'escalation', result: `matched: ${esc.join(', ')}` });
  }

  // ── 3. Triage ──────────────────────────────────────────────────────────────────
  const t = await triage(text, { run });
  record.lane = t.lane;
  record.chain = t.chain;
  trace.push({ step: 'triage', result: `${t.lane} (by ${t.method}) — ${t.why}` });

  if (t.escalate) { record.escalated = true; }

  if (!t.chain.length) {
    record.status = 'NO_ACTION';
    return finish(record, opts);
  }

  // A complaint or a policy escalation does NOT get an auto-drafted customer reply.
  // WONDERWOMAN writes an internal brief for the owner instead.
  const customerFacing = !record.escalated;

  // ── 4. Run the chain ───────────────────────────────────────────────────────────
  let carried = '';
  for (const name of t.chain) {
    let system;
    try {
      system = agentPrompt(name);
    } catch (e) {
      record.status = 'CHAIN_FAILED';
      trace.push({ step: name, result: `FAILED: ${e.message}` });
      return finish(record, opts);
    }
    const userPrompt = [
      `Inbound (${channel}) from ${from || 'unknown'}:`,
      `"""${text}"""`,
      carried ? `\nPrevious agent output:\n"""${carried}"""` : '',
      record.escalated
        ? `\nThis is ESCALATED to ${ownerLabel(profile)} (${record.escalations.join(', ') || t.lane}). `
          + 'Write an INTERNAL brief for the owner. Do NOT write a message to the customer.'
        : '\nDraft the next action.',
    ].filter(Boolean).join('\n');

    let out;
    try {
      out = String(await run({ system, userPrompt, maxTokens: 2500 }));
    } catch (e) {
      record.status = 'CHAIN_FAILED';
      trace.push({ step: name, result: `FAILED: ${e.message}` });
      return finish(record, opts);
    }
    out = out.replace(/<think>[\s\S]*?<\/think>/g, '').trim();
    trace.push({ step: name, result: `${out.length} chars` });
    carried = out;
    record.outputs[name] = out;

    // VISION can stop the chain. A governance agent that cannot say no is decoration.
    if (name === 'vision' && /NO-?GO/i.test(out)) {
      record.status = 'BLOCKED_BY_VISION';
      record.draft = out;
      trace.push({ step: 'halt', result: 'VISION returned NO-GO — chain stopped' });
      return finish(record, opts);
    }
  }
  // The draft a human approves must be the CUSTOMER-FACING one, not whatever ran last.
  // Internal work (the task note, the owner brief) is kept alongside it, not instead of it.
  const spoken = t.chain.filter(n => CUSTOMER_FACING.has(n) && record.outputs[n]);
  const rawDraft = record.escalated
    ? (carried || null)                                   // escalated: the brief IS the artefact
    : (spoken.length ? record.outputs[spoken[spoken.length - 1]] : carried || null);
  // An escalated brief is for the owner and keeps its markers; a customer draft does not.
  if (record.escalated) {
    record.draft = rawDraft;
  } else {
    const split = splitHandoff(rawDraft);
    record.draft = split.message || null;
    record.handoff = split.handoff;
  }
  record.internal = Object.fromEntries(
    Object.entries(record.outputs).filter(([n]) => INTERNAL.has(n)),
  );
  record.draft_from = record.escalated
    ? (t.chain[t.chain.length - 1] || null)
    : (spoken[spoken.length - 1] || t.chain[t.chain.length - 1] || null);

  // ── 5. Claims gate — non-optional ──────────────────────────────────────────────
  // Internal briefs are checked too. An owner brief that invents a number becomes the
  // basis of a decision, which is a different harm from the same number reaching a
  // customer but not a smaller one.
  // Gate the customer-facing draft. Internal notes are checked too — an owner brief that
  // invents a number becomes the basis of a decision, which is a different harm from the
  // same number reaching a customer, but not a smaller one.
  const gate = checkClaims(record.draft || '', { context: text, profile });
  for (const [n, o] of Object.entries(record.internal)) {
    const g = checkClaims(o, { context: text, profile });
    if (!g.ok) {
      gate.ok = false;
      gate.violations = gate.violations.concat(
        g.violations.map(v => ({ ...v, where: `internal:${n}` })),
      );
    }
  }
  record.gate = { ok: gate.ok, violations: gate.violations, summary: explainClaims(gate) };
  trace.push({ step: 'claims_gate', result: gate.ok ? 'clean' : `REFUSED (${gate.violations.length})` });

  if (!gate.ok) {
    record.status = 'NEEDS_FIX';
  } else if (record.escalated) {
    record.status = 'ESCALATED_TO_OWNER';
  } else if (customerFacing) {
    record.status = 'READY_FOR_APPROVAL';
  } else {
    record.status = 'READY_FOR_APPROVAL';
  }

  return finish(record, opts);
}

/* ───────────────────────────── queue ───────────────────────────── */

function slug(s) {
  return String(s || 'unknown').replace(/[^a-zA-Z0-9]+/g, '-').replace(/^-|-$/g, '').slice(0, 40) || 'unknown';
}

function finish(record, opts = {}) {
  if (opts.queue === false) return record;
  try {
    fs.mkdirSync(QUEUE_DIR, { recursive: true });
    const name = `${record.at.replace(/[:.]/g, '-')}-${slug(record.lane)}-${slug(record.from)}.json`;
    const file = path.join(QUEUE_DIR, name);
    fs.writeFileSync(file, JSON.stringify(record, null, 2), { mode: 0o600 });
    record.queued = file;
  } catch (e) {
    // Never throw away a decision because the disk complained — surface it instead.
    record.queueError = e.message;
  }
  return record;
}

/** Everything waiting on a human, newest first. */
function listQueue() {
  try {
    if (!fs.existsSync(QUEUE_DIR)) return [];
    return fs.readdirSync(QUEUE_DIR)
      .filter(f => f.endsWith('.json'))
      .sort().reverse()
      .map(f => {
        try { return { file: path.join(QUEUE_DIR, f), ...JSON.parse(fs.readFileSync(path.join(QUEUE_DIR, f), 'utf8')) }; }
        catch { return { file: path.join(QUEUE_DIR, f), status: 'UNREADABLE' }; }
      });
  } catch { return []; }
}

module.exports = { handleInbound, triage, matchesEscalation, listQueue, QUEUE_DIR, LANES };
