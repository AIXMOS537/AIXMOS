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
  bits.push('Never invent a price, a product or a claim that is not listed above.');
  return bits.join('\n\n');
}

/** Who a task can be assigned to. Never a specific human unless this install said so. */
function ownerLabel(p = loadProfile()) { return p.owner_label || 'OWNER'; }

function escalations(p = loadProfile()) {
  return (p.escalate_to_owner || GENERIC.escalate_to_owner).join(', ');
}

module.exports = { loadProfile, businessContext, ownerLabel, escalations, profilePath: FILE, GENERIC };
