'use strict';
/**
 * Claims gate — the enforcement behind "never invent a price, a product or a claim".
 *
 * WHY THIS EXISTS. `lib/profile.js` ends every persona's business context with the line
 * "Never invent a price, a product or a claim that is not listed above." That sentence was
 * the ONLY thing standing between a client's customers and a number the client never
 * authorised, and it was enforced by nothing at all.
 *
 * Measured 2026-09-19 against a clean white-label install (qwen3:14b, local lane), asking
 * CHUMMO to reply to "how much to detail a 2019 Tahoe?" with NO rate card supplied:
 *
 *     run 1 -> "$199"                run 2 -> "$125 + $50 = $175"        run 3 -> clean
 *
 * Two of three drafts quoted a price that did not exist, in the client's voice, under the
 * client's brand. The prompt said not to. The model did anyway. That is the whole lesson:
 * a rule written in a prompt is a preference, not a control — and a smaller local model
 * honours it less than a frontier one, which is exactly the lane a cost-conscious client
 * will run on.
 *
 * FAIL CLOSED. If the install supplied no rate card and a draft contains a price, this
 * REFUSES. It does not warn, and it does not pass the draft through with a note attached.
 * An unverifiable price is treated the same as a wrong one, because from the recipient's
 * side they are the same thing. An install that genuinely quotes no prices never trips it;
 * an install that quotes prices has to write them down first, which is the point.
 *
 * WHAT IT IS NOT. This is not a truth oracle. It catches the specific, checkable failures
 * that cost money and licences — invented numbers, guarantees, and the per-vertical claims
 * that regulators actually act on. It cannot catch a plausible lie with no number in it,
 * and nothing in this file should be read as saying it can.
 */

const { loadProfile } = require('./profile');

/* ─────────────────────────── money ─────────────────────────── */

/**
 * Currency amounts. Deliberately broad: "$1,299.00", "$99", "99 dollars", "99 bucks".
 * Broad is correct here — a missed amount is an unauthorised quote reaching a customer,
 * while a false positive only costs a human one glance at a draft.
 */
const MONEY_RE = /\$\s?\d[\d,]*(?:\.\d{1,2})?|\b\d[\d,]*(?:\.\d{1,2})?\s?(?:dollars|bucks|USD)\b/gi;

/** Percentages, which are how discounts and rates get invented. "20% off", "3.5% APR". */
const PERCENT_RE = /\b\d{1,3}(?:\.\d+)?\s?%/g;

/** Normalise an amount to a comparable number. "$1,299.00" and "1299" are the same claim. */
function amountOf(raw) {
  const n = String(raw).replace(/[^\d.]/g, '');
  if (!n || !/\d/.test(n)) return null;
  const f = parseFloat(n);
  return Number.isFinite(f) ? f : null;
}

/** Every number the install has actually authorised, from anywhere in the rate card. */
function authorisedAmounts(profile) {
  const out = new Set();
  const walk = (v) => {
    if (v == null) return;
    if (typeof v === 'number') { out.add(v); return; }
    if (typeof v === 'string') {
      for (const m of v.match(MONEY_RE) || []) { const a = amountOf(m); if (a != null) out.add(a); }
      for (const m of v.match(PERCENT_RE) || []) { const a = amountOf(m); if (a != null) out.add(a); }
      return;
    }
    if (Array.isArray(v)) { v.forEach(walk); return; }
    if (typeof v === 'object') { Object.values(v).forEach(walk); }
  };
  walk(profile.rate_card);
  return out;
}

/* ─────────────────────────── claim phrases ─────────────────────────── */

/**
 * Universally dangerous phrasing. Every entry here is something a business can be made to
 * answer for regardless of industry — an unconditional promise about a future outcome.
 */
