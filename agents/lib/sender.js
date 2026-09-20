/**
 * Multi-channel SMS sender for TMMT.
 *
 * Three pluggable channels, tried in the order set by SEND_CHANNELS
 * (default "ghl,quo,imessage"). You can also force one channel per call.
 *
 *   GHL      — TMMT Rentals GoHighLevel number (the business line). LIVE.
 *   QUO      — Quo number. Needs QUO_API_KEY + QUO_API_URL + QUO_NUMBER (+ credits).
 *   IMESSAGE — work iPhone, via a tiny relay running on the Mac
 *              (IMESSAGE_RELAY_URL [+ IMESSAGE_RELAY_SECRET]).
 *
 * Every provider implements: name, isConfigured(), why(), send({to,text}).
 * send() returns { ok, channel, id?, error? } and never throws to the router.
 */

const { loadAixmosEnv } = require('./env');
const { isSuppressed } = require('./suppression');
const { checkClaims, explain: explainClaims } = require('./claims');
loadAixmosEnv();

function toE164(raw) {
  const d = String(raw || '').replace(/\D/g, '');
  if (d.length === 10) return '+1' + d;
  if (d.length === 11 && d[0] === '1') return '+' + d;
  if (String(raw || '').trim().startsWith('+')) return String(raw).trim();
  return null;
}

async function http(method, url, headers, body) {
  const res = await fetch(url, {
    method,
    headers: { Accept: 'application/json', ...headers },
    body: body ? JSON.stringify(body) : undefined,
  });
  const text = await res.text();
  let json;
  try { json = text ? JSON.parse(text) : {}; } catch { json = { raw: text }; }
  return { status: res.status, ok: res.ok, json, text };
}

/* ── GHL (LeadConnector v2) ─────────────────────────────────────── */
const GHL_BASE = 'https://services.leadconnectorhq.com';
const ghl = {
  name: 'ghl',
  key() { return (process.env.GHL_API_KEY || '').trim(); },
  loc() { return (process.env.GHL_LOCATION_ID || '').trim(); },
  from() { return toE164(process.env.GHL_FROM_NUMBER || '') || ''; },
  isConfigured() { return !!(this.key() && this.loc()); },
  why() { return this.isConfigured() ? 'ready' : 'missing GHL_API_KEY or GHL_LOCATION_ID'; },
  hdr(version) {
    return { Authorization: `Bearer ${this.key()}`, Version: version, 'Content-Type': 'application/json' };
  },
  async send({ to, text }) {
    const phone = toE164(to);
    if (!phone) return { ok: false, channel: 'ghl', error: `bad phone: ${to}` };
    const up = await upsertGhlContact(phone);
    if (!up.ok) return up;
    const contactId = up.contactId;
    // 2) send the SMS in that contact's conversation
    const body = { type: 'SMS', contactId, message: text };
    if (this.from()) body.fromNumber = this.from();
    const msg = await http('POST', `${GHL_BASE}/conversations/messages`, this.hdr('2021-04-15'), body);
    if (!msg.ok) {
      return { ok: false, channel: 'ghl', error: `send failed (${msg.status}): ${msg.text.slice(0, 160)}` };
    }
    return { ok: true, channel: 'ghl', id: msg.json?.messageId || msg.json?.conversationId || 'sent', contactId };
  },
};

async function upsertGhlContact(phone, name) {
  const p = ghl;
  if (!p.isConfigured()) {
    return { ok: false, channel: 'ghl', error: `not configured — ${p.why()}` };
  }
  const body = { locationId: p.loc(), phone: toE164(phone) };
  if (name) body.name = String(name).trim();
  const up = await http('POST', `${GHL_BASE}/contacts/upsert`, p.hdr('2021-07-28'), body);
  const contactId = up.json?.contact?.id || up.json?.id;
  if (!contactId) {
    return { ok: false, channel: 'ghl', error: `upsert failed (${up.status}): ${up.text.slice(0, 160)}` };
  }
  return { ok: true, channel: 'ghl', contactId };
}

