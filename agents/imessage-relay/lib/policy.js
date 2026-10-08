'use strict';

const { loadFamilyHandles } = require('./paths');

const T3_RE = /\b(mom|dad|mama|baba|mother|father|sister|brother|aunt|uncle|grandma|grandpa|nana|family|kid|kids|son|daughter|wife|husband|child support|alimony|zelle|venmo|cashapp|cash app|paypal|wire transfer|routing number|iban|swift code|ssn|social security|ein\b|w-?2\b|lawsuit|lawyer|attorney|court date|subpoena|evict|eviction|nda\b|retainer|owe[sd]?\b|invoice|bank account|crypto wallet|bitcoin|child|minor)\b/i;

const T1_RE = /\b(rick|status|what'?s on|help me|draft|remind|summarize|briefing|queue|to-?do|owner gate|calendar|schedule|text my mac|ping)\b/i;

const COMMIT_RE = /\b(send (the )?(quote|invoice|contract|proposal|money)|i('ll| will) (send|do|pay|sign|call)|confirm(ed|ation)? (the )?(order|deal|price|booking)|signed |wire |pay (me|you|him|now)|deposit |approved |agreed to)\b/i;

function digits(raw) {
  return String(raw || '').replace(/\D/g, '');
}

function canonHandle(raw) {
  const s = String(raw || '').trim().toLowerCase();
  const d = digits(s);
  if (d.length >= 10) return d.slice(-10);
  return s;
}

function inList(handle, list) {
  const c = canonHandle(handle);
  return (list || []).some((x) => canonHandle(x) === c);
}

function looksAssistant(text) {
  const body = String(text || '').trim();
  if (!body) return false;
  if (T1_RE.test(body)) return true;
  if (/^(hi|hey|yo|status|help|\?)\s*$/i.test(body)) return true;
  if (/\b(hours|open|available|booking|book|price|pricing|how much|where are you|you there|got a minute)\b/i.test(body)) {
    return true;
  }
  return false;
}

/**
 * T1 — assistant voice. Auto-send when auto_send_assistant is on.
 * T2 — commitment / Taha-voice ghostwrite. Never auto-send.
 * T3 — family / money / legal. Never auto-send. Canned draft only.
 */
function classify({ from, text }, config) {
  const body = String(text || '');
  const t3Sender = inList(from, config.t3_senders);
  if (t3Sender || T3_RE.test(body)) {
    return {
      tier: 'T3',
      reason: t3Sender ? 't3_sender' : 'family_money_legal',
      allowlisted: inList(from, config.t1_allowlist),
    };
  }
  const allowlisted = inList(from, config.t1_allowlist);
  if (COMMIT_RE.test(body)) {
    return { tier: 'T2', reason: 'commitment_shaped', allowlisted };
  }
  const autoField = config.auto_field !== false;
  if ((allowlisted || autoField) && looksAssistant(body)) {
    return {
      tier: 'T1',
      reason: allowlisted ? 'allowlisted_assistant' : 'auto_field_assistant',
      allowlisted,
    };
  }
  if (autoField) {
    return { tier: 'T1', reason: 'auto_field_catchall', allowlisted };
  }
  if (allowlisted) {
    return { tier: 'T2', reason: 'allowlisted_not_assistant_shaped', allowlisted: true };
  }
  return { tier: 'T2', reason: 'ghostwrite', allowlisted: false };
}

function t3CannedDraft() {
  return 'FLAGGED T3 (family / money / legal). No auto-reply. Human review required. Draft never send.';
}

/**
 * Startup guard, not an enforcement gate: warns (never throws/blocks) if any
 * MASTER-exec-eligible owner_handles entry also appears on the content-team
 * pipeline's FAMILY_NUMBERS roster (~/.config/tmmt/content-team.env). A family
 * number should never be able to trigger runOwnerExec.
 */
function familyOwnerOverlap(ownerHandles) {
  const roster = loadFamilyHandles();
  if (!roster.found) {
    return {
      checked: false,
      overlaps: [],
      note: 'no family/team roster discoverable at ~/.config/tmmt/content-team.env — skipped',
    };
  }
  const overlaps = (ownerHandles || []).filter((h) => inList(h, roster.handles));
  return { checked: true, overlaps, familyCount: roster.handles.length };
}

module.exports = {
  T3_RE,
  T1_RE,
  COMMIT_RE,
  digits,
  canonHandle,
  inList,
  looksAssistant,
  classify,
  t3CannedDraft,
  familyOwnerOverlap,
};
