#!/usr/bin/env node
'use strict';
/**
 * FRONT DESK DAEMON — the part that runs on its own.
 *
 * Started at boot by setup.js (launchd on macOS, Task Scheduler on Windows). It watches for
 * inbound work, hands each item to the front desk, and leaves a gated draft in the queue.
 *
 * TWO WAYS WORK ARRIVES, because a client site has both:
 *   - a watched folder   drop a .json or .txt in inbox/ and it is processed. This is how a
 *                        phone relay, a shell script or a Zap lands work with no API.
 *   - an HTTP endpoint   POST /inbound — what a GHL/Twilio/webform webhook calls.
 *
 * IT DOES NOT SEND. Not in any mode, not behind any flag. The daemon's job ends when the
 * draft is queued and the owner is told. A background process that could send on its own is
 * a background process that will eventually send something nobody read.
 *
 * FAILURE IS LOUD AND BOUNDED. An item that throws is moved to inbox/failed/ with the error
 * beside it, never silently retried forever and never deleted. A crash exits non-zero so the
 * supervisor restarts it; KeepAlive is set to restart only on failure, so a clean stop stays
 * stopped (an always-restart KeepAlive on a short job is how a run loop becomes 97,000
 * silent executions).
 */

const fs = require('fs');
const path = require('path');
const http = require('http');
const { loadAixmosEnv } = require('./lib/env');

loadAixmosEnv();

const frontdesk = require('./lib/frontdesk');
const { loadProfile } = require('./lib/profile');

const ROOT = __dirname;
const INBOX = process.env.AIXMOS_INBOX || path.join(ROOT, 'inbox');
const DONE = path.join(INBOX, 'processed');
const FAILED = path.join(INBOX, 'failed');
const PORT = parseInt(process.env.AIXMOS_FRONTDESK_PORT || '7788', 10);
const HOST = process.env.AIXMOS_FRONTDESK_HOST || '127.0.0.1';
const POLL_MS = parseInt(process.env.AIXMOS_POLL_MS || '5000', 10);

for (const d of [INBOX, DONE, FAILED]) fs.mkdirSync(d, { recursive: true });

const log = (...a) => console.log(new Date().toISOString(), ...a);

/**
 * ONE DESK PER INBOX.
 *
 * Found 2026-09-19 in a live install test: setup.js had started the daemon under launchd,
 * an operator started a second one by hand, and both drained the same folder. One renamed
 * a file out from under the other mid-process (ENOENT on the move) — and the real harm is
 * the invisible one: the same inbound gets handled twice, so a customer receives two
 * replies from the same business.
 *
 * The in-process `draining` flag cannot see another PROCESS. Two defences, because either
 * alone is insufficient: this lock stops a second daemon starting, and claimFile() below
 * makes the per-file handoff atomic even if one somehow does.
 */
const LOCK = path.join(INBOX, '.daemon.lock');

function takeLock() {
  try {
    const prev = parseInt(fs.readFileSync(LOCK, 'utf8').trim(), 10);
    if (prev && prev !== process.pid) {
      try {
        process.kill(prev, 0);            // signal 0 = "does this pid exist?"
        log(`another front desk is already running (pid ${prev}) on this inbox — exiting.`);
        log('Two desks on one inbox answer the same customer twice. Stop that one first.');
        process.exit(0);                  // not a failure; the desk IS running
      } catch {
        log(`clearing a stale lock from pid ${prev} (process is gone)`);
      }
    }
  } catch { /* no lock file — normal */ }
  fs.writeFileSync(LOCK, String(process.pid));
  const release = () => { try { if (parseInt(fs.readFileSync(LOCK, 'utf8'), 10) === process.pid) fs.rmSync(LOCK); } catch {} };
  process.on('exit', release);
}

/* ─────────────────────── owner notification ─────────────────────── */

/**
 * A desk that works all night is useless if nobody is told. Reuses the Telegram config
 * setup.js writes (and scheduler.js already reads) rather than inventing a second channel.
 * Notification failure is logged, never fatal — a missed ping must not lose the draft.
 */
async function notifyOwner(record) {
  try {
    const f = path.join(ROOT, 'config.json');
    if (!fs.existsSync(f)) return;
    const cfg = JSON.parse(fs.readFileSync(f, 'utf8'));
    if (!cfg.telegram?.enabled || !cfg.telegram?.bot_token) return;
    const to = (cfg.scheduler?.morning_brief_recipients || [])[0];
    if (!to) return;

    const flag = record.status === 'NEEDS_FIX' ? '⛔ needs a fix'
      : record.escalated ? '⚠️ needs YOU'
        : '✅ ready to approve';
    const text = [
      `${flag} — ${record.lane}`,
      record.from ? `from ${record.from}` : '',
      `"${String(record.inbound).slice(0, 120)}"`,
      '',
      record.draft ? String(record.draft).slice(0, 400) : '(no draft)',
      record.gate && !record.gate.ok ? `\n${record.gate.summary}` : '',
    ].filter(Boolean).join('\n');

    await fetch(`https://api.telegram.org/bot${cfg.telegram.bot_token}/sendMessage`, {
      method: 'POST',
      headers: { 'content-type': 'application/json' },
      body: JSON.stringify({ chat_id: to, text }),
    });
  } catch (e) {
    log('notify failed (draft is still queued):', e.message);
  }
}

/* ─────────────────────── core ─────────────────────── */

