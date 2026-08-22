'use strict';

const fs = require('fs');
const path = require('path');
const { DRAFTS_DIR, AUDIT_FILE, ensureDirs } = require('./paths');
const { hashHandle } = require('./chatdb');

function writeDraft({ id, tier, from, inbound, reply, backend, action }) {
  ensureDirs();
  const stamp = new Date().toISOString().replace(/[:.]/g, '-');
  const safeId = String(id || stamp).replace(/[^a-zA-Z0-9._-]/g, '_').slice(0, 80);
  const file = path.join(DRAFTS_DIR, `${stamp}-${tier}-${safeId}.json`);
  const rec = {
    id: safeId,
    tier,
    from_hash: hashHandle(from),
    inbound: String(inbound || '').slice(0, 2000),
    reply: String(reply || '').slice(0, 2000),
    backend: backend || null,
    action,
    sent: false,
    created_at: new Date().toISOString(),
  };
  fs.writeFileSync(file, JSON.stringify(rec, null, 2), { mode: 0o600 });
  return { file, rec };
}

function markDraftSent(file) {
  try {
    const rec = JSON.parse(fs.readFileSync(file, 'utf8'));
    rec.sent = true;
    rec.action = 'sent';
    rec.sent_at = new Date().toISOString();
    fs.writeFileSync(file, JSON.stringify(rec, null, 2), { mode: 0o600 });
  } catch {
    /* draft already useful even if this stamp fails */
  }
}

function audit(event) {
  ensureDirs();
  const line = JSON.stringify({
    ts: new Date().toISOString(),
    ...event,
    from: undefined,
    from_hash: event.from_hash || (event.from ? hashHandle(event.from) : undefined),
    inbound: event.inbound ? String(event.inbound).slice(0, 240) : undefined,
  }) + '\n';
  fs.appendFileSync(AUDIT_FILE, line, { mode: 0o600 });
}

module.exports = { writeDraft, markDraftSent, audit };
