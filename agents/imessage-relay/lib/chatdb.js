'use strict';

const { execFileSync } = require('child_process');
const crypto = require('crypto');
const fs = require('fs');
const path = require('path');
const os = require('os');
const { CHAT_DB, CURSOR_FILE, MIRROR_DB } = require('./paths');

const APPLE_EPOCH_MS = Date.UTC(2001, 0, 1);

function sqlite(db, sql) {
  return execFileSync('/usr/bin/sqlite3', ['-readonly', db, sql], {
    encoding: 'utf8',
    timeout: 8000,
    stdio: ['ignore', 'pipe', 'pipe'],
  }).trim();
}

function resolveDb() {
  const candidates = [];
  try {
    if (MIRROR_DB && fs.existsSync(MIRROR_DB)) {
      const st = fs.statSync(MIRROR_DB);
      if (Date.now() - st.mtimeMs < 60000) candidates.push(MIRROR_DB);
    }
  } catch { /* ignore */ }
  candidates.push(CHAT_DB);
  return candidates;
}

function probeFda() {
  const dbs = resolveDb();
  let lastErr = '';
  for (const db of dbs) {
    try {
      const n = sqlite(db, 'SELECT COUNT(*) FROM message;');
      if (!/^\d+$/.test(n)) continue;
      return { ok: true, messages: Number(n), path: db, via: db === CHAT_DB ? 'live' : 'mirror' };
    } catch (err) {
      const msg = (err.stderr && String(err.stderr)) || err.message;
      lastErr = msg.trim();
    }
  }
  return {
    ok: false,
    error: lastErr || 'chat.db not accessible',
    hint: 'Grant Full Disk Access to /usr/local/bin/node (Cmd+Shift+G). Cursor can quit. Then: me on',
  };
}

function textFromAttributedBody(buf) {
  if (!Buffer.isBuffer(buf) || buf.length < 8) return '';
  const raw = buf.toString('utf8');
  const idx = raw.indexOf('NSString');
  const slice = idx >= 0 ? raw.slice(idx + 8) : raw;
  const runs = slice.match(/[\t\x20-\x7E\u00A0-\uFFFF]{3,}/g) || [];
  const cleaned = runs
    .map((s) => s.replace(/NS[A-Z][A-Za-z]+/g, '').trim())
    .filter((s) => s.length >= 2 && !/^(streamtyped|NSDictionary|NSNumber|iI)$/i.test(s));
  cleaned.sort((a, b) => b.length - a.length);
  return (cleaned[0] || '').slice(0, 2000);
}

function appleDateToIso(n) {
  const num = Number(n);
  if (!Number.isFinite(num) || num <= 0) return null;
  const ms = num > 1e12 ? APPLE_EPOCH_MS + num / 1e6 : APPLE_EPOCH_MS + num / 1e3;
  return new Date(ms).toISOString();
}

function copyChatDb() {
  const dest = path.join(os.tmpdir(), `chatdb-copy-${process.pid}.db`);
  const dbs = resolveDb();
  let lastErr;
  for (const db of dbs) {
    try {
      execFileSync('/usr/bin/sqlite3', [db, `.backup '${dest.replace(/'/g, "''")}'`], {
        timeout: 10000,
        stdio: ['ignore', 'pipe', 'pipe'],
      });
      // macOS 27 ships sqlite 3.54, which cannot open a WAL-mode file -readonly without
      // its -shm. .backup keeps WAL mode, so convert the PRIVATE TEMP COPY (never chat.db)
      // to a rollback journal before the -readonly query. Broke polling from ~2026-09-04.
      execFileSync('/usr/bin/sqlite3', [dest, 'PRAGMA journal_mode=DELETE;'], {
        timeout: 10000,
        stdio: ['ignore', 'pipe', 'pipe'],
      });
      return dest;
    } catch (err) {
      lastErr = err;
    }
  }
  throw lastErr || new Error('chat.db copy failed');
}

/**
 * Read inbound (not-from-me) messages after last cursor.
 * Does not log bodies. Caller must treat as private.
 */
function readNewInbound({ limit = 20 } = {}) {
  const fda = probeFda();
  if (!fda.ok) return { ok: false, error: fda.error, hint: fda.hint, messages: [] };

  let last = 0;
  try { last = Number(fs.readFileSync(CURSOR_FILE, 'utf8')) || 0; } catch { last = 0; }

  let copy;
  try {
    copy = copyChatDb();
    const sql = [
      'SELECT m.ROWID, m.guid, m.text, m.attributedBody, m.is_from_me, m.date, m.service, h.id',
      'FROM message m LEFT JOIN handle h ON h.ROWID = m.handle_id',
      `WHERE m.ROWID > ${Number(last)} AND m.is_from_me = 0 AND m.item_type = 0 AND m.is_system_message = 0`,
      'ORDER BY m.ROWID ASC',
      `LIMIT ${Number(limit)};`,
    ].join(' ');
    const raw = execFileSync('/usr/bin/sqlite3', ['-readonly', '-json', copy, sql], {
      encoding: 'utf8',
      timeout: 10000,
      maxBuffer: 8 * 1024 * 1024,
    }).trim();
    const rows = raw ? JSON.parse(raw) : [];
    const messages = rows.map((r) => {
      let text = (r.text || '').trim();
      if (!text && r.attributedBody) {
        const buf = Buffer.isBuffer(r.attributedBody)
          ? r.attributedBody
          : Buffer.from(String(r.attributedBody), 'base64');
        text = textFromAttributedBody(buf);
      }
      return {
        rowid: r.ROWID,
        guid: r.guid,
        from: r.id || '',
        text,
        service: r.service,
        at: appleDateToIso(r.date),
        fromMe: false,
      };
    });
    return { ok: true, messages, last };
  } catch (err) {
    return { ok: false, error: err.message, messages: [] };
  } finally {
    if (copy) for (const f of [copy, `${copy}-wal`, `${copy}-shm`]) { try { fs.unlinkSync(f); } catch { /* ignore */ } }
  }
}

function advanceCursor(rowid) {
  fs.writeFileSync(CURSOR_FILE, String(rowid), { mode: 0o600 });
}

function hashHandle(from) {
  return crypto.createHash('sha256').update(String(from || '')).digest('hex').slice(0, 12);
}

module.exports = {
  probeFda,
  textFromAttributedBody,
  appleDateToIso,
  readNewInbound,
  advanceCursor,
  hashHandle,
  CHAT_DB,
};