async function resolveGhlContactId({ phone, name } = {}) {
  const r = await upsertGhlContact(phone, name);
  return r.ok ? r.contactId : null;
}

/* ── Quo ────────────────────────────────────────────────────────── */
const quo = {
  name: 'quo',
  key() { return (process.env.QUO_API_KEY || '').trim(); },
  url() { return (process.env.QUO_API_URL || '').trim().replace(/\/$/, ''); },
  from() { return toE164(process.env.QUO_NUMBER || '') || ''; },
  isConfigured() { return !!(this.key() && this.url() && this.from()); },
  why() {
    if (!this.key()) return 'missing QUO_API_KEY (no Quo API key is stored yet)';
    if (!this.url()) return 'missing QUO_API_URL';
    if (!this.from()) return 'missing QUO_NUMBER';
    return 'ready (note: workspace must have prepaid credits)';
  },
  async send({ to, text }) {
    const phone = toE164(to);
    if (!phone) return { ok: false, channel: 'quo', error: `bad phone: ${to}` };
    const r = await http('POST', `${this.url()}/messages`,
      { Authorization: `Bearer ${this.key()}`, 'Content-Type': 'application/json' },
      { from: this.from(), to: phone, content: text });
    if (!r.ok) return { ok: false, channel: 'quo', error: `send failed (${r.status}): ${r.text.slice(0, 160)}` };
    return { ok: true, channel: 'quo', id: r.json?.id || 'sent' };
  },
};

/* ── iMessage (work iPhone) via Mac relay ───────────────────────── */
const imessage = {
  name: 'imessage',
  url() { return (process.env.IMESSAGE_RELAY_URL || '').trim().replace(/\/$/, ''); },
  secret() { return (process.env.IMESSAGE_RELAY_SECRET || '').trim(); },
  isConfigured() { return !!this.url(); },
  why() { return this.isConfigured() ? 'ready' : 'missing IMESSAGE_RELAY_URL (set up the Mac relay first)'; },
  async send({ to, text }) {
    const phone = toE164(to) || String(to);
    const headers = { 'Content-Type': 'application/json' };
    if (this.secret()) headers['X-Relay-Secret'] = this.secret();
    const r = await http('POST', `${this.url()}/send`, headers, { to: phone, text });
    if (!r.ok) return { ok: false, channel: 'imessage', error: `relay failed (${r.status}): ${r.text.slice(0, 160)}` };
    return { ok: true, channel: 'imessage', id: r.json?.id || 'sent' };
  },
};

const PROVIDERS = { ghl, quo, imessage };

function parseList(s) {
  return String(s || '').split(',').map(x => x.trim().toLowerCase()).filter(Boolean);
}

function channelOrder() {
  return parseList(process.env.SEND_CHANNELS || 'ghl,imessage');
}

// Role-based routing — pick channels by message PURPOSE, not one global order.
//   customer / partner → iMessage first (shows BLUE), GHL as deliverability backup
//   alert / reminder   → GHL (system automations)
// Quo is intentionally NOT in any auto-route: it's for the team to use BY HAND
// in the Quo app. (You can still force it per-call with channel:'quo'.)
// Override any route via env, e.g. ROUTE_CUSTOMER=imessage  (strict blue, no backup).
const DEFAULT_ROUTES = {
  customer: 'imessage,ghl',
  partner: 'imessage,ghl',
  alert: 'ghl',
  reminder: 'ghl',
};

function routeOrder(route) {
  if (!route) return channelOrder();
  const r = String(route).toLowerCase();
  const envVal = process.env['ROUTE_' + r.toUpperCase()];
  if (envVal) return parseList(envVal);
  if (DEFAULT_ROUTES[r]) return parseList(DEFAULT_ROUTES[r]);
  return channelOrder();
}

function channelStatus() {
  return Object.values(PROVIDERS).map(p => ({
    channel: p.name, configured: p.isConfigured(), detail: p.why(),
  }));
}