const CORE_PHRASES = [
  [/\bguarantee(?:d|s)?\b/i, 'an unconditional guarantee'],
  [/\brisk[- ]free\b/i, 'a risk-free claim'],
  [/\bno risk\b/i, 'a no-risk claim'],
  [/\b100\s?%\s?(?:guaranteed|satisfaction|effective|success)\b/i, 'an absolute-certainty claim'],
  [/\bwe promise\b/i, 'a promise of outcome'],
  [/\balways works\b/i, 'an absolute-certainty claim'],
  [/\bnever fails?\b/i, 'an absolute-certainty claim'],
  [/\binstant(?:ly)? (?:approved|results?|cure)\b/i, 'an instant-outcome claim'],
  [/\bbest (?:in|price in) (?:town|the area|the state)\b/i, 'an unverifiable superlative'],
  [/\bcheapest\b/i, 'an unverifiable superlative'],
  [/\blowest price\b/i, 'an unverifiable superlative'],
];

/**
 * Per-vertical rules. Keys match the FORGE industry pack names, so a client already running
 * `industry_pack: "med_spa"` gets the med-spa claim rules without configuring anything twice.
 * Each entry is drawn from the same statute or rule the pack's own compliance.md cites.
 */
const VERTICAL_PHRASES = {
  med_spa: [
    [/\bcure(?:s|d)?\b/i, 'a medical cure claim'],
    [/\bpermanent(?:ly)?\b/i, 'a permanence claim on a treatment'],
    [/\bFDA[- ]approved\b/i, 'an FDA-approval claim'],
    [/\bpain[- ]free\b/i, 'a clinical comfort promise'],
    [/\bno (?:downtime|side effects)\b/i, 'a clinical outcome promise'],
    [/\b(?:botox|filler|laser|injection|units?)\b/i, 'a treatment named in an unsecured message (HIPAA-aware rule)'],
  ],
  credit_funding: [
    // Must tolerate intervening words — "remove THOSE FROM your credit report" is the
    // natural phrasing and a tighter regex missed it. Bounded to one clause so it
    // cannot match a 'remove' and a 'credit' three sentences apart.
    [/\b(?:remove|delete|erase|wipe|clear)(?:s|d|ing)?\b[^.!?]{0,40}\b(?:credit report|credit file|credit|collections?|negative items?|late payments?|charge[- ]?offs?)\b/i,
      'a deletion promise (CROA)'],
    [/\b\d{2,3}\s?(?:points?|pts?)\b/i, 'a score-improvement claim (CROA)'],
    [/\bfix(?:es|ed)?\s+your\s+credit\b/i, 'an outcome claim (CROA)'],
    [/\bapproved\b/i, 'an approval claim before underwriting'],
    [/\bCPN\b|\bcredit privacy number\b/i, 'a prohibited CPN reference'],
  ],
  real_estate: [
    [/\b(?:safe|good|nice|family[- ]friendly|exclusive)\s+(?:neighbou?rhood|area|community|schools?)\b/i,
      'fair-housing coded language about an area'],
    [/\bgood schools?\b/i, 'fair-housing coded language about an area'],
    [/\bwill appreciate\b/i, 'a future-value claim'],
    [/\bguaranteed sale\b/i, 'a guaranteed-sale claim'],
  ],
  fitness_coaching: [
    [/\blose\s+\d+\s?(?:lbs?|pounds|kg)\b/i, 'a weight-loss outcome claim'],
    [/\btransform your body\b/i, 'a body-composition claim'],
    [/\bguaranteed results\b/i, 'a guaranteed-results claim'],
  ],
  ecom_dtc: [
    [/\bonly\s+\d+\s+left\b/i, 'a scarcity claim (FTC — must be true)'],
    [/\b(?:expires?|ends?)\s+in\s+\d+\s?(?:min|hour|hr)/i, 'an urgency countdown (FTC — must be true)'],
    [/\blast chance\b/i, 'an urgency claim (FTC — must be true)'],
  ],
  professional_services: [
    [/\bwe (?:will|can) win\b/i, 'an outcome claim on a matter'],
    [/\byou (?:will|should) win\b/i, 'an outcome claim on a matter'],
    [/\bspecialist\b/i, 'a "specialist" claim (bar/board regulated)'],
  ],
  restaurant_local: [],
  home_services: [],
  auto_detail: [],
  transportation: [],
};