async function process1(inbound, source) {
  const t0 = Date.now();
  const r = await frontdesk.handleInbound(inbound);
  log(`[${source}] ${r.lane} · ${r.chain.join('→') || '-'} · ${r.status}`
    + `${r.escalated ? ' ESCALATED' : ''} · ${((Date.now() - t0) / 1000).toFixed(1)}s`);
  // Only bother a human when a human is actually needed.
  if (['READY_FOR_APPROVAL', 'NEEDS_FIX', 'ESCALATED_TO_OWNER', 'NEEDS_HUMAN'].includes(r.status)) {
    await notifyOwner(r);
  }
  return r;
}

/** Parse a dropped file. JSON gives from/text; plain text is the message itself. */
function parseDrop(file, raw) {
  if (file.endsWith('.json')) {
    const j = JSON.parse(raw);
    return { from: j.from || j.phone || null, text: j.text || j.message || j.body || '', channel: j.channel || 'file' };
  }
  // "+15715550101: how much?"  — or just the message.
  const m = raw.match(/^\s*(\+?\d[\d\s().-]{6,})\s*[:|]\s*([\s\S]+)$/);
  return m ? { from: m[1].trim(), text: m[2].trim(), channel: 'file' }
    : { from: null, text: raw.trim(), channel: 'file' };
}

let draining = false;
async function drainInbox() {
  if (draining) return;                 // one pass at a time — no double-processing
  draining = true;
  try {
    const files = fs.readdirSync(INBOX)
      .filter(f => !f.startsWith('.'))          // never pick up a claim file or the lock
      .filter(f => /\.(json|txt)$/i.test(f))
      .filter(f => fs.statSync(path.join(INBOX, f)).isFile());
    for (const f of files) {
      // CLAIM IT FIRST. rename() is atomic on a local filesystem: exactly one process can
      // win the move, and the loser gets ENOENT and skips. Process only what you claimed —
      // reading first and renaming last is the race that answers a customer twice.
      const src = path.join(INBOX, f);
      const claimed = path.join(INBOX, `.claim-${process.pid}-${f}`);
      try { fs.renameSync(src, claimed); } catch { continue; }   // someone else got it

      let raw;
      try { raw = fs.readFileSync(claimed, 'utf8'); } catch { continue; }
      try {
        const inbound = parseDrop(f, raw);
        if (!inbound.text) throw new Error('no message text found in the drop');
        await process1(inbound, f);
        fs.renameSync(claimed, path.join(DONE, f));
      } catch (e) {
        // Moved aside WITH the reason. Never deleted, never retried in a loop.
        log(`[${f}] FAILED: ${e.message}`);
        try {
          fs.renameSync(claimed, path.join(FAILED, f));
          fs.writeFileSync(path.join(FAILED, `${f}.error.txt`),
            `${new Date().toISOString()}\n${e.stack || e.message}\n`);
        } catch { /* best effort */ }
      }
    }
  } catch (e) {
    log('inbox scan failed:', e.message);
  } finally { draining = false; }
}

/* ─────────────────────── http ─────────────────────── */

function startHttp() {
  const server = http.createServer(async (req, res) => {
    const send = (code, obj) => {
      res.writeHead(code, { 'content-type': 'application/json' });
      res.end(JSON.stringify(obj, null, 2));
    };
    try {
      if (req.method === 'GET' && req.url === '/healthz') {
        const p = loadProfile();
        return send(200, {
          ok: true,
          business: p.business_name || null,
          queue_waiting: frontdesk.listQueue().length,
          inbox: INBOX,
          sends: 'never — drafts queue for a human',
        });
      }
      if (req.method === 'GET' && req.url === '/queue') {
        return send(200, { queue: frontdesk.listQueue().slice(0, 50) });
      }
      if (req.method === 'POST' && req.url === '/inbound') {
        let body = '';
        for await (const c of req) {
          body += c;
          if (body.length > 64 * 1024) { req.destroy(); return; }
        }
        let j;
        try { j = JSON.parse(body || '{}'); } catch { return send(400, { error: 'body must be JSON' }); }
        const text = j.text || j.message || j.Body || '';
        if (!text) return send(400, { error: 'missing "text"' });
        const r = await process1({ from: j.from || j.From || null, text, channel: j.channel || 'http' }, 'http');
        return send(200, r);
      }
      return send(404, { error: 'not found', try: ['GET /healthz', 'GET /queue', 'POST /inbound {from,text}'] });
    } catch (e) {
      log('http error:', e.message);
      try { send(500, { error: e.message }); } catch { /* socket gone */ }
    }
  });
  // Loopback by default. A front desk reachable from the LAN is a free-LLM vending machine.
  server.listen(PORT, HOST, () => log(`http listening on http://${HOST}:${PORT}`));
  server.on('error', (e) => { log('http failed:', e.message); process.exit(1); });
}

/* ─────────────────────── main ─────────────────────── */

const p = loadProfile();
log('AIXMOS front desk starting');
log(`  business : ${p.business_name || '(unnamed — no profile)'} · vertical: ${p.industry_pack || 'none'}`);
log(`  rate card: ${(p.rate_card || []).length} item(s)` + ((p.rate_card || []).length ? '' : ' — all prices will be refused'));
log(`  inbox    : ${INBOX}`);
log(`  queue    : ${frontdesk.QUEUE_DIR}`);
log('  sending  : DISABLED BY DESIGN — every draft waits for a human');

takeLock();
startHttp();
drainInbox();
setInterval(drainInbox, POLL_MS);

process.on('unhandledRejection', (e) => { log('unhandled rejection:', e && e.message); });
for (const sig of ['SIGINT', 'SIGTERM']) {
  process.on(sig, () => { log(`${sig} — stopping cleanly`); process.exit(0); });
}