/**
 * Send one message.
 *   opts.route    — purpose: 'customer' | 'partner' | 'alert' | 'reminder'
 *                   (picks channels by role; ignored if opts.channel is set)
 *   opts.channel  — force a single channel (no fallback)
 *   opts.fallback — if true (default), try the next configured channel on failure
 *   opts.dryRun   — don't actually send; report what WOULD happen
 *   opts.claimsContext — the source text (customer's own message). Amounts THEY named
 *                   are allowed back in the reply; quoting someone is not inventing.
 *   opts.skipClaims — bypass the claims gate. For a human who has read the draft and
 *                   accepts it. Never set by default, never set by an agent.
 */
async function sendMessage({ to, text, channel, route, fallback = true, dryRun = false,
                             skipClaims = false, claimsContext = '' } = {}) {
  if (!to || !text) return { ok: false, error: 'to and text are required' };

  // ── DO-NOT-CONTACT GATE ─────────────────────────────────────────────────────────────
  // Every outbound path in this pack funnels through here: GHL, Quo and iMessage, and all
  // five callers (send-sms, remind-overdue, retry-failed-reminders, backfill-reminder-
  // dedupe, imessage-relay). One choke point, so the gate cannot be routed around.
  //
  // It is checked BEFORE dryRun on purpose: a dry run that reports "would send" to a
  // suppressed number is a lie that gets copied into a real run.
  //
  // FAILS CLOSED. An unreadable list refuses the send rather than assuming nobody opted
  // out. remind-overdue.js tells people "Reply STOP to opt out" -- this is what makes that
  // sentence true.
  try {
    if (isSuppressed(to)) {
      return { ok: false, suppressed: true, error: 'recipient has opted out (do-not-contact)', to };
    }
  } catch (e) {
    return { ok: false, suppressed: true, error: `refusing to send: ${e.message}`, to };
  }

  // ── CLAIMS GATE ─────────────────────────────────────────────────────────────────────
  // Same choke point, same reason: every outbound path funnels through here, so the gate
  // cannot be routed around by calling a provider directly.
  //
  // Checked BEFORE dryRun, for the identical reason the DNC check is: a dry run that
  // reports "would send" a draft quoting $199 the client never authorised is a lie that
  // gets copied into a real run.
  //
  // This is what makes profile.js's closing line — "Never invent a price, a product or a
  // claim that is not listed above" — true. On 2026-09-19 a clean white-label install
  // invented a price in 2 of 3 drafts while that line was in its prompt. A rule nothing
  // enforces is a preference.
  //
  // Skippable ONLY by an explicit opts.skipClaims, which exists so a human who has read a
  // draft and accepts it can push it through. Nothing sets that by default.
  if (!skipClaims) {
    try {
      const verdict = checkClaims(text, { context: claimsContext });
      if (!verdict.ok) {
        return {
          ok: false,
          claimsRefused: true,
          error: explainClaims(verdict),
          violations: verdict.violations,
          to,
        };
      }
    } catch (e) {
      // A gate that errors open is a control-shaped hole. Refuse.
      return { ok: false, claimsRefused: true, error: `refusing to send: ${e.message}`, to };
    }
  }

  const order = channel ? [channel.toLowerCase()] : routeOrder(route);
  const attempts = [];

  for (const name of order) {
    const p = PROVIDERS[name];
    if (!p) { attempts.push({ channel: name, ok: false, error: 'unknown channel' }); continue; }
    if (!p.isConfigured()) { attempts.push({ channel: name, ok: false, error: `not configured — ${p.why()}` }); continue; }
    if (dryRun) return { ok: true, dryRun: true, channel: name, route: route || null, order, to: toE164(to), attempts };
    const r = await p.send({ to, text });
    attempts.push(r);
    if (r.ok) return { ...r, route: route || null, attempts };
    if (!fallback) break;
  }
  return { ok: false, error: 'all channels failed or unconfigured', route: route || null, order, attempts };
}

module.exports = { sendMessage, channelStatus, channelOrder, routeOrder, toE164, resolveGhlContactId, upsertGhlContact, PROVIDERS };
