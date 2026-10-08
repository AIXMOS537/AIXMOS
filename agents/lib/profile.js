'use strict';
/**
 * Per-install business profile — what makes this pack white-label instead of TMMT-flavoured.
 *
 * WHY. The agent personas used to hardcode one specific operation: "AIXMOS serves three
 * businesses: TMMT Auto Services (car rentals/chauffeur/detailing/drivers), AIXMOS Platform
 * ($97/month members ...)". A client installing the pack got a CHUMMO that believed it
 * worked for TMMT and would say so in copy written for THEIR customers. MOOSE even listed
 * "MUHAMMAD" as a task owner.
 *
 * Now every persona reads this profile instead. Nobody's business name is in the prompts.
 *
 * THE DEFAULT NAMES NOTHING. With no profile file, agents get a neutral context that says
 * "the business you work for" and nothing more. That is deliberately bland rather than
 * clever: an agent inventing a plausible-sounding business is worse than one that simply
 * does not assume. The launcher reports which profile is loaded so nobody is guessing.
 */

const fs = require('fs');
const path = require('path');

const FILE = process.env.AIXMOS_PROFILE
  || path.join(__dirname, '..', 'config', 'business-profile.json');

/** Neutral. Names no business, no person, no price. */
const GENERIC = {
  business_name: null,
  what_we_do: null,
  owner_label: 'OWNER',
  lines: [],
  escalate_to_owner: ['legal or insurance matters', 'an unhappy customer', 'anything risky'],
  notes: [],
  // The authorised numbers. lib/claims.js REFUSES any price or rate in a draft that is
  // not in here. Empty means this install quotes nothing — and a draft that quotes
  // anyway is refused, because nothing can verify it.
  rate_card: [],
  // Optional. Matches a FORGE industry pack name and switches on that vertical's claim
  // rules (med_spa -> no cure/permanence, real_estate -> fair housing, and so on).
  industry_pack: null,
  claims: { allow_phrases: [] },
};

function loadProfile() {
  try {
    if (!fs.existsSync(FILE)) return { ...GENERIC, source: 'default' };
    const raw = JSON.parse(fs.readFileSync(FILE, 'utf8'));
    if (!raw || typeof raw !== 'object' || Array.isArray(raw)) return { ...GENERIC, source: 'default' };
    return {
      ...GENERIC,
      ...raw,
      lines: Array.isArray(raw.lines) ? raw.lines : GENERIC.lines,
      escalate_to_owner: Array.isArray(raw.escalate_to_owner) ? raw.escalate_to_owner : GENERIC.escalate_to_owner,
      notes: Array.isArray(raw.notes) ? raw.notes : GENERIC.notes,
      rate_card: raw.rate_card != null ? raw.rate_card : GENERIC.rate_card,
      industry_pack: typeof raw.industry_pack === 'string' ? raw.industry_pack : GENERIC.industry_pack,
      claims: (raw.claims && typeof raw.claims === 'object') ? raw.claims : GENERIC.claims,
      owner_label: typeof raw.owner_label === 'string' && raw.owner_label.trim() ? raw.owner_label.trim() : GENERIC.owner_label,
      source: 'file',
    };
  } catch {
    // A malformed profile must not inject half-parsed nonsense into a customer-facing
    // persona. Fall back to naming nothing.
    return { ...GENERIC, source: 'invalid' };
  }
}

/** The paragraph every persona gets. Never contains a name the install did not supply. */
function businessContext(p = loadProfile()) {
  if (!p.business_name && (!p.lines || p.lines.length === 0)) {
    return 'You work for the business that installed you. You have not been told its name, '
      + 'what it sells, or its prices — so never invent them. If a detail matters and you do '
      + 'not have it, say so and ask.';
  }
  const bits = [];
  if (p.business_name) {
    bits.push(`You work for ${p.business_name}${p.what_we_do ? ` — ${p.what_we_do}` : ''}.`);
  }
  if (p.lines && p.lines.length) {
    bits.push(
      'Lines of business:\n'
      + p.lines.map(l => (typeof l === 'string' ? `- ${l}` : `- ${l.name}${l.detail ? ` — ${l.detail}` : ''}${l.tone ? ` (tone: ${l.tone})` : ''}`)).join('\n'),
    );
  }
  if (p.notes && p.notes.length) bits.push(p.notes.map(n => `- ${n}`).join('\n'));
  // Show the rate card. The gate refuses anything off it either way, but an agent that
  // can SEE the authorised prices quotes them correctly instead of guessing and being
  // blocked — the prompt and the enforcement should agree, not fight.
  const card = Array.isArray(p.rate_card) ? p.rate_card : [];
  if (card.length) {
    bits.push('Rate card — the ONLY prices you may quote:\n'
      + card.map(r => (typeof r === 'string' ? `- ${r}` : `- ${r.item}: ${r.price}`)).join('\n'));
  } else {
    bits.push('You have NO rate card. Do not quote any price or percentage — say you will '
      + 'check and come back with it.');
  }
  bits.push('Never invent a price, a product or a claim that is not listed above. '
    + 'An automated gate checks every draft and refuses anything that is.');
  return bits.join('\n\n');
}

/** Who a task can be assigned to. Never a specific human unless this install said so. */
function ownerLabel(p = loadProfile()) { return p.owner_label || 'OWNER'; }

function escalations(p = loadProfile()) {
  return (p.escalate_to_owner || GENERIC.escalate_to_owner).join(', ');
}

module.exports = { loadProfile, businessContext, ownerLabel, escalations, profilePath: FILE, GENERIC };
