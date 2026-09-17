'use strict';
/**
 * Do-not-contact gate for every outbound message this pack can send.
 *
 * WHY THIS EXISTS. Before it, `lib/sender.js` sent to any number handed to it, through GHL,
 * Quo or iMessage, with no suppression check anywhere in the pack. Meanwhile
 * `remind-overdue.js` and `retry-failed-reminders.js` both end their message with
 * "Reply STOP to opt out" — a written promise to the recipient that **nothing in the code
 * honoured**, because nothing consumed an inbound STOP and nothing checked a list before
 * sending.
 *
 * That is worse than having no opt-out line at all: it is a representation the software
 * does not implement. This pack installs on other people's machines and sends from their
 * numbers, so that exposure lands on them and on whoever shipped it.
 *
 * FAIL CLOSED. If the list cannot be read — missing permissions, corrupt file, unreadable
 * disk — this refuses the send. A suppression list that errors open is not a control; it
 * is a control-shaped hole, and the whole point is that it cannot be silently bypassed.
 * An empty list is different from an unreadable one and is allowed through.
 */

const fs = require('fs');
const path = require('path');
const os = require('os');

const DIR = process.env.AIXMOS_STATE_DIR || path.join(os.homedir(), '.aixmos');
const FILE = path.join(DIR, 'do-not-contact.json');

/** Last 10 digits — comparison must survive +1, spaces, dashes and parentheses. */
function key(raw) {
  const d = String(raw == null ? '' : raw).replace(/\D/g, '');
  return d.length > 10 ? d.slice(-10) : d;
}

/** Keywords that are an unambiguous opt-out. Deliberately narrow and exact-match. */
const STOP_WORDS = new Set(['stop', 'stopall', 'unsubscribe', 'cancel', 'end', 'quit', 'revoke', 'optout']);
const START_WORDS = new Set(['start', 'unstop', 'yes', 'optin']);

/**
 * Free text that reads like an opt-out without being a keyword. NOT auto-suppressed and
 * NOT auto-replied — it is flagged for a human, because guessing wrong in either direction
 * is bad: suppress a customer who did not ask, or keep texting someone who plainly did.
 */
const STOP_LIKE = /\b(stop\s+(texting|messaging|calling)|take me off|remove me|leave me alone|don'?t (text|message|contact) me|no more (texts|messages))\b/i;

function classifyInbound(text) {
  const t = String(text == null ? '' : text).trim().toLowerCase().replace(/[.!?,]+$/, '');
  if (STOP_WORDS.has(t)) return 'opt_out';
  if (START_WORDS.has(t)) return 'opt_in';
  if (STOP_LIKE.test(t)) return 'stop_like';
  return 'none';
}

function readList() {
  try {
    if (!fs.existsSync(FILE)) return {};           // never written yet — genuinely empty
    const raw = fs.readFileSync(FILE, 'utf8');
    if (!raw.trim()) return {};
    const parsed = JSON.parse(raw);
    if (!parsed || typeof parsed !== 'object' || Array.isArray(parsed)) {
      throw new Error('do-not-contact list is not an object');
    }
    return parsed;
  } catch (e) {
    // Surfaced to the caller, which refuses the send. Never swallowed into "nobody opted out".
    const err = new Error(`do-not-contact list unreadable: ${e.message}`);
    err.code = 'DNC_UNREADABLE';
    throw err;
  }
}

function writeList(list) {
  fs.mkdirSync(DIR, { recursive: true });
  fs.writeFileSync(FILE, JSON.stringify(list, null, 2), { mode: 0o600 });
}

/** Throws DNC_UNREADABLE rather than returning false when the list cannot be read. */
function isSuppressed(phone) {
  const k = key(phone);
  if (!k) return false;
  return Object.prototype.hasOwnProperty.call(readList(), k);
}

function suppress(phone, reason = 'inbound STOP') {
  const k = key(phone);
  if (!k) return { ok: false, error: 'no usable number' };
  const list = readList();
  if (list[k]) return { ok: true, alreadySuppressed: true };
  list[k] = { at: new Date().toISOString(), reason };
  writeList(list);
  return { ok: true, alreadySuppressed: false };
}

function unsuppress(phone) {
  const k = key(phone);
  if (!k) return { ok: false, error: 'no usable number' };
  const list = readList();
  if (!list[k]) return { ok: true, wasSuppressed: false };
  delete list[k];
  writeList(list);
  return { ok: true, wasSuppressed: true };
}

/**
 * Handle one inbound message. STOP suppresses, START releases, stop-like is flagged only.
 * Returns what was decided so a caller can log or escalate it.
 */
function handleInbound({ from, text }) {
  const kind = classifyInbound(text);
  if (kind === 'opt_out') { suppress(from, 'inbound STOP'); return { kind, suppressed: true }; }
  if (kind === 'opt_in') { unsuppress(from); return { kind, suppressed: false }; }
  if (kind === 'stop_like') return { kind, suppressed: false, needsHuman: true };
  return { kind, suppressed: false };
}

module.exports = { isSuppressed, suppress, unsuppress, handleInbound, classifyInbound, listPath: FILE, _key: key };