/* ─────────────────────────── the gate ─────────────────────────── */

/**
 * Check one draft before it becomes a message.
 *
 * @param {string} text      the draft
 * @param {object} [opts]
 * @param {object} [opts.profile]  defaults to the install's business profile
 * @param {string} [opts.context]  source text (the customer's own message, a work order).
 *                                 Amounts the customer themselves named are allowed back —
 *                                 quoting "you said your budget is $200" is not inventing
 *                                 a price, and a gate that blocked it would be turned off.
 * @returns {{ok: boolean, violations: Array, checked: object}}
 */
function checkClaims(text, opts = {}) {
  const profile = opts.profile || loadProfile();
  const draft = String(text == null ? '' : text);
  const violations = [];

  // Amounts the install authorised, plus any the other party already put on the table.
  const allowed = authorisedAmounts(profile);
  for (const m of String(opts.context || '').match(MONEY_RE) || []) {
    const a = amountOf(m); if (a != null) allowed.add(a);
  }
  for (const m of String(opts.context || '').match(PERCENT_RE) || []) {
    const a = amountOf(m); if (a != null) allowed.add(a);
  }

  const hasRateCard = allowed.size > 0 || (profile.rate_card != null
    && (Array.isArray(profile.rate_card) ? profile.rate_card.length > 0 : true));

  for (const raw of draft.match(MONEY_RE) || []) {
    const a = amountOf(raw);
    if (a == null || allowed.has(a)) continue;
    violations.push({
      kind: 'unauthorised_price',
      found: raw.trim(),
      why: hasRateCard
        ? `${raw.trim()} is not on this install's rate card`
        : `${raw.trim()} was quoted and this install has NO rate card — nothing can verify it`,
    });
  }

  for (const raw of draft.match(PERCENT_RE) || []) {
    const a = amountOf(raw);
    if (a == null || allowed.has(a)) continue;
    violations.push({
      kind: 'unauthorised_rate',
      found: raw.trim(),
      why: `${raw.trim()} is not on this install's rate card`,
    });
  }

  const vertical = profile.industry_pack || profile.claims_profile || null;
  const phrases = CORE_PHRASES.concat(VERTICAL_PHRASES[vertical] || []);
  const allow = (profile.claims && Array.isArray(profile.claims.allow_phrases))
    ? profile.claims.allow_phrases.map(s => String(s).toLowerCase())
    : [];

  for (const [re, why] of phrases) {
    const m = draft.match(re);
    if (!m) continue;
    if (allow.some(a => m[0].toLowerCase().includes(a))) continue;  // explicitly authorised
    violations.push({ kind: 'unverifiable_claim', found: m[0], why });
  }

  return {
    ok: violations.length === 0,
    violations,
    checked: { vertical, hasRateCard, authorisedAmounts: allowed.size },
  };
}

/**
 * Throwing form, for a caller that should simply not proceed.
 * The error carries the violations so a human sees WHAT to fix, not just that something broke.
 */
function assertClaimsOk(text, opts = {}) {
  const r = checkClaims(text, opts);
  if (r.ok) return r;
  const err = new Error(
    `claims gate REFUSED this draft (${r.violations.length}): `
    + r.violations.map(v => `${v.found} — ${v.why}`).join(' · '),
  );
  err.code = 'CLAIMS_REFUSED';
  err.violations = r.violations;
  throw err;
}

/** One-line human summary for a review queue. */
function explain(result) {
  if (result.ok) return 'claims gate: clean';
  return 'claims gate REFUSED: ' + result.violations.map(v => `${v.found} (${v.why})`).join('; ');
}

module.exports = {
  checkClaims,
  assertClaimsOk,
  explain,
  _internals: { MONEY_RE, PERCENT_RE, amountOf, authorisedAmounts, CORE_PHRASES, VERTICAL_PHRASES },
};
